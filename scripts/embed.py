#!/usr/bin/env python3
"""
Phase 2 of the KI-Infrastruktur pipeline: embeds every full-text letter from
`build/letters.jsonl` (has_fulltext=true) with BGE-M3 and writes a static, GitHub-friendly
safetensors artifact.

Output (under embeddings/<model-dir>/):
  letters.safetensors  - float16 tensor, shape (n_letters, dim), row order == ids.json
  ids.json             - letter ids in tensor row order (the only ordering key)
  shas.json            - {letter_id: sha256} of the text that was embedded, for incremental runs
  meta.json            - model name, HF revision (commit hash), dim, dtype, normalization,
                          creation date, letter count

Incremental behaviour: existing tensor + shas.json are loaded first; only letters that are new or
whose `sha256` (as recorded in letters.jsonl by parse_tei.py) changed are re-embedded. Everything
else is carried over unchanged. Use --force to re-embed all letters regardless.

Long letters (> max_tokens) are split into overlapping chunks, embedded separately, and the
resulting vectors are averaged and re-normalized (see docs at CHUNK_OVERLAP_TOKENS below).

Usage:
    python scripts/embed.py [--model primary|secondary] [--force] [--batch-size N] [--repo-root PATH]
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml
from safetensors.numpy import load_file, save_file

CHUNK_OVERLAP_TOKENS = 200  # words, approximated as whitespace-split tokens (see chunk_text)


def load_config(repo_root: Path) -> dict:
    with (repo_root / "config.yaml").open() as fh:
        return yaml.safe_load(fh)


def load_fulltext_letters(repo_root: Path) -> list[dict]:
    letters = []
    with (repo_root / "build/letters.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            if rec["has_fulltext"] and rec["text"]:
                letters.append(rec)
    letters.sort(key=lambda r: r["id"])  # stable, alphabetical == numeric here
    return letters


def chunk_text(text: str, max_tokens: int, overlap: int = CHUNK_OVERLAP_TOKENS) -> list[str]:
    """Approximate word-based chunking (1 word ~ 1.3 tokens for German is close enough here;
    we chunk conservatively at max_tokens words, well under the true token budget)."""
    words = text.split()
    if len(words) <= max_tokens:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + max_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


class BgeM3Backend:
    def __init__(self, model_name: str, batch_size: int):
        from FlagEmbedding import BGEM3FlagModel
        import torch

        use_fp16 = torch.cuda.is_available()
        self.model = BGEM3FlagModel(model_name, use_fp16=use_fp16)
        self.batch_size = batch_size
        self.revision = getattr(self.model.model.config, "_commit_hash", None) or "unknown"

    def encode(self, texts: list[str], max_tokens: int) -> np.ndarray:
        out = self.model.encode(
            texts,
            batch_size=self.batch_size,
            max_length=max_tokens,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return np.asarray(out["dense_vecs"], dtype=np.float32)


def normalize(vec: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


def embed_letter(backend: BgeM3Backend, text: str, max_tokens: int) -> np.ndarray:
    chunks = chunk_text(text, max_tokens)
    vecs = backend.encode(chunks, max_tokens)
    if len(chunks) == 1:
        return normalize(vecs[0])
    return normalize(vecs.mean(axis=0))


def load_existing(out_dir: Path) -> tuple[dict[str, np.ndarray], dict[str, str]]:
    """Returns (id -> float32 vector, id -> sha256) for whatever was embedded last run."""
    ids_path = out_dir / "ids.json"
    tensor_path = out_dir / "letters.safetensors"
    shas_path = out_dir / "shas.json"
    if not (ids_path.exists() and tensor_path.exists() and shas_path.exists()):
        return {}, {}
    ids = json.loads(ids_path.read_text())
    shas = json.loads(shas_path.read_text())
    tensor = load_file(str(tensor_path))["embeddings"].astype(np.float32)
    vectors = {lid: tensor[i] for i, lid in enumerate(ids)}
    return vectors, shas


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--model", choices=["primary", "secondary"], default="primary")
    parser.add_argument("--force", action="store_true", help="re-embed all letters, ignore cache")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    config = load_config(repo_root)
    emb_config = config["embedding"][args.model]
    if args.model == "secondary" and not emb_config.get("enabled", False):
        print("Secondary embedding model is disabled in config.yaml (embedding.secondary.enabled: false). Exiting.")
        return

    model_dir_name = "bge-m3" if args.model == "primary" else "qwen3"
    out_dir = repo_root / "embeddings" / model_dir_name
    out_dir.mkdir(parents=True, exist_ok=True)

    letters = load_fulltext_letters(repo_root)
    print(f"{len(letters)} full-text letters to consider for embedding")

    existing_vectors, existing_shas = ({}, {}) if args.force else load_existing(out_dir)

    max_tokens = emb_config["max_tokens"]
    backend = BgeM3Backend(emb_config["name"], args.batch_size)

    to_embed = [l for l in letters if l["id"] not in existing_shas or existing_shas[l["id"]] != l["sha256"]]
    print(f"{len(to_embed)} letters new or changed since last run (force={args.force})")

    n_chunked = 0
    new_vectors: dict[str, np.ndarray] = {}
    for i, letter in enumerate(to_embed):
        chunks = chunk_text(letter["text"], max_tokens)
        if len(chunks) > 1:
            n_chunked += 1
        new_vectors[letter["id"]] = embed_letter(backend, letter["text"], max_tokens)
        if (i + 1) % 20 == 0 or i + 1 == len(to_embed):
            print(f"  embedded {i + 1}/{len(to_embed)}")

    if n_chunked:
        print(f"{n_chunked} letters required chunking (> {max_tokens} words)")

    # Merge: keep vectors for unchanged letters, overwrite/add changed ones, drop letters that
    # no longer exist in letters.jsonl (e.g. removed).
    all_ids = [l["id"] for l in letters]
    all_shas = {l["id"]: l["sha256"] for l in letters}
    vectors_by_id = {**existing_vectors, **new_vectors}
    matrix = np.stack([vectors_by_id[i] for i in all_ids]).astype(np.float16)

    save_file({"embeddings": matrix}, str(out_dir / "letters.safetensors"))
    (out_dir / "ids.json").write_text(json.dumps(all_ids, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "shas.json").write_text(json.dumps(all_shas, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "model_name": emb_config["name"],
        "model_revision": backend.revision,
        "dim": matrix.shape[1],
        "dtype": "float16",
        "normalized": True,
        "created": datetime.now(timezone.utc).isoformat(),
        "n_letters": len(all_ids),
        "chunk_overlap_tokens": CHUNK_OVERLAP_TOKENS,
        "max_tokens": max_tokens,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {matrix.shape[0]} vectors x {matrix.shape[1]}d to {out_dir}/letters.safetensors "
          f"({(out_dir / 'letters.safetensors').stat().st_size / 1024:.1f} KiB)")

    # Self-similarity acceptance test: stored (fp16, possibly chunk-averaged) vector vs. a fresh
    # full-precision re-embedding of the same text, for one sample letter.
    if to_embed:
        sample = to_embed[0]
        fresh = embed_letter(backend, sample["text"], max_tokens)
        stored = matrix[all_ids.index(sample["id"])].astype(np.float32)
        cos_sim = float(np.dot(fresh, stored) / (np.linalg.norm(fresh) * np.linalg.norm(stored)))
        print(f"Self-similarity test on {sample['id']}: cosine={cos_sim:.6f} ({'PASS' if cos_sim > 0.999 else 'FAIL'})")


if __name__ == "__main__":
    main()
