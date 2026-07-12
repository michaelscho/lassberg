"""Pure-function semantic search over the BGE-M3 letter embeddings. No MCP dependency in this
module - `mcp_server/server.py` registers `semantic_search()` as a tool; the function itself can
be imported and called from plain scripts, other agent frameworks, tests, etc.

Data read (all static, no services required):
  build/letters.jsonl          - metadata (date, sender/receiver ids, incipit)
  build/entities.json          - id -> label lookups for sender/receiver
  embeddings/bge-m3/letters.safetensors + ids.json - the corpus vectors (170 full-text letters)

The BGE-M3 query model is loaded lazily on first call and cached at module level so repeated tool
calls in one server process don't reload it.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

_model = None
_ids: list[str] | None = None
_matrix: np.ndarray | None = None
_letters_by_id: dict | None = None
_entities_by_id: dict | None = None


def _load_model():
    global _model
    if _model is None:
        from FlagEmbedding import BGEM3FlagModel
        config = json.loads((REPO_ROOT / "embeddings/bge-m3/meta.json").read_text())
        _model = BGEM3FlagModel(config["model_name"], use_fp16=False)
    return _model


def _load_data():
    global _ids, _matrix, _letters_by_id, _entities_by_id
    if _ids is None:
        emb_dir = REPO_ROOT / "embeddings/bge-m3"
        _ids = json.loads((emb_dir / "ids.json").read_text())
        _matrix = load_file(str(emb_dir / "letters.safetensors"))["embeddings"].astype(np.float32)

        _letters_by_id = {}
        with (REPO_ROOT / "build/letters.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                _letters_by_id[rec["id"]] = rec

        _entities_by_id = {}
        entities = json.loads((REPO_ROOT / "build/entities.json").read_text())
        for bucket in entities.values():
            _entities_by_id.update(bucket)
    return _ids, _matrix, _letters_by_id, _entities_by_id


def _label(entity_id: str | None) -> str | None:
    if not entity_id or _entities_by_id is None:
        return entity_id
    ent = _entities_by_id.get(entity_id)
    return ent["label"] if ent else entity_id


def semantic_search(
    query: str,
    top_k: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
) -> list[dict]:
    """Cosine-similarity search over the corpus's BGE-M3 letter embeddings.

    Args:
        query: natural-language query (German or English; BGE-M3 is multilingual).
        top_k: number of results to return.
        date_from: optional ISO date (YYYY-MM-DD) lower bound (inclusive) on the letter's
            sent-or-received date.
        date_to: optional ISO date (YYYY-MM-DD) upper bound (inclusive).

    Returns:
        List of {id, score, date, sender, recipient, incipit}, best match first. `id` is the
        canonical "lassberg-letter-NNNN" form (4-digit zero-padded) - always use and report this
        exact string (e.g. "lassberg-letter-0952"), not just the bare number, when referring to a
        result; it's also what get_letter()/graph_query() expect. Only covers the ~170 letters
        that have full text (has_fulltext=true) - register-only letters have no embedding.
    """
    ids, matrix, letters_by_id, _ = _load_data()
    model = _load_model()

    query_vec = model.encode([query], return_dense=True, return_sparse=False, return_colbert_vecs=False)["dense_vecs"][0]
    query_vec = np.asarray(query_vec, dtype=np.float32)
    query_vec = query_vec / np.linalg.norm(query_vec)

    scores = matrix @ query_vec  # both sides are unit-normalized -> dot product == cosine sim

    candidates = []
    for i, letter_id in enumerate(ids):
        rec = letters_by_id[letter_id]
        letter_date = rec["sent"]["date"] or rec["received"]["date"]
        if date_from and (not letter_date or letter_date < date_from):
            continue
        if date_to and (not letter_date or letter_date > date_to):
            continue
        candidates.append((float(scores[i]), letter_id, rec, letter_date))

    candidates.sort(key=lambda c: c[0], reverse=True)

    results = []
    for score, letter_id, rec, letter_date in candidates[:top_k]:
        results.append({
            "id": letter_id,
            "score": round(score, 4),
            "date": letter_date,
            "sender": _label(rec["sent"]["person"]),
            "recipient": _label(rec["received"]["person"]),
            "incipit": rec["incipit"],
        })
    return results
