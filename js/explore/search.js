/**
 * Phase 7: browser-side semantic search over the corpus's embeddings.
 *
 * Multi-model (2026-07-21): the corpus is embedded once per model listed in
 * json/explore/embedding_models.json (built from config.yaml: embedding.models by
 * scripts/export_frontend.py) - currently BGE-M3 and Qwen3-Embedding-0.6B/4B. The user picks one
 * from a dropdown (#embedding-model-select); the choice is shared by both the Semantic Search tab
 * and GraphRAG's semantic_search tool, since both call search() in this module.
 *
 * Chunk-level index (2026-07-21): corpus vectors are one row per ~300-token passage, not one row
 * per letter (see scripts/embed.py) - a long, multi-topic letter no longer dilutes into a single
 * averaged vector. Results are still deduplicated to one card per letter (best-scoring chunk
 * wins), but that card shows the actual matching excerpt, not just the letter's opening line.
 *
 * Query encoding, per model:
 *   - Primary path: Transformers.js running the model's ONNX build (meta.onnx_repo), lazy-loaded
 *     only when the user actually searches. Pooling mode (cls vs last_token) and the optional
 *     instruction prefix (Qwen3's "Instruct: ...\nQuery:" template - see the Qwen3-Embedding model
 *     cards; documents/chunks are never prefixed, only queries) both come from the model's meta,
 *     not hardcoded - get either wrong and query vectors land outside the corpus vectors' space
 *     and results become meaningless.
 *   - Fallback path: HF Inference API feature-extraction against meta.name (the original repo,
 *     not the ONNX mirror), for users who don't want the model download. Requires a user-supplied
 *     HF token, stored only in localStorage, never sent anywhere but huggingface.co. The same
 *     instruction prefix is prepended manually here too - the generic feature-extraction endpoint
 *     has no notion of sentence-transformers' named prompts.
 *   - qwen3-4b has no ONNX build offered (meta.browser_local is false, 4B params is not a
 *     reasonable browser download) - only the HF API path is available for it.
 *
 * Corpus vectors are int8-quantized (json/explore/vectors_<key>_int8.bin +
 * vectors_<key>_meta.json, dequantized here) - see scripts/export_frontend.py for the
 * quantization/matryoshka-truncation logic (bge-m3 only; Qwen3 models keep full dimension).
 *
 * All fetch/link paths are relative to the page that loads this module: html/explore.html.
 */

let modelsManifest = null; // {key: {name, dim, n_chunks, browser_local, onnx_repo, pooling, query_instruction}}
const corpusCache = new Map(); // model key -> { vectors: Float32Array[nChunks][dim], meta }
let lettersIndex = null;
let lettersById = null;
const transformersPipelines = new Map(); // model key -> pipeline instance

const MODEL_STORAGE_KEY = "explore_embedding_model";

async function loadManifest() {
  if (modelsManifest) return modelsManifest;
  const [modelsResp, indexResp] = await Promise.all([
    fetch("../json/explore/embedding_models.json"),
    fetch("../json/explore/letters_index.json"),
  ]);
  modelsManifest = await modelsResp.json();
  lettersIndex = await indexResp.json();
  lettersById = new Map(lettersIndex.map((l) => [l.id, l]));
  return modelsManifest;
}

export function getSelectedModelKey() {
  const stored = localStorage.getItem(MODEL_STORAGE_KEY);
  if (stored && modelsManifest && modelsManifest[stored]) return stored;
  // default: first browser_local model (works without a token out of the box), else first at all
  const keys = Object.keys(modelsManifest || {});
  const local = keys.find((k) => modelsManifest[k].browser_local);
  return local || keys[0];
}

export function setSelectedModelKey(key) {
  localStorage.setItem(MODEL_STORAGE_KEY, key);
}

async function loadCorpusData(modelKey) {
  await loadManifest();
  if (corpusCache.has(modelKey)) return corpusCache.get(modelKey);

  const [metaResp, binResp] = await Promise.all([
    fetch(`../json/explore/vectors_${modelKey}_meta.json`),
    fetch(`../json/explore/vectors_${modelKey}_int8.bin`),
  ]);
  const meta = await metaResp.json();
  const raw = new Int8Array(await binResp.arrayBuffer());

  const { dim, n_chunks, mins, maxs } = meta;
  const vectors = new Array(n_chunks);
  for (let i = 0; i < n_chunks; i++) {
    const vec = new Float32Array(dim);
    for (let d = 0; d < dim; d++) {
      const q = raw[i * dim + d];
      const range = maxs[d] - mins[d] || 1;
      vec[d] = ((q + 128) / 255) * range + mins[d];
    }
    // re-normalize after dequantization (quantization error can nudge the norm off 1.0)
    let norm = 0;
    for (let d = 0; d < dim; d++) norm += vec[d] * vec[d];
    norm = Math.sqrt(norm) || 1;
    for (let d = 0; d < dim; d++) vec[d] /= norm;
    vectors[i] = vec;
  }
  const entry = { vectors, meta };
  corpusCache.set(modelKey, entry);
  return entry;
}

function cosine(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot; // both are unit-normalized
}

