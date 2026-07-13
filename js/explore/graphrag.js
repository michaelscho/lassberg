/**
 * Phase 7b.4: GraphRAG retrieval orchestration, entirely client-side.
 *   1. Query -> embedding search (search.js) -> top-k letters.
 *   2. Graph expansion per hit: sharedMentions + correspondenceContext (graph-core.js).
 *   3. Context assembly: hits + expanded candidates, capped, embedding score primary + graph
 *      evidence as a tie-break/bonus note.
 *   4. Default: retrieval-only display (no LLM call, no key needed) - the assembled, cited
 *      context IS the deliverable.
 *   5. LLM-orchestrated research chat (user-supplied key): agent.js runs the full GraphRAG
 *      agent loop - the LLM formulates semantic + SPARQL + graph queries itself and
 *      synthesizes a cited answer; llm-providers.js supports SAIA/Anthropic/OpenAI/Gemini.
 *      The retrieval-only pipeline above stays as the keyless path, with a copy-prompt
 *      fallback (needed for SAIA, whose API currently rejects browser CORS preflights).
 */
import { buildIndex, correspondenceContext, sharedMentions } from "./graph-core.js";
import { search } from "./search.js";
// agent.js imports loadGraphIndex from this module in turn - a benign cycle, since both
// modules only reference each other's exports at call time, never during module evaluation.
import { runAgent } from "./agent.js";
import { PROVIDERS, listModels } from "./llm-providers.js";
import { renderMarkdown } from "./md.js";

let graphIndexCache = null;

/** Cached graph index over json/explore/graph.json - shared with the agent (agent.js). */
export async function loadGraphIndex() {
  if (graphIndexCache) return graphIndexCache;
  const graphJson = await (await fetch("../json/explore/graph.json")).json();
  graphIndexCache = buildIndex(graphJson);
  return graphIndexCache;
}

