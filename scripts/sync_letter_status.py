#!/usr/bin/env python3
"""Validates and synchronizes the letter-status model between the individual letter files and
the corpus register (docs/TEI.md, "Letter status model").

The model has three axes, each with exactly one hand-maintained home:
  1. source:      div/@type original|print in the letter file
  2. editorial:   revisionDesc/listChange/change/@status in the letter file
                  (draft -> done -> reviewed -> published; "published" is appended by --publish,
                  never by hand)
  3. publication: correspDesc/@change in data/register/lassberg-letters.xml - a *derived* value
                  this script computes from axes 1+2:
                    in_register            no letter file
                    preview_print          file exists (OCR source), not yet published
                    preview_transcription  file exists (manuscript source), not yet published
                    online_print           published, OCR source
                    online_transcription   published, manuscript source
  The register additionally carries the hand-maintained <note type="scan"> (none|internal|online).

Usage:
  python scripts/sync_letter_status.py            # --check: validate, report, exit 1 on conflict
  python scripts/sync_letter_status.py --write    # recompute register @change from letter files
  python scripts/sync_letter_status.py --publish lassberg-letter-XXXX [...]
                                                  # gate: latest status must be "reviewed";
                                                  # appends the published <change> entry and
                                                  # updates the register

Register edits are line-based (only the @change value on the correspDesc line is touched), so
the file's formatting stays byte-identical otherwise.
"""
from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path

from lxml import etree

NS = {"tei": "http://www.tei-c.org/ns/1.0"}
REPO = Path(__file__).resolve().parent.parent
REGISTER = REPO / "data/register/lassberg-letters.xml"
LETTERS_DIR = REPO / "data/letters"

FILE_STATUSES = ["draft", "done", "reviewed", "published"]
REGISTER_STATUSES = {"in_register", "preview_print", "preview_transcription",
                     "online_print", "online_transcription"}
SCAN_VALUES = {"none", "internal", "online"}


def load_letter_facts() -> dict[str, dict]:
    """id -> {source: original|print|None, latest: status|None, path}"""
    facts = {}
    for f in sorted(LETTERS_DIR.glob("lassberg-letter-*.xml")):
        tree = etree.parse(str(f))
        has_original = bool(tree.findall(".//tei:text//tei:div[@type='original']", NS))
        has_print = bool(tree.findall(".//tei:text//tei:div[@type='print']", NS))
        changes = tree.findall(".//tei:revisionDesc//tei:change", NS)
        facts[f.stem] = {
            "source": "original" if has_original else ("print" if has_print else None),
            "latest": changes[-1].get("status") if changes else None,
            "all_statuses": [c.get("status") for c in changes],
            "path": f,
        }
    return facts


def load_register_facts() -> dict[str, dict]:
    """id -> {change, scan, url_facsimile_filled}"""
    tree = etree.parse(str(REGISTER))
    facts = {}
    for cd in tree.findall(".//tei:correspDesc", NS):
        scan = cd.find("tei:note[@type='scan']", NS)
        url = cd.find("tei:note[@type='url_facsimile']", NS)
        facts[cd.get("key")] = {
            "change": cd.get("change"),
            "scan": scan.text.strip() if scan is not None and scan.text else None,
            "url_filled": bool(url is not None and (url.text or "").strip()),
        }
    return facts


def expected_change(letter: dict | None) -> str:
    if letter is None or letter["source"] is None:
        return "in_register"
    tier = "online" if letter["latest"] == "published" else "preview"
    src = "transcription" if letter["source"] == "original" else "print"
    return f"{tier}_{src}"


