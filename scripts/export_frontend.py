#!/usr/bin/env python3
"""
Phase 7 of the KI-Infrastruktur pipeline: exports everything the Explore page (html/explore.html
+ js/explore/) needs into json/explore/ - quantized search vectors, a flat letters index, and
copies of the RDF/cluster artifacts (single source of truth stays in rdf/ and clustering/, this
just syncs copies for GitHub Pages to serve from one directory).

Matryoshka validation (mandatory, plan Phase 7 step 1): BGE-M3 was NOT trained with Matryoshka
Representation Learning, so truncating 1024D -> matryoshka_dim (config.yaml: frontend.
matryoshka_dim) is not guaranteed to preserve ranking quality. This script embeds
TEST_QUERIES, computes top-10 retrieval overlap between full 1024D and truncated+renormalized
vectors, and only uses the truncated dimension if overlap >= 80%; otherwise it falls back to the
full 1024D (still fine at this corpus size - int8-quantized 1024D is well under a MB).

Output (json/explore/):
  vectors_int8.bin    - flat int8 array, row-major, shape (n_letters, dim_used)
  vectors_meta.json   - dim_used, per-dimension min/max (for dequantization), ids in row order,
                        the matryoshka validation result (overlap, decision)
  letters_index.json  - id, date, sender/recipient labels, incipit (everything the results list
                        needs without further requests)
  graph.json          - copied from export_graph_json.py's output (already written there)
  edition.ttl         - copy of rdf/edition.ttl (for Oxigraph-WASM)
(overview.json and related.json are written by scripts/export_overview.py and
scripts/export_related.py respectively, not by this script)

Usage:
    python scripts/export_frontend.py [--repo-root PATH]
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_pipeline import flatten_entities, load_config, load_entities, load_letters  # noqa: E402

# 20 topically diverse test queries drawn from the corpus's actual subject matter (correspondents,
# places, manuscripts/editions discussed) - see clustering/clusters.json top_terms for how these
# were chosen.
TEST_QUERIES = [
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
]


def load_bge_m3_model(model_name: str):
    from FlagEmbedding import BGEM3FlagModel
    return BGEM3FlagModel(model_name, use_fp16=False)


def truncate_and_renorm(matrix: np.ndarray, dim: int) -> np.ndarray:
    truncated = matrix[:, :dim]
    norms = np.linalg.norm(truncated, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return truncated / norms


def top_k_ids(scores: np.ndarray, ids: list[str], k: int = 10) -> set[str]:
    top_idx = np.argsort(scores)[::-1][:k]
    return {ids[i] for i in top_idx}


def validate_matryoshka(model, corpus_matrix_1024: np.ndarray, ids: list[str], target_dim: int) -> float:
    """Returns average top-10 overlap ratio (0-1) between 1024D and target_dim retrieval."""
    query_vecs = model.encode(TEST_QUERIES, return_dense=True, return_sparse=False, return_colbert_vecs=False)["dense_vecs"]
    query_vecs = np.asarray(query_vecs, dtype=np.float32)
    query_vecs = query_vecs / np.linalg.norm(query_vecs, axis=-1, keepdims=True)

    corpus_truncated = truncate_and_renorm(corpus_matrix_1024, target_dim)
    query_truncated = truncate_and_renorm(query_vecs, target_dim)

    overlaps = []
    for i in range(len(TEST_QUERIES)):
        scores_full = corpus_matrix_1024 @ query_vecs[i]
        scores_trunc = corpus_truncated @ query_truncated[i]
        top_full = top_k_ids(scores_full, ids)
        top_trunc = top_k_ids(scores_trunc, ids)
        overlaps.append(len(top_full & top_trunc) / 10)
    return float(np.mean(overlaps))


def quantize_int8(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-dimension min/max int8 quantization. Returns (int8_matrix, mins, maxs)."""
    mins = matrix.min(axis=0)
    maxs = matrix.max(axis=0)
    ranges = np.where(maxs > mins, maxs - mins, 1.0)
    scaled = (matrix - mins) / ranges  # 0..1
    q = np.clip(np.round(scaled * 255) - 128, -128, 127).astype(np.int8)
    return q, mins, maxs


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    config = load_config(repo_root)
    frontend_cfg = config["frontend"]

    emb_dir = repo_root / "embeddings/bge-m3"
    ids = json.loads((emb_dir / "ids.json").read_text())
    matrix_1024 = load_file(str(emb_dir / "letters.safetensors"))["embeddings"].astype(np.float32)

    target_dim = frontend_cfg["matryoshka_dim"]
    model_name = config["embedding"]["primary"]["name"]

    print(f"Validating matryoshka truncation ({matrix_1024.shape[1]}D -> {target_dim}D) with {len(TEST_QUERIES)} test queries...")
    model = load_bge_m3_model(model_name)
    overlap = validate_matryoshka(model, matrix_1024, ids, target_dim)
    print(f"Average top-10 overlap: {overlap:.1%}")

    if overlap >= 0.8:
        dim_used = target_dim
        vectors = truncate_and_renorm(matrix_1024, target_dim)
        decision = f"truncated to {target_dim}D (overlap {overlap:.1%} >= 80%)"
    else:
        dim_used = matrix_1024.shape[1]
        vectors = matrix_1024
        decision = f"kept full {matrix_1024.shape[1]}D (truncation overlap {overlap:.1%} < 80%)"
    print(f"Decision: {decision}")

    q_matrix, mins, maxs = quantize_int8(vectors)

    out_dir = repo_root / "json/explore"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "vectors_int8.bin").write_bytes(q_matrix.tobytes())
    meta = {
        "dim": dim_used,
        "n_letters": len(ids),
        "ids": ids,
        "quantization": "int8_per_dim_minmax",
        "mins": mins.tolist(),
        "maxs": maxs.tolist(),
        "matryoshka_validation": {
            "source_dim": int(matrix_1024.shape[1]),
            "target_dim": target_dim,
            "test_queries": len(TEST_QUERIES),
            "avg_top10_overlap": round(overlap, 4),
            "decision": decision,
        },
        "model_name": model_name,
    }
    # Preserve a prior onnx_consistency_test result (written by test_onnx_consistency.mjs) across
    # reruns of this script - that test requires Node/a model download and isn't rerun every time
    # export_frontend.py is, so a routine rerun shouldn't silently drop its last known result.
    existing_meta_path = out_dir / "vectors_meta.json"
    if existing_meta_path.exists():
        try:
            prior = json.loads(existing_meta_path.read_text())
            if "onnx_consistency_test" in prior:
                meta["onnx_consistency_test"] = prior["onnx_consistency_test"]
        except (json.JSONDecodeError, OSError):
            pass
    existing_meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote vectors_int8.bin ({q_matrix.nbytes / 1024:.1f} KiB) and vectors_meta.json")

    # letters_index.json - everything the results list needs without further requests
    entities = flatten_entities(load_entities(repo_root))
    letters_by_id = {l["id"]: l for l in load_letters(repo_root)}
    index = []
    for lid in ids:
        rec = letters_by_id[lid]
        sender = entities.get(rec["sent"]["person"], {}).get("label") if rec["sent"]["person"] else None
        recipient = entities.get(rec["received"]["person"], {}).get("label") if rec["received"]["person"] else None
        index.append({
            "id": lid,
            "date": rec["sent"]["date"] or rec["received"]["date"],
            "sender": sender,
            "recipient": recipient,
            "incipit": rec["incipit"],
        })
    (out_dir / "letters_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote letters_index.json ({len(index)} letters)")

    # Copy: RDF dump (for Oxigraph-WASM). graph.json is written directly into json/explore/ by
    # export_graph_json.py. The clustering artifacts stay in clustering/ (internal corpus-triage
    # tool since the 2026-07 Explore rework - no longer shipped to the website).
    ttl_src = repo_root / "rdf/edition.ttl"
    if ttl_src.exists():
        shutil.copy(ttl_src, out_dir / "edition.ttl")
        print("Copied rdf/edition.ttl -> json/explore/edition.ttl")

    graph_json = out_dir / "graph.json"
    if not graph_json.exists():
        print("WARNING: json/explore/graph.json missing - run scripts/export_graph_json.py first.", file=sys.stderr)


if __name__ == "__main__":
    main()
