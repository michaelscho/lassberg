"""Identify a manuscript via the HSP: local mirror index first, optionally live HSP search.

Usage: python scripts/manuscripts/hsp_lookup.py "<query>" [--live] [--limit N]
Output: one hit per line (JSON with --json). Live hits are Kulturobjekte from the HSP search
(spell-correction applies: always verify shelfmark/title).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_hsp as hsp  # noqa: E402


def lookup(query: str, live: bool = False, limit: int = 10) -> list[dict]:
    hits = [{"source": "local", **h} for h in hsp.local_search(query, limit)]
    if live:
        known = {h["hsp_id"] for h in hits}
        try:
            for k in hsp.search(query, rows=limit):
                if k["id"] in known:
                    continue
                hits.append({"source": "live", "hsp_id": k["id"], "witness_id": None,
                             "shelfmark": k.get("idno-display"),
                             "msname": hsp.clean_kod_title(k.get("title-display")),
                             "settlement": k.get("settlement-display"),
                             "repository": k.get("repository-display"),
                             "date": "; ".join(k.get("orig-date-lang-display") or []),
                             "orig_place": k.get("orig-place-display"), "score": None})
        except hsp.HspError as exc:
            print(f"live search failed: {exc}", file=sys.stderr)
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--limit", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    hits = lookup(a.query, a.live, a.limit)
    if a.json:
        print(json.dumps(hits, ensure_ascii=False, indent=1))
        return
    for h in hits:
        print(f"[{h['source']}] {h['hsp_id']} | {h.get('shelfmark')} | {h.get('msname')} | "
              f"{h.get('settlement') or ''} {h.get('repository') or ''} {h.get('date') or ''} "
              f"| {h.get('witness_id') or '-'} | {h.get('snippet') or ''}".replace("  ", " "))
    if not hits:
        print("(no hits)")


if __name__ == "__main__":
    main()
