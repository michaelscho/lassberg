/**
 * Phase 7b.3: deterministic, dependency-free GraphRAG expansion functions over the Graphology-
 * serialization-format graph exported by scripts/export_graph_json.py (frontend/data/graph.json).
 *
 * Framework-agnostic on purpose: these four functions only touch plain objects/Maps, so they run
 * identically in the browser and under plain Node (`node --test tests/`) with zero dependencies -
 * Graphology/Sigma (frontend/graph.js) are only needed for the interactive visualization, not for
 * this expansion logic.
 *
 * Graph shape (see scripts/export_graph_json.py):
 *   nodes: [{ key, attributes: { type: "letter"|"person"|"place"|"work"|"witness", ... } }]
 *   edges: [{ source, target, attributes: { type: "SENT_BY"|"SENT_TO"|"SENT_FROM"|"MENTIONS" } }]
 */

/** Builds adjacency indices once so the expansion functions below are O(1)/O(degree), not O(E). */
export function buildIndex(graphJson) {
  const nodesByKey = new Map(graphJson.nodes.map((n) => [n.key, n]));
  const outEdges = new Map();
  const inEdges = new Map();
  for (const e of graphJson.edges) {
    const type = e.attributes.type;
    if (!outEdges.has(e.source)) outEdges.set(e.source, []);
    outEdges.get(e.source).push({ target: e.target, type });
    if (!inEdges.has(e.target)) inEdges.set(e.target, []);
    inEdges.get(e.target).push({ source: e.source, type });
  }
  return { nodesByKey, outEdges, inEdges };
}

/** All directly connected entities of a letter (or any node), with the edge type. */
export function neighbors(index, nodeId) {
  const out = (index.outEdges.get(nodeId) || []).map((e) => ({
    id: e.target,
    type: e.type,
    node: index.nodesByKey.get(e.target),
  }));
  const inn = (index.inEdges.get(nodeId) || []).map((e) => ({
    id: e.source,
    type: e.type,
    node: index.nodesByKey.get(e.source),
  }));
  return [...out, ...inn];
}

/**
 * Letters that share >= minShared mentioned entities with `letterId` (2-hop via entity nodes),
 * sorted by overlap size descending. Only meaningful between full-text letters - register-only
 * letters have no MENTIONS edges at all, so they never appear here.
 */
export function sharedMentions(index, letterId, minShared = 2) {
  const myMentions = new Set(
    (index.outEdges.get(letterId) || []).filter((e) => e.type === "MENTIONS").map((e) => e.target)
  );
  const counts = new Map();
  for (const entityId of myMentions) {
    const mentioningLetters = (index.inEdges.get(entityId) || [])
      .filter((e) => e.type === "MENTIONS")
      .map((e) => e.source);
    for (const otherId of mentioningLetters) {
      if (otherId === letterId) continue;
      counts.set(otherId, (counts.get(otherId) || 0) + 1);
    }
  }
  return [...counts.entries()]
    .filter(([, n]) => n >= minShared)
    .map(([id, n]) => ({ id, sharedCount: n, node: index.nodesByKey.get(id) }))
    .sort((a, b) => b.sharedCount - a.sharedCount);
}

function dayDiff(d1, d2) {
  return Math.abs((new Date(d1) - new Date(d2)) / 86400000);
}

function pairKey(a, b) {
  return [a, b].sort().join("|");
}

/**
 * Letters belonging to the same correspondence (same sender/recipient pair, either direction) as
 * `letterId`, within `windowDays` of its date. Works across all 3268 letters (register-only
 * included) since SENT_BY/SENT_TO/date come from the overall register, not just full-text ones.
 */
export function correspondenceContext(index, letterId, windowDays = 90) {
  const myEdges = index.outEdges.get(letterId) || [];
  const sender = myEdges.find((e) => e.type === "SENT_BY")?.target;
  const recipient = myEdges.find((e) => e.type === "SENT_TO")?.target;
  const myDate = index.nodesByKey.get(letterId)?.attributes?.date;
  if (!sender || !recipient || !myDate) return [];

  const myPair = pairKey(sender, recipient);
  const results = [];
  for (const [id, node] of index.nodesByKey) {
    if (node.attributes.type !== "letter" || id === letterId) continue;
    const edges = index.outEdges.get(id) || [];
    const s = edges.find((e) => e.type === "SENT_BY")?.target;
    const r = edges.find((e) => e.type === "SENT_TO")?.target;
    if (!s || !r || pairKey(s, r) !== myPair) continue;
    const otherDate = node.attributes.date;
    if (!otherDate) continue;
    const diff = dayDiff(myDate, otherDate);
    if (diff <= windowDays) {
      results.push({ id, date: otherDate, daysApart: Math.round(diff) });
    }
  }
  return results.sort((a, b) => a.daysApart - b.daysApart);
}

/**
 * Ego network of an entity (or letter) up to `depth` hops, traversed as undirected (both in- and
 * out-edges) - for visualization (frontend/graph.js renders this via Sigma.js), not for ranking.
 */
export function egoNetwork(index, nodeId, depth = 2) {
  const visited = new Set([nodeId]);
  const nodeDepth = new Map([[nodeId, 0]]);
  const collectedEdges = [];
  let frontier = [nodeId];

  for (let d = 0; d < depth; d++) {
    const nextFrontier = [];
    for (const id of frontier) {
      for (const e of index.outEdges.get(id) || []) {
        collectedEdges.push({ source: id, target: e.target, type: e.type });
        if (!visited.has(e.target)) {
          visited.add(e.target);
          nodeDepth.set(e.target, d + 1);
          nextFrontier.push(e.target);
        }
      }
      for (const e of index.inEdges.get(id) || []) {
        collectedEdges.push({ source: e.source, target: id, type: e.type });
        if (!visited.has(e.source)) {
          visited.add(e.source);
          nodeDepth.set(e.source, d + 1);
          nextFrontier.push(e.source);
        }
      }
    }
    frontier = nextFrontier;
  }

  const seen = new Set();
  const edges = collectedEdges.filter((e) => {
    const key = `${e.source}->${e.target}:${e.type}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
  const nodes = [...visited].map((id) => index.nodesByKey.get(id)).filter(Boolean);
  // depths: {nodeId -> BFS distance from the ego node}, e.g. for graph.js's concentric-ring
  // layout - additive field, doesn't change the nodes/edges shape existing callers rely on.
  const depths = Object.fromEntries(nodeDepth);
  return { nodes, edges, depths };
}
