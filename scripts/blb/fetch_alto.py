#!/usr/bin/env python3
"""Fill the ALTO cache data/blb/_alto/ for all pages of all harvested letter units (small files;
used by match.py for date hints from the letter text and copied by download.py).

Usage:  python scripts/blb/fetch_alto.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_blb  # noqa: E402


def main():
    pages = {p["page_id"] for u in lib_blb.load_units() for p in u["pages"] if p["alto"]}
    done = failed = 0
    for i, pid in enumerate(sorted(pages), 1):
        try:
            lib_blb.cached_alto(pid)
            done += 1
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  {pid}: {e}", file=sys.stderr)
        if i % 250 == 0:
            print(f"  {i}/{len(pages)}", flush=True)
    print(f"{done} ALTO cached, {failed} failed -> {lib_blb.ALTO_CACHE}")


if __name__ == "__main__":
    main()
