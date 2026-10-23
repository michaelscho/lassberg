#!/usr/bin/env python3
"""Download images + ALTO for every accepted row of build/blb/matches.tsv (accept=y) into
data/blb/<letter-key>/ and convert ALTO 3 to PAGE 2019:

  data/blb/lassberg-letter-XXXX/0001.jpg        full resolution (BLB webcache/0)
                               0001.alto.xml    ALTO 3 as delivered by the BLB
                               0001.page.xml    PAGE 2019, converted (lib_blb.alto_to_page)
                               blb.json         shelfmark, record/IIIF links, page ids, licences

Existing files are kept (resumable); --force re-fetches. data/blb/ is gitignored (~12 GB).

Usage:  python scripts/blb/download.py [--only lassberg-letter-XXXX ...] [--no-images] [--force]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_blb  # noqa: E402

MATCHES = lib_blb.REPO / "build" / "blb" / "matches.tsv"
LICENCE_TEXT = "https://creativecommons.org/licenses/by/4.0/"


def accepted() -> list[dict]:
    with MATCHES.open(encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f, delimiter="\t")
                if r["accept"].strip().lower() == "y" and r["letter_key"] and r["unit_id"]]
    dup = [k for k, n in Counter(r["letter_key"] for r in rows).items() if n > 1]
    if dup:
        sys.exit(f"letter_key accepted for several units, fix matches.tsv first: {', '.join(dup)}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*", help="letter keys to download")
    ap.add_argument("--no-images", action="store_true", help="ALTO/PAGE/blb.json only")
    ap.add_argument("--force", action="store_true", help="re-fetch existing files")
    args = ap.parse_args()
    units = {u["unit_id"]: u for u in lib_blb.load_units()}
    rows = [r for r in accepted() if not args.only or r["letter_key"] in args.only]
    stats = Counter()
    for n, r in enumerate(rows, 1):
        u = units[r["unit_id"]]
        d = lib_blb.BLB_DIR / r["letter_key"]
        d.mkdir(parents=True, exist_ok=True)
        pages = []
        for i, p in enumerate(u["pages"], 1):
            stem, pid = f"{i:04d}", p["page_id"]
            jpg, alto, page = d / f"{stem}.jpg", d / f"{stem}.alto.xml", d / f"{stem}.page.xml"
            if not args.no_images and (args.force or not jpg.exists()):
                jpg.write_bytes(lib_blb.get(lib_blb.image_url(pid)).content)
                stats["images"] += 1
            if p["alto"] and (args.force or not alto.exists()):
                data = lib_blb.cached_alto(pid)
                alto.write_bytes(data)
                page.write_bytes(lib_blb.alto_to_page(data, jpg.name))
                stats["alto"] += 1
            pages.append({"n": i, "page_id": pid, "image": jpg.name,
                          "alto": alto.name if p["alto"] else None,
                          "page": page.name if p["alto"] else None,
                          "image_url": lib_blb.image_url(pid),
                          "canvas": lib_blb.canvas_url(u["record_id"], pid)})
        meta = {
            "letter_key": r["letter_key"], "shelfmark": u["shelfmark"], "unit_type": u["unit_type"],
            "unit_id": u["unit_id"], "record_id": u["record_id"], "label": u["file_label"],
            "record_url": lib_blb.record_url(u["unit_id"]),
            "iiif_manifest": lib_blb.manifest_url(u["record_id"]),
            "iiif_canvas": pages[0]["canvas"] if pages else None,
            "urn": u["urn"], "match": {"status": r["status"], "note": r["note"]},
            "licence_images": u["licence"] or lib_blb.LICENCE_IMAGES,
            "licence_transcription": LICENCE_TEXT,
            "pages": pages,
        }
        (d / "blb.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"[{n}/{len(rows)}] {r['letter_key']} {u['shelfmark']}: {len(pages)} pages", flush=True)
    print(f"done: {len(rows)} letters, {stats['images']} images, {stats['alto']} ALTO/PAGE written -> {lib_blb.BLB_DIR}")


if __name__ == "__main__":
    main()
