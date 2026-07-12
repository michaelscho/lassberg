/**
 * Phase 7b.4: GraphRAG retrieval orchestration, entirely client-side.
 *   1. Query -> embedding search (search.js) -> top-k letters.
 *   2. Graph expansion per hit: sharedMentions + correspondenceContext (graph-core.js).
 *   3. Context assembly: hits + expanded candidates, capped, embedding score primary + graph
 *      evidence as a tie-break/bonus note.
 *   4. Default: retrieval-only display (no LLM call, no key needed) - the assembled, cited
 *      context IS the deliverable. An optional "ask an LLM" step is intentionally NOT wired to a
 *      real API call here: browser-side calls to the Anthropic Messages API are blocked by CORS
 *      (no browser-safe endpoint exists), so pretending a key field enables it would ship a
 *      broken feature. The retrieval-only context is written so it can be pasted into any chat
 *      client instead.
 */
import { buildIndex, correspondenceContext, sharedMentions } from "./graph-core.js";
import { search } from "./search.js";

let graphIndexCache = null;

async function loadGraphIndex() {
  if (graphIndexCache) return graphIndexCache;
  const graphJson = await (await fetch("data/graph.json")).json();
  graphIndexCache = buildIndex(graphJson);
  return graphIndexCache;
}

/** Runs the full GraphRAG retrieval pipeline; returns a structured, citable context object. */
export async function graphragRetrieve(query, { topK = 5, maxContext = 15, onProgress } = {}) {
  onProgress?.("Embedding-Suche...");
  const hits = await search(query, { topK, onProgress });
  const index = await loadGraphIndex();

  const context = new Map(); // id -> { id, source: "embedding"|"graph", score?, reasons: [] }
  for (const hit of hits) {
    context.set(hit.id, { id: hit.id, score: hit.score, reasons: ["Embedding-Treffer"], meta: hit });
  }

  for (const hit of hits) {
    if (!index.nodesByKey.has(hit.id)) continue;

    for (const shared of sharedMentions(index, hit.id, 2)) {
      const reason = `Teilt ${shared.sharedCount} Erwaehnungen mit Treffer ${hit.id}`;
      if (context.has(shared.id)) {
        context.get(shared.id).reasons.push(reason);
      } else if (context.size < maxContext) {
        context.set(shared.id, { id: shared.id, score: null, reasons: [reason] });
      }
    }

    for (const related of correspondenceContext(index, hit.id, 90)) {
      const reason = `Im Korrespondenzkontext von ${hit.id} (${related.daysApart} Tage entfernt)`;
      if (context.has(related.id)) {
        context.get(related.id).reasons.push(reason);
      } else if (context.size < maxContext) {
        context.set(related.id, { id: related.id, score: null, reasons: [reason] });
      }
    }
  }

  const ranked = [...context.values()].sort((a, b) => {
    if (a.score != null && b.score != null) return b.score - a.score;
    if (a.score != null) return -1;
    if (b.score != null) return 1;
    return b.reasons.length - a.reasons.length;
  });

  return { query, results: ranked.slice(0, maxContext) };
}

function renderContext(contextResult, container) {
  container.innerHTML = "";
  if (contextResult.results.length === 0) {
    container.innerHTML = '<p class="status">Keine Ergebnisse.</p>';
    return;
  }
  for (const item of contextResult.results) {
    const div = document.createElement("div");
    div.className = "rag-card";
    const scoreLabel = item.score != null ? `<span class="score">${item.score.toFixed(3)}</span>` : "";
    div.innerHTML = `
      ${scoreLabel}
      <a href="../html/letters/${item.id}.html" target="_blank"><strong>${item.id}</strong></a>
      ${item.meta ? `<div class="meta">${item.meta.date || ""} - ${item.meta.sender || "?"} &rarr; ${item.meta.recipient || "?"}</div>` : ""}
      ${item.meta?.incipit ? `<p>${item.meta.incipit}</p>` : ""}
      <ul>${item.reasons.map((r) => `<li>${r}</li>`).join("")}</ul>
    `;
    container.appendChild(div);
  }
}

export function initGraphRagUI() {
  const form = document.getElementById("graphrag-form");
  const input = document.getElementById("graphrag-input");
  const status = document.getElementById("graphrag-status");
  const results = document.getElementById("graphrag-results");
  const button = document.getElementById("graphrag-button");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    button.disabled = true;
    status.textContent = "";
    try {
      const contextResult = await graphragRetrieve(query, {
        onProgress: (msg) => { status.textContent = msg; },
      });
      status.textContent = `${contextResult.results.length} Briefe im Kontext (Retrieval-only-Modus).`;
      renderContext(contextResult, results);
    } catch (err) {
      status.textContent = `Fehler: ${err.message}`;
      console.error(err);
    } finally {
      button.disabled = false;
    }
  });
}
