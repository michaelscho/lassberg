#!/usr/bin/env python3
"""
Phase 2 of the KI-Infrastruktur pipeline: embeds every full-text letter from
`build/letters.jsonl` (has_fulltext=true) into passage-level chunks and writes static,
GitHub-friendly safetensors artifacts, once per enabled model in config.yaml (embedding.models).

Chunking (2026-07-15): letters are split into overlapping token windows (config.yaml:
embedding.chunk_tokens/chunk_overlap_tokens) and each chunk is embedded separately, rather than
pooling a whole letter into one vector - long, multi-topic letters (the Laßberg<->Uhland exchanges
especially) otherwise dilute a query-relevant passage into an average that no longer scores well,
and a single letter-level vector can't back a "here's the matching excerpt" UI. Short letters (the
corpus majority - typically one paragraph) fall under chunk_tokens and end up as exactly one
chunk, so this doesn't change anything for them.

Output (under embeddings/<model-key>/, one directory per config.yaml: embedding.models entry):
  chunks.safetensors  - float16 tensor, shape (n_chunks, dim), row order == chunk_meta.json
  chunk_meta.json     - [{id, letter_id, chunk_index, text}, ...] in tensor row order - the
                        chunk's own text is stored directly (not sliced from the letter client-side)
                        so the frontend can show the matching excerpt without shipping full letter
                        text separately
  letters.safetensors - float16 tensor, shape (n_letters, dim): mean of each letter's chunk
                        vectors, renormalized - kept for scripts/cluster.py and
                        scripts/export_related.py, which want one vector per letter and are
                        unaffected by the chunking change
  ids.json             - letter ids in letters.safetensors row order
  shas.json             - {letter_id: sha256} of the text that was chunked/embedded, for
                        incremental runs (a changed letter's old chunks are fully replaced, not
                        appended to)
  meta.json             - model name, HF revision (commit hash), dim, dtype, normalization,
                        creation date, letter/chunk counts

Usage:
    python scripts/embed.py [--model KEY|all] [--force] [--batch-size N] [--repo-root PATH]

    KEY is a key under config.yaml: embedding.models (e.g. bge-m3, qwen3-0.6b, qwen3-4b).
    Default is "all" enabled models.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file, save_file


def load_config(repo_root: Path) -> dict:
    import yaml
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


def chunk_text(text: str, chunk_tokens: int, overlap: int) -> list[str]:
    """Approximate word-based chunking (1 word ~ 1.3 tokens for German is close enough here);
    a letter shorter than chunk_tokens words becomes a single chunk unchanged."""
    words = text.split()
    if len(words) <= chunk_tokens:
        return [text]
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_tokens, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap
    return chunks


def normalize_rows(mat: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(mat, axis=-1, keepdims=True)
    norms[norms == 0] = 1.0
    return mat / norms


class BgeM3Backend:
    """CLS pooling + normalization, built into FlagEmbedding's .encode()."""

    def __init__(self, model_name: str, batch_size: int):
        from FlagEmbedding import BGEM3FlagModel
        import torch

        use_fp16 = torch.cuda.is_available()
        self.model = BGEM3FlagModel(model_name, use_fp16=use_fp16)
        self.batch_size = batch_size
        self.revision = getattr(self.model.model.config, "_commit_hash", None) or "unknown"

    def encode(self, texts: list[str]) -> np.ndarray:
        out = self.model.encode(
            texts,
            batch_size=self.batch_size,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        return normalize_rows(np.asarray(out["dense_vecs"], dtype=np.float32))

    def unload(self):
        del self.model
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class SentenceTransformerBackend:
    """Last-token pooling + instruction-prefixed queries, per the Qwen3-Embedding model cards.
    Corpus/document text uses the empty "document" prompt (i.e. no prefix) - only actual search
    queries get the instruction prefix, and that happens client-side in js/explore/search.js, not
    here."""

    def __init__(self, model_name: str, batch_size: int):
        import torch
        from sentence_transformers import SentenceTransformer

        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = SentenceTransformer(
            model_name, device=device,
            model_kwargs={"torch_dtype": torch.float16} if device == "cuda" else {},
        )
        self.batch_size = batch_size
        try:
            self.revision = self.model[0].auto_model.config._commit_hash or "unknown"
        except Exception:
            self.revision = "unknown"

    def encode(self, texts: list[str]) -> np.ndarray:
        vecs = self.model.encode(
            texts, batch_size=self.batch_size, normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vecs, dtype=np.float32)

    def unload(self):
        del self.model
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


BACKENDS = {"bge-m3": BgeM3Backend, "sentence-transformers": SentenceTransformerBackend}


def load_existing_chunks(out_dir: Path):
    """Returns (letter_id -> [(chunk_text, vector), ...], letter_id -> sha256) from the last run,
    or ({}, {}) if nothing exists yet."""
    meta_path = out_dir / "chunk_meta.json"
    tensor_path = out_dir / "chunks.safetensors"
    shas_path = out_dir / "shas.json"
    if not (meta_path.exists() and tensor_path.exists() and shas_path.exists()):
        return {}, {}
    chunk_meta = json.loads(meta_path.read_text())
    shas = json.loads(shas_path.read_text())
    tensor = load_file(str(tensor_path))["embeddings"].astype(np.float32)
    by_letter: dict[str, list] = {}
    for i, c in enumerate(chunk_meta):
        by_letter.setdefault(c["letter_id"], []).append((c["text"], tensor[i]))
    return by_letter, shas


def embed_model(key: str, model_cfg: dict, chunk_tokens: int, overlap: int,
                 letters: list[dict], repo_root: Path, batch_size: int, force: bool):
    print(f"\n=== {key} ({model_cfg['name']}) ===")
    out_dir = repo_root / "embeddings" / key
    out_dir.mkdir(parents=True, exist_ok=True)

    existing_chunks, existing_shas = ({}, {}) if force else load_existing_chunks(out_dir)

    to_process = [l for l in letters if force or l["id"] not in existing_shas
                  or existing_shas[l["id"]] != l["sha256"]]
    print(f"{len(letters)} full-text letters total, {len(to_process)} new or changed (force={force})")

    backend = None
    if to_process:
        backend_cls = BACKENDS[model_cfg["backend"]]
        backend = backend_cls(model_cfg["name"], batch_size)

    new_chunks_by_letter: dict[str, list] = {}
    n_chunks_total = 0
    interrupted_error = None
    try:
        for i, letter in enumerate(to_process):
            pieces = chunk_text(letter["text"], chunk_tokens, overlap)
            vecs = backend.encode(pieces)
            new_chunks_by_letter[letter["id"]] = list(zip(pieces, vecs))
            n_chunks_total += len(pieces)
            if (i + 1) % 20 == 0 or i + 1 == len(to_process):
                print(f"  embedded {i + 1}/{len(to_process)} letters ({n_chunks_total} chunks so far)")
    except Exception as exc:
        # For paid/rate-limited backends (hf-api) especially, losing already-embedded letters to
        # an error partway through would waste real API spend - save whatever completed so far
        # (the merge below only touches letters actually in new_chunks_by_letter; the rest keep
        # their existing_shas entry so the next run's incremental skip-logic retries just the
        # ones that didn't finish) and re-raise after saving.
        interrupted_error = exc
        print(f"  ERROR after {len(new_chunks_by_letter)}/{len(to_process)} letters embedded - "
              f"saving partial progress before re-raising: {exc}")

    # Merge: unchanged letters keep their old chunks, changed/new letters get the fresh ones,
    # letters no longer in the corpus (removed) are dropped entirely. On a partial run (see
    # except above), letters not yet reached keep whatever they had before (old chunks if any,
    # none if new) and are simply not in all_shas-matching state, so the next run retries them.
    all_ids = [l["id"] for l in letters]
    shas_by_id = {l["id"]: l["sha256"] for l in letters}
    if interrupted_error:
        all_shas = {**existing_shas, **{lid: shas_by_id[lid] for lid in new_chunks_by_letter}}
    else:
        all_shas = shas_by_id
    chunks_by_letter = {**existing_chunks, **new_chunks_by_letter}

    chunk_meta = []
    chunk_vecs = []
    letter_vecs = []
    for lid in all_ids:
        pairs = chunks_by_letter.get(lid, [])
        for idx, (text, vec) in enumerate(pairs):
            chunk_meta.append({"id": f"{lid}-c{idx}", "letter_id": lid, "chunk_index": idx, "text": text})
            chunk_vecs.append(vec)
        if pairs:
            mean_vec = normalize_rows(np.mean([v for _, v in pairs], axis=0, keepdims=True))[0]
        else:
            mean_vec = np.zeros(model_cfg["dim"], dtype=np.float32)
        letter_vecs.append(mean_vec)

    chunk_matrix = np.stack(chunk_vecs).astype(np.float16) if chunk_vecs else np.zeros((0, model_cfg["dim"]), dtype=np.float16)
    letter_matrix = np.stack(letter_vecs).astype(np.float16)

    save_file({"embeddings": chunk_matrix}, str(out_dir / "chunks.safetensors"))
    (out_dir / "chunk_meta.json").write_text(json.dumps(chunk_meta, ensure_ascii=False, indent=2), encoding="utf-8")
    save_file({"embeddings": letter_matrix}, str(out_dir / "letters.safetensors"))
    (out_dir / "ids.json").write_text(json.dumps(all_ids, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "shas.json").write_text(json.dumps(all_shas, ensure_ascii=False, indent=2), encoding="utf-8")

    meta = {
        "model_name": model_cfg["name"],
        "model_revision": backend.revision if backend else "unchanged",
        "dim": model_cfg["dim"],
        "dtype": "float16",
        "normalized": True,
        "created": datetime.now(timezone.utc).isoformat(),
        "n_letters": len(all_ids),
        "n_chunks": len(chunk_meta),
        "chunk_tokens": chunk_tokens,
        "chunk_overlap_tokens": overlap,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {chunk_matrix.shape[0]} chunk vectors ({chunk_matrix.shape[0] / max(len(all_ids),1):.2f}/letter) "
          f"and {letter_matrix.shape[0]} letter vectors to {out_dir}/")

    if backend:
        backend.unload()

    if interrupted_error:
        raise interrupted_error


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--model", default="all", help="key under embedding.models, or 'all' (default)")
    parser.add_argument("--force", action="store_true", help="re-embed all letters, ignore cache")
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    config = load_config(repo_root)
    emb_cfg = config["embedding"]
    models = emb_cfg["models"]

    if args.model == "all":
        keys = [k for k, v in models.items() if v.get("enabled", False)]
    else:
        if args.model not in models:
            raise SystemExit(f"Unknown model key '{args.model}'. Known: {list(models)}")
        keys = [args.model]

    letters = load_fulltext_letters(repo_root)
    print(f"{len(letters)} full-text letters to consider for embedding")

    for key in keys:
        model_cfg = models[key]
        if not model_cfg.get("enabled", False):
            print(f"Skipping {key}: disabled in config.yaml")
            continue
        embed_model(
            key, model_cfg, emb_cfg["chunk_tokens"], emb_cfg["chunk_overlap_tokens"],
            letters, repo_root, args.batch_size, args.force,
        )


if __name__ == "__main__":
    main()
