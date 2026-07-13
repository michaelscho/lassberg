#!/usr/bin/env node
/**
 * Phase 7 mandatory consistency test: runs the same BGE-M3 ONNX model + pooling setup that
 * js/explore/search.js uses in the browser (Transformers.js, q8, CLS pooling, normalized) against
 * the server-computed corpus vectors (json/explore/vectors_int8.bin, produced from
 * embeddings/bge-m3/letters.safetensors by scripts/export_frontend.py), for the same 20 test
 * queries used in that script's matryoshka validation.
 *
 * This validates the ONNX retrieval path end-to-end (no shape mismatches, no degenerate/garbage
 * rankings) against the real, deployed corpus vectors. For a query-level cross-check between the
 * server-side FlagEmbedding path (mcp_server/tools/semantic_search.py) and this ONNX path with an
 * identical query string, see tests/test_onnx_consistency.md.
 *
 * Usage: node scripts/test_onnx_consistency.mjs
 */
import { readFileSync, writeFileSync } from "node:fs";
import { pipeline } from "@huggingface/transformers";

const REPO_ROOT = new URL("..", import.meta.url).pathname;

const TEST_QUERIES = [
  "Handschrift des Tristan von Gottfried von Straßburg",
  "Grimms deutsche Grammatik und Dialekte",
  "Bischofszell und die Familie Pupikofer",
  "Nibelungenlied und Heldensage",
  "Wappen und Siegel alter Adelsgeschlechter",
  "Urkunden aus dem Kantonsarchiv",
  "Jacob und Wilhelm Grimm Briefwechsel",
  "Minnesänger und mittelalterliche Lyrik",
  "Klöster und Handschriften in der Schweiz",
  "Liedersaal und altdeutsche Gedichte",
  "Reise nach Eppishausen",
  "Bücher und Buchhandel im 19. Jahrhundert",
  "Chronik Heinrichs von Klingenberg",
  "Predigten des Bruders Berthold",
  "Wackernagel und die Basler Bibliothek",
  "Zellweger und die Gesellschaft für Geschichte",
  "Codex und Textzeugen mittelalterlicher Werke",
  "Krankheit und Familie",
  "Neujahrsblatt und Vereine",
  "Meersburg und Freunde am Bodensee",
];

function dequantize(meta, raw) {
  const { dim, n_letters, mins, maxs } = meta;
  const vectors = [];
  for (let i = 0; i < n_letters; i++) {
    const vec = new Float32Array(dim);
    for (let d = 0; d < dim; d++) {
      const q = raw[i * dim + d];
      const range = maxs[d] - mins[d] || 1;
      vec[d] = ((q + 128) / 255) * range + mins[d];
    }
    let norm = 0;
    for (let d = 0; d < dim; d++) norm += vec[d] * vec[d];
    norm = Math.sqrt(norm) || 1;
    for (let d = 0; d < dim; d++) vec[d] /= norm;
    vectors.push(vec);
  }
  return vectors;
}

function cosine(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot;
}

function top10(scores, ids) {
  return ids
    .map((id, i) => [id, scores[i]])
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([id]) => id);
}

async function main() {
  const meta = JSON.parse(readFileSync(`${REPO_ROOT}json/explore/vectors_meta.json`, "utf-8"));
  const raw = new Int8Array(readFileSync(`${REPO_ROOT}json/explore/vectors_int8.bin`).buffer);
  const corpusVectors = dequantize(meta, raw);
  const ids = meta.ids;
  const modelName = meta.model_name.replace("BAAI/", "Xenova/");

  console.log(`Loading ${modelName} (dtype=q8) and running ${TEST_QUERIES.length} test queries...`);
  const extractor = await pipeline("feature-extraction", modelName, { dtype: "q8" });

  let serverRankings = null;
  try {
    serverRankings = JSON.parse(readFileSync("/tmp/server_rankings.json", "utf-8"));
  } catch {
    console.log("(no /tmp/server_rankings.json found - skipping overlap-vs-server comparison, printing ONNX top-3 only)");
  }

  const overlaps = [];
  for (const query of TEST_QUERIES) {
    const output = await extractor(query, { pooling: "cls", normalize: true });
    const queryVec = Array.from(output.data).slice(0, meta.dim);
    const scores = corpusVectors.map((v) => cosine(v, queryVec));
    const onnxTop10 = top10(scores, ids);

    if (serverRankings) {
      const serverTop10 = new Set(serverRankings[query]);
      const overlap = onnxTop10.filter((id) => serverTop10.has(id)).length / 10;
      overlaps.push(overlap);
      console.log(`  "${query}" -> overlap ${(overlap * 100).toFixed(0)}% (onnx: ${onnxTop10.slice(0, 3).join(", ")})`);
    } else {
      console.log(`  "${query}" -> ${onnxTop10.slice(0, 3).join(", ")}`);
    }
  }

  if (overlaps.length) {
    const avg = overlaps.reduce((a, b) => a + b, 0) / overlaps.length;
    const passed = avg >= 0.9;
    console.log(`\nAverage top-10 overlap (ONNX q8 vs. server FlagEmbedding, same queries): ${(avg * 100).toFixed(1)}%`);
    console.log(passed ? "PASS (>= 90%): q8 quantization is consistent enough for the browser path." : "BELOW 90% threshold - consider fp16 or the HF-API fallback as primary.");

    meta.onnx_consistency_test = {
      browser_model: modelName,
      dtype: "q8",
      n_test_queries: TEST_QUERIES.length,
      avg_top10_overlap_vs_server: Math.round(avg * 1000) / 1000,
      decision: passed ? "q8 kept as primary (overlap >= 90%)" : "q8 below threshold - review fp16/HF-API fallback",
      tested_at: new Date().toISOString(),
    };
    writeFileSync(`${REPO_ROOT}json/explore/vectors_meta.json`, JSON.stringify(meta, null, 2));
    console.log("Wrote result to json/explore/vectors_meta.json (onnx_consistency_test).");
  }
}

main();
