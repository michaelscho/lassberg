#!/usr/bin/env python3
"""Mark the edition's Ground-Truth transcriptions in the letter register.

In the Transkribus collection (src/config.py: collection_id), every document whose title starts
with `done_` is Ground Truth (user decision 2026-10-23). This script lists the collection, maps the
`done_` documents to register keys and writes

  <note type="transcription" subtype="own" ana="gt">Transkription der Edition (Transkribus), Ground Truth; Dokument 10036509</note>

into data/register/lassberg-letters.xml (after the scan/IIIF notes; an external BLB note stays).
A Transkribus transcription implies a scan: `<note type="scan">none</note>` becomes `internal`
(docs/TEI.md: scan exists, no public URL); `online` stays.
Title forms: `done_lassberg-letter-1248` (also `_dupl`, `_duplicated`), `done_K 2911,17` /
`done_BLB_K 3123 8 4` (via the register's signatur), `done_lassberg-letter-0000-1814-04-30`
(register comment "Verzeichnis …"). Unresolved titles are reported, never guessed.

The document list is kept in build/transkribus/done_documents.tsv (docId, title, pages, key);
--offline rereads it instead of logging in. Notes are only added or updated, never removed: a
letter that loses its `done_` prefix is reported. Without --write: dry run.

Usage:  python scripts/transkribus/sync_gt.py [--offline] [--write]
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
REGISTER = REPO / "data" / "register" / "lassberg-letters.xml"
SNAPSHOT = REPO / "build" / "transkribus" / "done_documents.tsv"
RX_KEY = re.compile(r"^done_(lassberg-letter-\d{4})(?:_dupl(?:icated)?)?$")
RX_SHELF = re.compile(r"^done_(?:BLB_)?(K\s*\d.*)$")
RX_LIST = re.compile(r"^done_(lassberg-letter-0000-\d{4}-\d{2}-\d{2})$")
RX_OWN = re.compile(r'^(?P<ind>[ \t]*)<note type="transcription" subtype="own"[^>]*>.*?</note>[ \t]*$', re.M)


def fetch_done() -> list[dict]:
    sys.path.insert(0, str(REPO / "src"))
    from file_selection import TranskribusClient  # needs src/config.py (Transkribus credentials)
    return [{"docId": d.id, "title": d.title, "pages": d.pages or ""}
            for d in TranskribusClient().list_documents() if d.title.startswith("done_")]


def norm_shelf(s: str) -> str:
    """'K 3123 8 4' / 'K 3123, 8, 1' / 'K 2911,17' -> 'K3123,8,4'"""
    s = re.sub(r"^K\s*", "K", s.strip())
    return re.sub(r"[\s,]+", ",", s).replace("K,", "K")


def resolve(docs: list[dict], text: str) -> None:
    keys = set(re.findall(r'<correspDesc key="([^"]+)"', text))
    shelf = {}
    for k, s in re.findall(r'<correspDesc key="([^"]+)".*?<note type="signatur">([^<]*)</note>', text, re.S):
        if s.strip():
            shelf.setdefault(norm_shelf(s), []).append(k)
    for d in docs:
        t, d["key"] = d["title"].strip(), ""
        if m := RX_KEY.match(t):
            d["key"] = m.group(1) if m.group(1) in keys else ""
        elif m := RX_LIST.match(t):
            hit = re.search(rf'<correspDesc key="([^"]+)"(?:(?!</correspDesc>).)*?Verzeichnis {m.group(1)}', text, re.S)
            d["key"] = hit.group(1) if hit else ""
        elif m := RX_SHELF.match(t):
            ks = shelf.get(norm_shelf(m.group(1)), [])
            d["key"] = ks[0] if len(ks) == 1 else ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help=f"use {SNAPSHOT.relative_to(REPO)}")
    ap.add_argument("--write", action="store_true", help="write the register (default: dry run)")
    args = ap.parse_args()
    text = REGISTER.read_text(encoding="utf-8")
    if args.offline:
        with SNAPSHOT.open(encoding="utf-8") as f:
            docs = list(csv.DictReader(f, delimiter="\t"))
    else:
        docs = fetch_done()
    resolve(docs, text)
    SNAPSHOT.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, ["docId", "title", "pages", "key"], delimiter="\t")
        w.writeheader()
        w.writerows(sorted(docs, key=lambda d: d["title"]))

    by_key: dict[str, list[str]] = {}
    for d in docs:
        if d["key"]:
            by_key.setdefault(d["key"], []).append(str(d["docId"]))
    changed = 0
    for key, ids in sorted(by_key.items()):
        m = re.search(rf'<correspDesc key="{re.escape(key)}"[^>]*>.*?</correspDesc>', text, re.S)
        b = m.group(0)
        label = "Dokument" if len(ids) == 1 else "Dokumente"
        value = f"Transkription der Edition (Transkribus), Ground Truth; {label} {', '.join(sorted(ids))}"
        own = RX_OWN.search(b)
        if own:
            line = f'{own.group("ind")}<note type="transcription" subtype="own" ana="gt">{value}</note>'
            nb = b[:own.start()] + line + b[own.end():]
        else:
            anchor = None
            for typ in ("transcription", "iiif_canvas", "iiif_manifest", "scan"):
                found = list(re.finditer(rf'^([ \t]*)<note type="{typ}"[^\n]*$', b, re.M))
                if found:
                    anchor = found[-1]
                    break
            line = f'\n{anchor.group(1)}<note type="transcription" subtype="own" ana="gt">{value}</note>'
            nb = b[:anchor.end()] + line + b[anchor.end():]
        nb = re.sub(r'<note type="scan">none</note>', '<note type="scan">internal</note>', nb)
        if nb != b:
            text = text[:m.start()] + nb + text[m.end():]
            changed += 1
    stale = [k for k in re.findall(r'<correspDesc key="([^"]+)"(?:(?!</correspDesc>).)*?subtype="own" ana="gt"', text, re.S)
             if k not in by_key]
    unresolved = [d["title"] for d in docs if not d["key"]]
    print(f"{len(docs)} done_ documents -> {len(by_key)} register entries; "
          f"{changed} {'updated' if args.write else 'would change (dry run, --write to apply)'}")
    if unresolved:
        print(f"  unresolved ({len(unresolved)}): " + "; ".join(sorted(unresolved)))
    if stale:
        print(f"  marked gt in the register but no done_ document any more: {', '.join(stale)}")
    if args.write:
        REGISTER.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