async function embedQueryTransformersJs(modelKey, meta, query, onProgress) {
  if (!transformersPipelines.has(modelKey)) {
    onProgress?.("Loading search model (one-time download, cached afterwards)...");
    const { pipeline } = await import("https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.2.0/+esm");
    const p = await pipeline("feature-extraction", meta.onnx_repo, { dtype: "q8" });
    transformersPipelines.set(modelKey, p);
  }
  onProgress?.("Searching...");
  const input = meta.query_instruction ? `${meta.query_instruction}${query}` : query;
  const output = await transformersPipelines.get(modelKey)(input, { pooling: meta.pooling, normalize: true });
  return Array.from(output.data).slice(0, meta.dim);
}

async function embedQueryHfApi(meta, query, token) {
  const input = meta.query_instruction ? `${meta.query_instruction}${query}` : query;
  const resp = await fetch(`https://router.huggingface.co/hf-inference/models/${meta.name}/pipeline/feature-extraction`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ inputs: input, options: { wait_for_model: true } }),
  });
  if (!resp.ok) throw new Error(`HF API error ${resp.status}: ${await resp.text()}`);
  const data = await resp.json();
  // feature-extraction returns [dim] or [1][dim] depending on model wrapper
  const vec = Array.isArray(data[0]) ? data[0] : data;
  const norm = Math.sqrt(vec.reduce((s, x) => s + x * x, 0)) || 1;
  return vec.map((x) => x / norm);
}

/**
 * Runs a search; returns [{id, score, date, sender, recipient, incipit, snippet}], best-scoring
 * chunk per letter, deduplicated so each letter appears at most once.
 */
export async function search(query, { topK = 10, onProgress, modelKey } = {}) {
  await loadManifest();
  const key = modelKey || getSelectedModelKey();
  const { vectors, meta } = await loadCorpusData(key);

  const useHfApi = document.getElementById("use-hf-api")?.checked || !meta.browser_local;
  let queryVec;
  if (useHfApi) {
    const token = localStorage.getItem("hf_token");
    if (!token) throw new Error("No HF token stored. Please enter one in the field above.");
    queryVec = await embedQueryHfApi(meta, query, token);
  } else {
    queryVec = await embedQueryTransformersJs(key, meta, query, onProgress);
  }

  const bestByLetter = new Map(); // letter_id -> {score, snippet}
  for (let i = 0; i < meta.chunks.length; i++) {
    const chunk = meta.chunks[i];
    const score = cosine(vectors[i], queryVec);
    const prev = bestByLetter.get(chunk.letter_id);
    if (!prev || score > prev.score) {
      bestByLetter.set(chunk.letter_id, { score, snippet: chunk.text });
    }
  }

  const scored = [...bestByLetter.entries()].map(([id, { score, snippet }]) => {
    const entry = lettersById.get(id) || {};
    return { id, score, snippet, date: entry.date, sender: entry.sender, recipient: entry.recipient, incipit: entry.incipit };
  });
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK);
}

function truncateSnippet(text, maxLen = 400) {
  if (!text || text.length <= maxLen) return text || "";
  return text.slice(0, maxLen).replace(/\s+\S*$/, "") + "…";
}

function renderResults(results, container) {
  container.innerHTML = "";
  if (results.length === 0) {
    container.innerHTML = '<p class="status">No matches.</p>';
    return;
  }
  for (const r of results) {
    const div = document.createElement("div");
    div.className = "result-card";
    div.innerHTML = `
      <span class="score">${r.score.toFixed(3)}</span>
      <div class="meta">${r.date || "undated"} &middot; ${r.sender || "?"} &rarr; ${r.recipient || "?"}</div>
      <a href="letters/${r.id}.html" target="_blank">${r.id}</a>
      <p class="result-snippet">${truncateSnippet(r.snippet)}</p>
    `;
    container.appendChild(div);
  }
}

async function populateModelSelect(select) {
  await loadManifest();
  select.innerHTML = "";
  for (const [key, m] of Object.entries(modelsManifest)) {
    const opt = document.createElement("option");
    opt.value = key;
    const apiOnly = m.browser_local ? "" : " (HF API only)";
    opt.textContent = `${m.name}${apiOnly}`;
    select.appendChild(opt);
  }
  select.value = getSelectedModelKey();
  select.addEventListener("change", () => setSelectedModelKey(select.value));
}

export function initSearchUI() {
  const form = document.getElementById("search-form");
  const input = document.getElementById("search-input");
  const status = document.getElementById("search-status");
  const results = document.getElementById("search-results");
  const button = document.getElementById("search-button");
  const modelSelect = document.getElementById("embedding-model-select");

  if (modelSelect) populateModelSelect(modelSelect);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    button.disabled = true;
    status.textContent = "";
    try {
      const hits = await search(query, {
        topK: 10,
        modelKey: modelSelect?.value,
        onProgress: (msg) => { status.textContent = msg; },
      });
      status.textContent = `${hits.length} matches.`;
      renderResults(hits, results);
    } catch (err) {
      status.textContent = `Error: ${err.message}`;
      console.error(err);
    } finally {
      button.disabled = false;
    }
  });

  const tokenInput = document.getElementById("hf-token");
  if (tokenInput) {
    tokenInput.value = localStorage.getItem("hf_token") || "";
    tokenInput.addEventListener("change", () => {
      localStorage.setItem("hf_token", tokenInput.value.trim());
    });
  }
}
