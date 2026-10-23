#!/usr/bin/env python3
"""Harvest the METS records of the BLB OAI set "Joseph von Laßberg" into data/blb/_oai/mets/.

Usage:  python scripts/blb/harvest.py [--force]
Existing records are kept unless --force (metadata only, ~430 requests).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_blb  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="re-fetch records already cached")
    args = ap.parse_args()
    lib_blb.METS_DIR.mkdir(parents=True, exist_ok=True)
    ids = lib_blb.list_identifiers()
    new = 0
    for oai_id in ids:
        f = lib_blb.METS_DIR / f"{oai_id.rsplit(':', 1)[1]}.xml"
        if f.exists() and not args.force:
            continue
        f.write_bytes(lib_blb.fetch_mets(oai_id))
        new += 1
    print(f"{len(ids)} records in set {lib_blb.OAI_SET}, {new} fetched -> {lib_blb.METS_DIR}")


if __name__ == "__main__":
    main()
