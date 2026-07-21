#!/usr/bin/env python3
"""
Phase 7 of the KI-Infrastruktur pipeline: exports everything the Explore page (html/explore.html
+ js/explore/) needs into json/explore/ - quantized, chunk-level search vectors (one set per
enabled model in config.yaml: embedding.models), a flat letters index, and copies of the RDF
artifacts (single source of truth stays in rdf/, this just syncs a copy for GitHub Pages to serve
from one directory).

Per-model output (json/explore/), row order shared between the .bin and its meta's "chunks" list:
  vectors_<key>_int8.bin   - flat int8 array, row-major, shape (n_chunks, dim_used)
  vectors_<key>_meta.json  - dim_used, per-dimension min/max (for dequantization), model_name,
                             browser_local, onnx_repo, chunk_tokens/overlap, and the chunk list
                             itself ({letter_id, chunk_index, text}) - the chunk's own text ships
                             here so the frontend can show the matching excerpt without a second
                             request for full letter text.
Shared output:
  embedding_models.json    - {key: {name, dim, browser_local, onnx_repo, n_chunks}} manifest so
                             the frontend can build the model dropdown without fetching every
                             per-model meta file up front.
  letters_index.json       - id, date, sender/recipient labels, incipit (model-independent;
                             everything the results list needs beyond the matched excerpt)
  graph.json                - copied from export_graph_json.py's output (already written there)
  edition.ttl                - copy of rdf/edition.ttl (for Oxigraph-WASM)
(overview.json and related.json are written by scripts/export_overview.py and
scripts/export_related.py respectively, not by this script)

Matryoshka truncation (bge-m3 only): BGE-M3 was NOT trained with Matryoshka Representation
Learning, so truncating 1024D -> matryoshka_dim (config.yaml: frontend.matryoshka_dim) is not
guaranteed to preserve ranking quality. This script embeds TEST_QUERIES, computes top-10 retrieval
overlap between full 1024D and truncated+renormalized vectors (at the chunk level), and only uses
the truncated dimension if overlap >= 80%; otherwise it falls back to the full 1024D. The Qwen3
models keep their full dimension unconditionally - no equivalent validated truncation pipeline for
them yet, and at this corpus size int8-quantized full-dimension vectors are still well under a few
MB.

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
# were chosen. Used only for the bge-m3 matryoshka validation.
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


def truncate_and_renorm(matrix: np.ndarray, dim: int) -> np.ndarray:
    truncated = matrix[:, :dim]
    norms = np.linalg.norm(truncated, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return truncated / norms


def top_k_ids(scores: np.ndarray, ids: list[str], k: int = 10) -> set[str]:
    top_idx = np.argsort(scores)[::-1][:k]
    return {ids[i] for i in top_idx}


def validate_bge_m3_matryoshka(corpus_matrix: np.ndarray, chunk_ids: list[str], target_dim: int, model_name: str) -> float:
    """Returns average top-10 overlap ratio (0-1) between full-dim and target_dim chunk retrieval."""
    from FlagEmbedding import BGEM3FlagModel

    model = BGEM3FlagModel(model_name, use_fp16=False)
    query_vecs = model.encode(TEST_QUERIES, return_dense=True, return_sparse=False, return_colbert_vecs=False)["dense_vecs"]
    query_vecs = np.asarray(query_vecs, dtype=np.float32)
    query_vecs = query_vecs / np.linalg.norm(query_vecs, axis=-1, keepdims=True)

    corpus_truncated = truncate_and_renorm(corpus_matrix, target_dim)
    query_truncated = truncate_and_renorm(query_vecs, target_dim)

    overlaps = []
    for i in range(len(TEST_QUERIES)):
        scores_full = corpus_matrix @ query_vecs[i]
        scores_trunc = corpus_truncated @ query_truncated[i]
        overlaps.append(len(top_k_ids(scores_full, chunk_ids) & top_k_ids(scores_trunc, chunk_ids)) / 10)
    return float(np.mean(overlaps))


def quantize_int8(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Per-dimension min/max int8 quantization. Returns (int8_matrix, mins, maxs)."""
    mins = matrix.min(axis=0)
    maxs = matrix.max(axis=0)
    ranges = np.where(maxs > mins, maxs - mins, 1.0)
    scaled = (matrix - mins) / ranges  # 0..1
    q = np.clip(np.round(scaled * 255) - 128, -128, 127).astype(np.int8)
    return q, mins, maxs