def check(letters: dict, register: dict) -> tuple[list[str], list[str]]:
    conflicts, infos = [], []
    for lid, letter in letters.items():
        if lid not in register:
            conflicts.append(f"orphan-file: {lid} has a letter file but no register entry")
            continue
        for s in letter["all_statuses"]:
            if s not in FILE_STATUSES:
                conflicts.append(f"unknown-status: {lid} has change/@status='{s}' (allowed: {FILE_STATUSES})")
        if letter["latest"] is None:
            conflicts.append(f"missing-revisionDesc: {lid} has no revisionDesc/change entry")
        if letter["source"] is None:
            conflicts.append(f"missing-div: {lid} has neither div[@type='original'] nor div[@type='print']")
        if letter["latest"] == "reviewed":
            infos.append(f"ready-to-publish: {lid} is reviewed but not yet published "
                         f"(run --publish {lid})")
    for lid, reg in register.items():
        if reg["change"] not in REGISTER_STATUSES:
            conflicts.append(f"unknown-register-status: {lid} @change='{reg['change']}'")
        exp = expected_change(letters.get(lid))
        if reg["change"] != exp and reg["change"] in REGISTER_STATUSES:
            conflicts.append(f"register-drift: {lid} @change='{reg['change']}' but letter files imply "
                             f"'{exp}' (run --write to sync)")
        if reg["scan"] is None:
            conflicts.append(f"missing-scan-note: {lid} has no <note type='scan'>")
        elif reg["scan"] not in SCAN_VALUES:
            conflicts.append(f"unknown-scan-value: {lid} scan='{reg['scan']}' (allowed: {sorted(SCAN_VALUES)})")
        elif reg["scan"] == "online" and not reg["url_filled"]:
            conflicts.append(f"scan-url-mismatch: {lid} scan='online' but url_facsimile is empty")
        elif reg["scan"] == "none" and letters.get(lid, {}).get("source") == "original":
            conflicts.append(f"scan-implied: {lid} has a manuscript transcription (a scan must exist) "
                             f"but scan='none' - set to 'internal' or 'online'")
    return conflicts, infos


def write_register(letters: dict, register: dict) -> int:
    """Rewrites @change on correspDesc lines where it drifted. Returns number of lines changed."""
    changed = 0
    out = []
    for line in REGISTER.read_text(encoding="utf-8").splitlines(keepends=True):
        m = re.search(r'<correspDesc key="(lassberg-letter-\d+)"[^>]*change="([^"]*)"', line)
        if m:
            exp = expected_change(letters.get(m.group(1)))
            if exp != m.group(2):
                line = line.replace(f'change="{m.group(2)}"', f'change="{exp}"')
                changed += 1
        out.append(line)
    if changed:
        REGISTER.write_text("".join(out), encoding="utf-8")
    return changed


def publish(lid: str, letters: dict) -> None:
    letter = letters.get(lid)
    if letter is None:
        sys.exit(f"ERROR: {lid} has no letter file")
    if letter["latest"] == "published":
        print(f"{lid}: already published, nothing to do")
        return
    if letter["latest"] != "reviewed":
        sys.exit(f"ERROR: {lid} latest status is '{letter['latest']}' - only reviewed letters can be "
                 f"published (add a status='reviewed' change entry first, e.g. via the "
                 f"check-letter-annotations skill)")
    path: Path = letter["path"]
    text = path.read_text(encoding="utf-8")
    m = re.search(r"([ \t]*)</listChange>", text)
    if not m:
        sys.exit(f"ERROR: {lid}: no </listChange> found")
    today = datetime.date.today().isoformat()
    entry = (f'{m.group(1)}    <change when="{today}" who="#sync-letter-status" '
             f'status="published">Published online</change>\n')
    path.write_text(text[:m.start()] + entry + text[m.start():], encoding="utf-8")
    letter["latest"] = "published"
    letter["all_statuses"].append("published")
    print(f"{lid}: appended published entry")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="sync register @change from letter files")
    parser.add_argument("--publish", nargs="+", metavar="ID", help="publish reviewed letters (implies --write)")
    args = parser.parse_args()

    letters = load_letter_facts()

    if args.publish:
        for lid in args.publish:
            publish(lid, letters)
        args.write = True

    if args.write:
        changed = write_register(letters, load_register_facts())
        print(f"register: {changed} @change value(s) updated")

    conflicts, infos = check(letters, load_register_facts())
    for line in infos:
        print(f"  INFO {line}")
    if conflicts:
        print(f"\n{len(conflicts)} CONFLICT(S):")
        for line in conflicts:
            print(f"  {line}")
        sys.exit(1)
    print(f"status model consistent: {len(letters)} letter files, {sum(1 for _ in load_register_facts())} register entries")


if __name__ == "__main__":
    main()
