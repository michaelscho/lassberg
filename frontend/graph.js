/**
 * Phase 7b.3: browser graph layer. Loads frontend/data/graph.json, builds the dependency-free
 * index from graph-core.js (shared with the Node unit tests in tests/test_graph_core.mjs), and
 * renders ego networks with Graphology + Sigma.js (lazy-loaded only when the Graph tab is opened
 * or a node is selected - never on initial page load).
 */
import { buildIndex, correspondenceContext, egoNetwork, neighbors, sharedMentions } from "./graph-core.js";

let graphIndex = null;
let sigmaInstance = null;

async function loadGraph() {
  if (graphIndex) return graphIndex;
  const resp = await fetch("data/graph.json");
  const graphJson = await resp.json();
  graphIndex = buildIndex(graphJson);
  return graphIndex;
}

const MAX_RENDERED_NODES = 80; // dense hubs (e.g. a person who is sender/recipient of 100+
// letters) would otherwise produce an unreadable hairball; keep the closest nodes by depth.

async function renderEgoNetwork(nodeId, depth = 2) {
  const index = await loadGraph();
  const { nodes, edges, depths } = egoNetwork(index, nodeId, depth);

  const [{ default: Graph }, { Sigma }] = await Promise.all([
    import("https://cdn.jsdelivr.net/npm/graphology@0.26.0/+esm"),
    import("https://cdn.jsdelivr.net/npm/sigma@3.0.3/+esm"),
  ]);

  // Sort by depth so truncation keeps the closest neighborhood, then group into concentric rings
  // per depth (instead of one flat circle) so depth-2 nodes don't overlap depth-1 labels.
  const sortedNodes = [...nodes].sort((a, b) => (depths[a.key] ?? 99) - (depths[b.key] ?? 99));
  const shown = sortedNodes.slice(0, MAX_RENDERED_NODES);

  const byDepth = new Map();
  for (const node of shown) {
    const d = depths[node.key] ?? 0;
    if (!byDepth.has(d)) byDepth.set(d, []);
    byDepth.get(d).push(node);
  }

  const g = new Graph();
  const typeColor = { letter: "#1d4e89", person: "#a13d3d", place: "#3f6b5c", work: "#8a6f45", witness: "#6a4c93" };
  for (const [d, ringNodes] of byDepth) {
    const radius = d === 0 ? 0 : d;
    ringNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / ringNodes.length;
      if (!g.hasNode(node.key)) {
        g.addNode(node.key, {
          label: node.attributes.label || node.key,
          size: node.key === nodeId ? 12 : Math.max(3, 6 - d),
          color: typeColor[node.attributes.type] || "#888",
          x: radius * Math.cos(angle),
          y: radius * Math.sin(angle),
        });
      }
    });
  }
  edges.forEach((e) => {
    if (g.hasNode(e.source) && g.hasNode(e.target) && !g.hasEdge(e.source, e.target)) {
      g.addEdge(e.source, e.target, { label: e.type, size: 1, color: "#ccc" });
    }
  });

  const container = document.getElementById("sigma-container");
  if (sigmaInstance) {
    sigmaInstance.kill();
    sigmaInstance = null;
  }
  sigmaInstance = new Sigma(g, container, { labelSize: 12, renderEdgeLabels: false });
}

export async function initGraphUI() {
  const form = document.getElementById("graph-form");
  const input = document.getElementById("graph-node-input");
  const status = document.getElementById("graph-status");
  const depthInput = document.getElementById("graph-depth");
  const resultsBox = document.getElementById("graph-expansion-results");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const nodeId = input.value.trim();
    if (!nodeId) return;
    status.textContent = "Lade Graph...";
    try {
      const index = await loadGraph();
      if (!index.nodesByKey.has(nodeId)) {
        status.textContent = `Unbekannte ID: ${nodeId}`;
        return;
      }
      const depth = Number(depthInput.value) || 2;
      await renderEgoNetwork(nodeId, depth);
      status.textContent = `Ego-Netzwerk fuer ${nodeId} (Tiefe ${depth}).`;

      const parts = [];
      const nb = neighbors(index, nodeId);
      parts.push(`<h4>Direkte Nachbarn (${nb.length})</h4><ul>` +
        nb.slice(0, 15).map((x) => `<li>${x.type}: ${x.node?.attributes?.label || x.id}</li>`).join("") + "</ul>");

      if (index.nodesByKey.get(nodeId)?.attributes?.type === "letter") {
        const sm = sharedMentions(index, nodeId, 2);
        parts.push(`<h4>Briefe mit geteilten Erwaehnungen (${sm.length})</h4><ul>` +
          sm.slice(0, 10).map((x) => `<li>${x.id} (${x.sharedCount} geteilt)</li>`).join("") + "</ul>");

        const cc = correspondenceContext(index, nodeId, 90);
        parts.push(`<h4>Gleicher Korrespondenzkontext, +/-90 Tage (${cc.length})</h4><ul>` +
          cc.slice(0, 10).map((x) => `<li>${x.id} (${x.date}, ${x.daysApart} Tage)</li>`).join("") + "</ul>");
      }
      resultsBox.innerHTML = parts.join("");
    } catch (err) {
      status.textContent = `Fehler: ${err.message}`;
      console.error(err);
    }
  });
}