/** Runs the full GraphRAG retrieval pipeline; returns a structured, citable context object. */
export async function graphragRetrieve(query, { topK = 5, maxContext = 15, onProgress } = {}) {
  onProgress?.("Embedding search...");
  const hits = await search(query, { topK, onProgress });
  const index = await loadGraphIndex();

  const context = new Map(); // id -> { id, source: "embedding"|"graph", score?, reasons: [] }
  for (const hit of hits) {
    context.set(hit.id, { id: hit.id, score: hit.score, reasons: ["Embedding match"], meta: hit });
  }

  for (const hit of hits) {
    if (!index.nodesByKey.has(hit.id)) continue;

    for (const shared of sharedMentions(index, hit.id, 2)) {
      const reason = `Shares ${shared.sharedCount} mentions with hit ${hit.id}`;
      if (context.has(shared.id)) {
        context.get(shared.id).reasons.push(reason);
      } else if (context.size < maxContext) {
        context.set(shared.id, { id: shared.id, score: null, reasons: [reason] });
      }
    }

    for (const related of correspondenceContext(index, hit.id, 90)) {
      const reason = `In the correspondence context of ${hit.id} (${related.daysApart} days apart)`;
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
    container.innerHTML = '<p class="status">No results.</p>';
    return;
  }
  for (const item of contextResult.results) {
    const div = document.createElement("div");
    div.className = "rag-card";
    const scoreLabel = item.score != null ? `<span class="score">${item.score.toFixed(3)}</span>` : "";
    div.innerHTML = `
      ${scoreLabel}
      <a href="letters/${item.id}.html" target="_blank"><strong>${item.id}</strong></a>
      ${item.meta ? `<div class="meta">${item.meta.date || ""} - ${item.meta.sender || "?"} &rarr; ${item.meta.recipient || "?"}</div>` : ""}
      ${item.meta?.incipit ? `<p>${item.meta.incipit}</p>` : ""}
      <ul>${item.reasons.map((r) => `<li>${r}</li>`).join("")}</ul>
    `;
    container.appendChild(div);
  }
}

// --- optional LLM step (SAIA / any OpenAI-compatible endpoint) --------------------------------

const MAX_TEXT_CHARS = 2500; // per letter, keeps 15-letter contexts well inside typical limits

/** Builds the full RAG prompt from the retrieval context, pulling letter texts from the graph. */
async function buildPrompt(contextResult) {
  const index = await loadGraphIndex();
  const blocks = contextResult.results.map((item) => {
    const attrs = index.nodesByKey.get(item.id)?.attributes || {};
    const text = (attrs.text || "").slice(0, MAX_TEXT_CHARS);
    return [
      `[${item.id}] ${attrs.date || "undated"} - ${item.meta?.sender || "?"} an ${item.meta?.recipient || "?"}`,
      `Retrieval-Begruendung: ${item.reasons.join("; ")}`,
      text ? `Text:\n${text}` : "(kein Volltext verfuegbar - nur Registermetadaten)",
    ].join("\n");
  });
  const system =
    "Du bist Assistent fuer die digitale Edition der Korrespondenz Joseph von Lassbergs " +
    "(1770-1855). Beantworte die Frage AUSSCHLIESSLICH auf Grundlage der folgenden Briefe. " +
    "Zitiere jede Aussage mit der Brief-ID in eckigen Klammern, z.B. [lassberg-letter-0952]. " +
    "Wenn die Briefe die Frage nicht beantworten, sage das ausdruecklich.";
  const user = `Frage: ${contextResult.query}\n\nBriefe:\n\n${blocks.join("\n\n---\n\n")}`;
  return { system, user };
}

// --- LLM-orchestrated research chat (agent.js) --------------------------------------------------

let letterPageIds = null; // IDs of full-text letters (they have html/letters/ pages)

async function loadLetterPageIds() {
  if (letterPageIds) return letterPageIds;
  try {
    const index = await (await fetch("../json/explore/letters_index.json")).json();
    letterPageIds = new Set(index.map((e) => e.id));
  } catch {
    letterPageIds = new Set();
  }
  return letterPageIds;
}

function chatBubble(role, text) {
  const div = document.createElement("div");
  div.className = `chat-msg ${role}`;
  if (role === "assistant") {
    // safe renderer: escapes everything first, then whitelisted markdown + letter-ID links
    div.appendChild(renderMarkdown(text, letterPageIds || new Set()));
  } else {
    div.textContent = text; // user input / errors stay plain text
  }
  return div;
}

function initAgentChat() {
  const providerSelect = document.getElementById("agent-provider");
  const keyInput = document.getElementById("agent-key");
  const modelInput = document.getElementById("agent-model");
  const endpointInput = document.getElementById("agent-endpoint");
  const providerNote = document.getElementById("agent-provider-note");
  const log = document.getElementById("agent-log");
  const form = document.getElementById("agent-form");
  const input = document.getElementById("agent-input");
  const send = document.getElementById("agent-send");
  if (!providerSelect) return;

  for (const [id, p] of Object.entries(PROVIDERS)) {
    const opt = document.createElement("option");
    opt.value = id;
    opt.textContent = p.label;
    providerSelect.appendChild(opt);
  }

  function applyProvider(fromStorage) {
    const p = PROVIDERS[providerSelect.value];
    providerNote.textContent = p.note || "";
    keyInput.value = localStorage.getItem(`llm_key_${providerSelect.value}`) || "";
    if (fromStorage) {
      modelInput.value = localStorage.getItem(`llm_model_${providerSelect.value}`) || p.defaultModel;
      endpointInput.value = localStorage.getItem(`llm_endpoint_${providerSelect.value}`) || p.endpoint;
    } else {
      modelInput.value = p.defaultModel;
      endpointInput.value = p.endpoint;
    }
  }

  providerSelect.value = localStorage.getItem("llm_provider") || "anthropic";
  applyProvider(true);
  providerSelect.addEventListener("change", () => {
    localStorage.setItem("llm_provider", providerSelect.value);
    applyProvider(true);
  });
  keyInput.addEventListener("change", () => localStorage.setItem(`llm_key_${providerSelect.value}`, keyInput.value.trim()));
  modelInput.addEventListener("change", () => localStorage.setItem(`llm_model_${providerSelect.value}`, modelInput.value.trim()));
  endpointInput.addEventListener("change", () => localStorage.setItem(`llm_endpoint_${providerSelect.value}`, endpointInput.value.trim()));

  // fetch the models actually available for this key -> autocomplete on the model field,
  // so nobody has to guess model IDs (a wrong ID is a 404 from the provider)
  const modelsBtn = document.getElementById("agent-models-btn");
  const modelList = document.getElementById("agent-model-list");
  modelsBtn?.addEventListener("click", async () => {
    const key = keyInput.value.trim();
    if (!key) { providerNote.textContent = "Enter an API key first, then fetch the model list."; return; }
    modelsBtn.disabled = true;
    providerNote.textContent = "Fetching available models…";
    try {
      const models = await listModels({
        provider: providerSelect.value,
        endpoint: endpointInput.value.trim(),
        key,
      });
      modelList.textContent = "";
      for (const id of models) {
        const opt = document.createElement("option");
        opt.value = id;
        modelList.appendChild(opt);
      }
      providerNote.textContent = `${models.length} models available — the model field now autocompletes (clear it and click to browse).`;
    } catch (err) {
      providerNote.textContent = `Could not list models: ${err.message}`;
    } finally {
      modelsBtn.disabled = false;
    }
  });

  const history = []; // prior Q&A pairs, passed back to the model each turn

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const question = input.value.trim();
    if (!question) return;
    const key = keyInput.value.trim();
    if (!key) {
      providerNote.textContent = "Please enter an API key for the selected provider first.";
      return;
    }
    input.value = "";
    send.disabled = true;
    log.hidden = false;
    await loadLetterPageIds(); // so answer citations can link to existing letter pages
    log.appendChild(chatBubble("user", question));

    const trace = document.createElement("div");
    trace.className = "agent-trace";
    log.appendChild(trace);
    log.scrollTop = log.scrollHeight;

    const llmConfig = {
      provider: providerSelect.value,
      key,
      model: modelInput.value.trim(),
      endpoint: endpointInput.value.trim(),
    };

    try {
      for await (const event of runAgent(question, history, llmConfig)) {
        if (event.type === "tool_call") {
          const step = document.createElement("div");
          step.className = "agent-step";
          step.textContent = `→ ${event.name}(${JSON.stringify(event.args)})`;
          trace.appendChild(step);
        } else if (event.type === "tool_result") {
          const last = trace.lastElementChild;
          if (last) last.textContent += `  ✓ ${event.preview.length < event.size ? event.preview + "…" : event.preview}`;
        } else if (event.type === "answer") {
          log.appendChild(chatBubble("assistant", event.text));
          history.push({ role: "user", content: question });
          history.push({ role: "assistant", content: event.text });
        } else if (event.type === "error") {
          let msg = `Error: ${event.message}`;
          if (llmConfig.provider === "saia" && /failed to fetch/i.test(event.message)) {
            msg += " — SAIA's API currently rejects browser CORS preflights; use the copy-prompt " +
                   "path below, another provider, or a proxy endpoint.";
          } else if (/404|not found|NOT_FOUND/i.test(event.message)) {
            msg += " — the model ID probably doesn't exist. Use the ↻ button next to the model " +
                   "field to fetch the models available for your key.";
          }
          log.appendChild(chatBubble("error", msg));
        }
        log.scrollTop = log.scrollHeight;
      }
    } finally {
      send.disabled = false;
    }
  });
}

export function initGraphRagUI() {
  const form = document.getElementById("graphrag-form");
  const input = document.getElementById("graphrag-input");
  const status = document.getElementById("graphrag-status");
  const results = document.getElementById("graphrag-results");
  const button = document.getElementById("graphrag-button");
  const copyButton = document.getElementById("graphrag-copy");

  let lastContext = null;

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
      status.textContent = `${contextResult.results.length} letters in context (retrieval-only mode).`;
      renderContext(contextResult, results);
      lastContext = contextResult;
      if (copyButton) {
        copyButton.disabled = false;
        copyButton.title = "";
      }
    } catch (err) {
      status.textContent = `Error: ${err.message}`;
      console.error(err);
    } finally {
      button.disabled = false;
    }
  });

  copyButton?.addEventListener("click", async () => {
    if (!lastContext) return;
    const { system, user } = await buildPrompt(lastContext);
    await navigator.clipboard.writeText(`${system}\n\n${user}`);
    copyButton.textContent = "copied!";
    setTimeout(() => { copyButton.textContent = "copy-prompt"; }, 2000);
  });

  initAgentChat();
}