def export_model(key: str, model_cfg: dict, repo_root: Path, out_dir: Path, frontend_cfg: dict) -> dict:
    emb_dir = repo_root / "embeddings" / key
    chunk_meta = json.loads((emb_dir / "chunk_meta.json").read_text())
    matrix = load_file(str(emb_dir / "chunks.safetensors"))["embeddings"].astype(np.float32)
    chunk_ids = [c["id"] for c in chunk_meta]

    if key == "bge-m3":
        target_dim = frontend_cfg["matryoshka_dim"]
        print(f"[{key}] Validating matryoshka truncation ({matrix.shape[1]}D -> {target_dim}D) "
              f"with {len(TEST_QUERIES)} test queries...")
        overlap = validate_bge_m3_matryoshka(matrix, chunk_ids, target_dim, model_cfg["name"])
        print(f"[{key}] Average top-10 overlap: {overlap:.1%}")
        if overlap >= 0.8:
            dim_used = target_dim
            vectors = truncate_and_renorm(matrix, target_dim)
            decision = f"truncated to {target_dim}D (overlap {overlap:.1%} >= 80%)"
        else:
            dim_used = matrix.shape[1]
            vectors = matrix
            decision = f"kept full {matrix.shape[1]}D (truncation overlap {overlap:.1%} < 80%)"
        print(f"[{key}] Decision: {decision}")
        matryoshka_info = {
            "source_dim": int(matrix.shape[1]), "target_dim": target_dim,
            "test_queries": len(TEST_QUERIES), "avg_top10_overlap": round(overlap, 4),
            "decision": decision,
        }
    else:
        dim_used = matrix.shape[1]
        vectors = matrix
        matryoshka_info = None
        print(f"[{key}] Keeping full {dim_used}D (no matryoshka validation for this backend)")

    q_matrix, mins, maxs = quantize_int8(vectors)
    (out_dir / f"vectors_{key}_int8.bin").write_bytes(q_matrix.tobytes())

    meta = {
        "model_key": key,
        "model_name": model_cfg["name"],
        "dim": dim_used,
        "n_chunks": len(chunk_meta),
        "quantization": "int8_per_dim_minmax",
        "mins": mins.tolist(),
        "maxs": maxs.tolist(),
        "browser_local": model_cfg.get("browser_local", False),
        "onnx_repo": model_cfg.get("onnx_repo"),
        "pooling": model_cfg.get("pooling", "cls"),
        "query_instruction": model_cfg.get("query_instruction", ""),
        "chunks": chunk_meta,
    }
    if matryoshka_info:
        meta["matryoshka_validation"] = matryoshka_info
    (out_dir / f"vectors_{key}_meta.json").write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")
    print(f"[{key}] Wrote vectors_{key}_int8.bin ({q_matrix.nbytes / 1024:.1f} KiB, "
          f"{len(chunk_meta)} chunks) and vectors_{key}_meta.json")

    return {
        "name": model_cfg["name"], "dim": dim_used, "n_chunks": len(chunk_meta),
        "browser_local": model_cfg.get("browser_local", False), "onnx_repo": model_cfg.get("onnx_repo"),
        "pooling": model_cfg.get("pooling", "cls"), "query_instruction": model_cfg.get("query_instruction", ""),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    config = load_config(repo_root)
    frontend_cfg = config["frontend"]
    models_cfg = config["embedding"]["models"]

    out_dir = repo_root / "json/explore"
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {}
    for key, model_cfg in models_cfg.items():
        if not model_cfg.get("enabled", False):
            continue
        emb_dir = repo_root / "embeddings" / key
        if not (emb_dir / "chunks.safetensors").exists():
            print(f"WARNING: embeddings/{key}/chunks.safetensors missing - run "
                  f"'python scripts/embed.py --model {key}' first. Skipping.", file=sys.stderr)
            continue
        manifest[key] = export_model(key, model_cfg, repo_root, out_dir, frontend_cfg)

    (out_dir / "embedding_models.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWrote embedding_models.json ({len(manifest)} models: {', '.join(manifest)})")

    # letters_index.json - everything the results list needs beyond the matched excerpt,
    # model-independent (built once from the register/entities, not from any embedding run).
    letters = load_letters(repo_root)
    entities = flatten_entities(load_entities(repo_root))
    letters_by_id = {l["id"]: l for l in letters}
    index = []
    for lid, rec in letters_by_id.items():
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
    # export_graph_json.py.
    ttl_src = repo_root / "rdf/edition.ttl"
    if ttl_src.exists():
        shutil.copy(ttl_src, out_dir / "edition.ttl")
        print("Copied rdf/edition.ttl -> json/explore/edition.ttl")

    graph_json = out_dir / "graph.json"
    if not graph_json.exists():
        print("WARNING: json/explore/graph.json missing - run scripts/export_graph_json.py first.", file=sys.stderr)


if __name__ == "__main__":
    main()
