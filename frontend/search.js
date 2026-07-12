/**
 * Phase 7: browser-side semantic search over the corpus's BGE-M3 embeddings.
 *
 * Primary path: Transformers.js running the ONNX build of the *same* BGE-M3 model used server-
 * side (scripts/embed.py), lazy-loaded only when the user actually searches. Pooling must match
 * embed.py's setup exactly (CLS pooling + normalization) or query vectors land in a different
 * space than the corpus vectors and results become meaningless.
 *
 * Fallback path: HF Inference API feature-extraction (same model + revision as meta.json), for
 * users who don't want the ~560MB model download. Requires a user-supplied HF token, stored only
 * in localStorage, never sent anywhere but huggingface.co.
 *
 * Corpus vectors are int8-quantized (frontend/data/vectors_int8.bin + vectors_meta.json,
 * dequantized here) - see scripts/export_frontend.py for the quantization/matryoshka-truncation
 * logic and why the full 1024D was kept (BGE-M3 truncation overlap test failed the 80% bar).
 */

let corpusVectors = null; // Float32Array[nLetters][dim], dequantized once and cached
let vectorsMeta = null;
let lettersIndex = null;
let transformersPipeline = null;

async function loadCorpusData() {
  if (corpusVectors) return;
  const [metaResp, binResp, indexResp] = await Promise.all([
    fetch("data/vectors_meta.json"),
    fetch("data/vectors_int8.bin"),
    fetch("data/letters_index.json"),
  ]);
  vectorsMeta = await metaResp.json();
  lettersIndex = await indexResp.json();
  const raw = new Int8Array(await binResp.arrayBuffer());

  const { dim, n_letters, mins, maxs } = vectorsMeta;
  corpusVectors = new Array(n_letters);
  for (let i = 0; i < n_letters; i++) {
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
    corpusVectors[i] = vec;
  }
}

function cosine(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot; // both are unit-normalized
}

async function embedQueryTransformersJs(query, onProgress) {
  if (!transformersPipeline) {
    onProgress?.("Suchmodell wird geladen (~560 MB, einmalig, wird gecacht)...");
    const { pipeline } = await import("https://cdn.jsdelivr.net/npm/@huggingface/transformers@4.2.0/+esm");
    transformersPipeline = await pipeline("feature-extraction", vectorsMeta.model_name.replace("BAAI/", "Xenova/"), {
      dtype: "q8",
    });
  }
  onProgress?.("Suche läuft...");
  // BGE-M3 uses CLS pooling + normalization - must match embed.py's server-side setup exactly.
  const output = await transformersPipeline(query, { pooling: "cls", normalize: true });
  return Array.from(output.data).slice(0, vectorsMeta.dim);
}

async function embedQueryHfApi(query, token) {
  const resp = await fetch(`https://api-inference.huggingface.co/pipeline/feature-extraction/${vectorsMeta.model_name}`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ inputs: query, options: { wait_for_model: true } }),
  });
  if (!resp.ok) throw new Error(`HF API error ${resp.status}: ${await resp.text()}`);
  const data = await resp.json();
  // feature-extraction returns [dim] or [1][dim] depending on model wrapper
  const vec = Array.isArray(data[0]) ? data[0] : data;
  const norm = Math.sqrt(vec.reduce((s, x) => s + x * x, 0)) || 1;
  return vec.map((x) => x / norm);
}

/** Runs a search; returns [{id, score, date, sender, recipient, incipit}], best first. */
export async function search(query, { topK = 10, onProgress } = {}) {
  await loadCorpusData();

  const useHfApi = document.getElementById("use-hf-api")?.checked;
  let queryVec;
  if (useHfApi) {
    const token = localStorage.getItem("hf_token");
    if (!token) throw new Error("Kein HF-Token gespeichert. Bitte in den Einstellungen eintragen.");
    queryVec = await embedQueryHfApi(query, token);
  } else {
    queryVec = await embedQueryTransformersJs(query, onProgress);
  }

  const scored = lettersIndex.map((entry, i) => ({
    ...entry,
    score: cosine(corpusVectors[i], queryVec),
  }));
  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, topK);
}

function renderResults(results, container) {
  container.innerHTML = "";
  if (results.length === 0) {
    container.innerHTML = '<p class="status">Keine Treffer.</p>';
    return;
  }
  for (const r of results) {
    const div = document.createElement("div");
    div.className = "result-card";
    div.innerHTML = `
      <span class="score">${r.score.toFixed(3)}</span>
      <div class="meta">${r.date || "ohne Datum"} &middot; ${r.sender || "?"} &rarr; ${r.recipient || "?"}</div>
      <a href="../html/letters/${r.id}.html" target="_blank">${r.id}</a>
      <p>${r.incipit || ""}</p>
    `;
    container.appendChild(div);
  }
}

export function initSearchUI() {
  const form = document.getElementById("search-form");
  const input = document.getElementById("search-input");
  const status = document.getElementById("search-status");
  const results = document.getElementById("search-results");
  const button = document.getElementById("search-button");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (!query) return;
    button.disabled = true;
    status.textContent = "";
    try {
      const hits = await search(query, {
        topK: 10,
        onProgress: (msg) => { status.textContent = msg; },
      });
      status.textContent = `${hits.length} Treffer.`;
      renderResults(hits, results);
    } catch (err) {
      status.textContent = `Fehler: ${err.message}`;
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
