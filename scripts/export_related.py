#!/usr/bin/env python3
"""Precomputes the neuro-symbolic "related letters" lists shown on every letter page
(html/letters/*.html, rendered by js/related.js) to json/explore/related.json.

For each full-text letter this combines the two evidence layers of the edition:
  - neural:    top BGE-M3 cosine neighbors (embeddings/bge-m3/letters.safetensors) - the same
               vectors the browser search uses, so page suggestions and live search agree
  - symbolic:  shared register mentions (>= 2 common entities) and correspondence context
               (same sender/recipient pair within +/- 90 days), mirroring
               js/explore/graph-core.js's sharedMentions()/correspondenceContext() semantics
               exactly - if those change, change this too (and vice versa)

Each related entry keeps its human-readable reasons ("shares 3 mentions", "0.61 cosine") so the
letter page can *show why* something is suggested - the citability requirement, as opposed to an
opaque "you might also like".

Usage: python scripts/export_related.py [--repo-root PATH]
"""
from __future__ import annotations

import argparse
import collections
import datetime
import json
import sys
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_pipeline import flatten_entities, load_entities, load_letters  # noqa: E402

TOP_NEIGHBORS = 5      # neural candidates per letter
MIN_SHARED = 2         # sharedMentions threshold (= graph-core.js default)
WINDOW_DAYS = 90       # correspondenceContext window (= graph-core.js default)
MAX_RELATED = 6        # entries kept per letter after merging


def day_diff(d1: str, d2: str) -> float | None:
    try:
        return abs((datetime.date.fromisoformat(d1[:10]) - datetime.date.fromisoformat(d2[:10])).days)
    except ValueError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    repo_root: Path = args.repo_root

    letters = load_letters(repo_root)
    by_id = {l["id"]: l for l in letters}
    labels = flatten_entities(load_entities(repo_root))

    emb_dir = repo_root / "embeddings/bge-m3"
    ids: list[str] = json.loads((emb_dir / "ids.json").read_text())
    matrix = load_file(str(emb_dir / "letters.safetensors"))["embeddings"].astype(np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    row = {lid: i for i, lid in enumerate(ids)}

    # symbolic index 1: entity -> mentioning letters (mirror of graph.json MENTIONS edges)
    mentioned_by = collections.defaultdict(set)
    for letter in letters:
        for bucket in letter["mentions"].values():
            for eid in bucket:
                mentioned_by[eid].add(letter["id"])

    # symbolic index 2: correspondence pair -> dated letters
    pair_letters = collections.defaultdict(list)
    for letter in letters:
        s, r = letter["sent"]["person"], letter["received"]["person"]
        date = letter["sent"]["date"] or letter["received"]["date"]
        if s and r and date:
            pair_letters[tuple(sorted((s, r)))].append((letter["id"], date))

    def meta(lid: str) -> dict:
        rec = by_id[lid]
        sender = labels.get(rec["sent"]["person"] or "", {}).get("label")
        recipient = labels.get(rec["received"]["person"] or "", {}).get("label")
        status = rec.get("publication_status") or ""
        return {
            "date": rec["sent"]["date"] or rec["received"]["date"],
            "sender": sender,
            "recipient": recipient,
            "has_page": status.startswith(("online", "preview")),
            "preview": status.startswith("preview"),
        }

    sims = matrix @ matrix.T
    related = {}
    for lid in ids:
        me = by_id[lid]
        candidates: dict[str, dict] = {}

        # neural: top cosine neighbors
        order = np.argsort(sims[row[lid]])[::-1]
        taken = 0
        for j in order:
            other = ids[j]
            if other == lid:
                continue
            candidates[other] = {"id": other, "score": round(float(sims[row[lid]][j]), 3),
                                 "reasons": [f"similar content (cosine {sims[row[lid]][j]:.2f})"]}
            taken += 1
            if taken >= TOP_NEIGHBORS:
                break

        # symbolic: shared mentions
        counts = collections.Counter()
        for bucket in me["mentions"].values():
            for eid in bucket:
                for other in mentioned_by[eid]:
                    if other != lid:
                        counts[other] += 1
        for other, n in counts.most_common():
            if n < MIN_SHARED:
                break
            reason = f"shares {n} register mentions"
            if other in candidates:
                candidates[other]["reasons"].append(reason)
            elif len(candidates) < MAX_RELATED + 4:
                candidates[other] = {"id": other, "score": None, "reasons": [reason]}

        # symbolic: correspondence context
        s, r = me["sent"]["person"], me["received"]["person"]
        my_date = me["sent"]["date"] or me["received"]["date"]
        if s and r and my_date:
            for other, date in pair_letters[tuple(sorted((s, r)))]:
                if other == lid:
                    continue
                diff = day_diff(my_date, date)
                if diff is None or diff > WINDOW_DAYS:
                    continue
                reason = f"same correspondence, {int(diff)} days apart"
                if other in candidates:
                    candidates[other]["reasons"].append(reason)
                elif len(candidates) < MAX_RELATED + 4:
                    candidates[other] = {"id": other, "score": None, "reasons": [reason]}

        ranked = sorted(candidates.values(),
                        key=lambda c: (-(len(c["reasons"]) > 1),  # corroborated first
                                       -(c["score"] or 0),
                                       -len(c["reasons"])))
        related[lid] = [{**c, **meta(c["id"])} for c in ranked[:MAX_RELATED]]

    out = {
        "method": (f"BGE-M3 cosine top-{TOP_NEIGHBORS} + shared register mentions (>= {MIN_SHARED}) "
                   f"+ same correspondence within {WINDOW_DAYS} days; corroborated entries ranked first"),
        "letters": related,
    }
    out_path = repo_root / "json/explore/related.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    n_entries = sum(len(v) for v in related.values())
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KiB): "
          f"{len(related)} letters, {n_entries} related entries")


if __name__ == "__main__":
    main()
