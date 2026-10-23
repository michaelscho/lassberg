#!/usr/bin/env python3
"""Write BLB shelfmark, record link and IIIF links of the accepted rows of build/blb/matches.tsv
(accept=y) into data/register/lassberg-letters.xml:

  <note type="signatur">K 2911,16,3</note>                     only if empty (else reported)
  <note type="url_facsimile" target="…/titleinfo/<id>">…</note>  BLB record of the letter; only if empty
  <note type="scan">online</note>
  <note type="iiif_manifest">…/i3f/v20/<recordId>/manifest</note>
  <note type="iiif_canvas">…/canvas/<pageId></note>             first page; only for letters inside
                                                                 a folder (manifest covers the folder)
  aufbewahrungsort/-institution are filled (Karlsruhe / Badische Landesbibliothek) only if empty.

Edits are line-based inside the entry's <correspDesc>…</correspDesc>, so the rest of the file
stays byte-identical (as in scripts/sync_letter_status.py). Without --write: dry run.

Usage:  python scripts/blb/apply_register.py [--write]
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_blb  # noqa: E402
from download import accepted  # noqa: E402

REGISTER = lib_blb.REPO / "data" / "register" / "lassberg-letters.xml"


def note_rx(typ: str) -> re.Pattern:
    return re.compile(rf'^(?P<ind>[ \t]*)<note type="{typ}"(?P<attrs>[^>]*?)(?:/>|>(?P<val>.*?)</note>)[ \t]*$', re.M)


def set_note(block: str, typ: str, value: str, target: bool = False, overwrite: bool = True,
             after: str = "scan") -> tuple[str, str | None]:
    """-> (new block, message if an existing different value was kept)"""
    attrs = f' target="{escape(value)}"' if target else ""
    m = note_rx(typ).search(block)
    if m:
        cur = (m.group("val") or "").strip()
        if cur == value:
            return block, None
        if cur and not overwrite:
            return block, f"{typ}: kept '{cur}' (BLB: '{value}')"
        line = f'{m.group("ind")}<note type="{typ}"{attrs}>{escape(value)}</note>'
        return block[:m.start()] + line + block[m.end():], None
    a = note_rx(after).search(block)
    line = f'\n{a.group("ind")}<note type="{typ}"{attrs}>{escape(value)}</note>'
    return block[:a.end()] + line + block[a.end():], None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="write the register (default: dry run)")
    args = ap.parse_args()
    units = {u["unit_id"]: u for u in lib_blb.load_units()}
    text = REGISTER.read_text(encoding="utf-8")
    changed, kept = 0, []
    for r in accepted():
        u = units[r["unit_id"]]
        m = re.search(rf'<correspDesc key="{re.escape(r["letter_key"])}"[^>]*>.*?</correspDesc>', text, re.S)
        if not m:
            kept.append(f"{r['letter_key']}: not in register")
            continue
        b = m.group(0)
        edits = [("signatur", u["shelfmark"], False, False, "aufbewahrungsinstitution"),
                 ("url_facsimile", lib_blb.record_url(u["unit_id"]), True, False, "signatur"),
                 ("scan", "online", False, True, "url_facsimile"),
                 ("iiif_manifest", lib_blb.manifest_url(u["record_id"]), False, True, "scan")]
        if u["in_folder"] and u["pages"]:
            edits.append(("iiif_canvas", lib_blb.canvas_url(u["record_id"], u["pages"][0]["page_id"]),
                          False, True, "iiif_manifest"))
        edits += [("aufbewahrungsort", "Karlsruhe", False, False, "journalnummer"),
                  ("aufbewahrungsinstitution", "Badische Landesbibliothek", False, False, "aufbewahrungsort")]
        for typ, val, target, overwrite, after in edits:
            b, msg = set_note(b, typ, val, target, overwrite, after)
            if msg:
                kept.append(f"{r['letter_key']}: {msg}")
        if b != m.group(0):
            text = text[:m.start()] + b + text[m.end():]
            changed += 1
    for k in kept:
        print("  " + k)
    print(f"{changed} register entries {'updated' if args.write else 'would change (dry run, --write to apply)'}")
    if args.write:
        REGISTER.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
