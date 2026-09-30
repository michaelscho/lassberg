"""Import the BLB Donaueschingen manuscripts (Laßbergs Besitz) from the Excel table into
data/register/lassberg-manuscripts.xml. Run with `.venv/bin/python` (needs openpyxl).

Base set = union of the sheets `HSP-Abzug` and `HSP-Abzug 2` over `Signatur`; `Tabellenblatt1`
only contributes the Laßberg number (its HSP columns are a shifted VLOOKUP and not trusted).
Idempotent: entries with the same HSP-ID or signature are skipped.

Usage: .venv/bin/python scripts/manuscripts/import_blb_excel.py [--xlsx PATH] [--dry-run]
"""
import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import register as reg  # noqa: E402
from openpyxl import load_workbook  # noqa: E402

REPO = reg.REPO
DEFAULT_XLSX = REPO / "data" / "temp" / "Handschriften BLB Laßberg.xlsx"


def signum(sig: str) -> int:
    m = re.search(r"(\d+)\s*$", sig)
    return int(m.group(1)) if m else 10**9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    wb = load_workbook(args.xlsx, data_only=True)
    t1 = [r for r in wb["Tabellenblatt1"].iter_rows(min_row=2, values_only=True) if r[1]]
    a1 = [r for r in wb["HSP-Abzug"].iter_rows(min_row=2, values_only=True) if r[0]]
    a2 = [r for r in wb["HSP-Abzug 2"].iter_rows(min_row=2, values_only=True) if r[0]]

    lassberg_nr = {}
    for r in t1:
        n = r[3]
        if isinstance(n, (int, float)):
            lassberg_nr[r[1]] = int(n)
        elif isinstance(r[2], (int, float)):
            lassberg_nr.setdefault(r[1], None)

    base: dict[str, dict] = {}
    descs: dict[str, list] = defaultdict(list)
    for r in a1:
        base[r[0]] = {"signature": r[0], "repository": r[2], "settlement": r[3],
                      "kod": r[6], "gnd": r[7], "desc_ids": [r[9]] if r[9] else [], "purl": r[10]}
    for r in a2:
        e = base.setdefault(r[0], {"signature": r[0], "repository": r[1], "settlement": r[2],
                                   "kod": r[7], "gnd": None, "desc_ids": [], "purl": None})
        if r[6] and r[6] not in e["desc_ids"]:
            e["desc_ids"].append(r[6])
        if not e["kod"]:
            e["kod"] = r[7]
        descs[r[0]].append({"desc": r[6], "author": r[5], "status": r[3], "catalog": r[13]})
    for r in t1:  # signatures only in Tabellenblatt1: create without HSP-ID
        base.setdefault(r[1], {"signature": r[1], "repository": None, "settlement": None,
                               "kod": None, "gnd": None, "desc_ids": [], "purl": None, "only_t1": True})

    only1 = sorted(set(r[0] for r in a1) - set(r[0] for r in a2))
    only2 = sorted(set(r[0] for r in a2) - set(r[0] for r in a1))
    dup2 = [k for k, v in Counter(r[0] for r in a2).items() if v > 1]
    dup1 = [k for k, v in Counter(r[0] for r in a1).items() if v > 1]

    entries = reg.load_entries()
    new, skipped = [], []
    for sig in sorted(base, key=signum):
        b = base[sig]
        if reg.find_by_hsp_or_signature(entries, b["kod"], sig):
            skipped.append(sig)
            continue
        nr = lassberg_nr.get(sig)
        e = {
            "settlement": b["settlement"], "repository": b["repository"], "shelfmark": sig,
            "hsp_id": b["kod"], "gnd": b["gnd"],
            "former": [f"Laßberg-Nr. {nr}"] if nr else [],
            "provenance": f"Sammlung Laßberg (Laßberg-Nr. {nr})" if nr else "Sammlung Laßberg",
            "needs_review": not b["kod"],
            "note": None if b["kod"] else "Signatur nur in der Laßberg-Tabelle, kein HSP-Eintrag im Abzug.",
        }
        new.append(e)

    if not args.dry_run and new:
        reg.add_msdescs(new)

    idx = REPO / "data" / "indices" / "hsp_blb_donaueschingen.json"
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(json.dumps({"entries": base, "descriptions": descs}, ensure_ascii=False, indent=1),
                   encoding="utf-8")

    lines = [
        "# Importbericht BLB-Handschriften",
        "",
        f"- Tabellenblatt1: {len(t1)} Zeilen, davon mit Laßberg-Nr.: {sum(1 for v in lassberg_nr.values() if v)}",
        f"- HSP-Abzug: {len(a1)} Zeilen ({len(set(r[0] for r in a1))} Signaturen); "
        f"HSP-Abzug 2: {len(a2)} Zeilen ({len(set(r[0] for r in a2))} Signaturen)",
        f"- nur in HSP-Abzug: {len(only1)}; nur in HSP-Abzug 2: {len(only2)}",
        f"- Signaturen mit mehreren Beschreibungen in Abzug 2: {', '.join(dup2) or '–'} "
        f"(erklärt die Zeilendifferenz {len(a2)} vs. {len(a1)})",
        f"- Doppelte Signaturen in Abzug 1: {', '.join(dup1) or '–'}",
        f"- Grundmenge: {len(base)}; neu angelegt: {len(new)}; übersprungen (bereits im Register): {len(skipped)}",
        f"- ohne HSP-ID (needs-review): {sum(1 for e in new if not e['hsp_id'])}",
        "",
    ]
    rep = REPO / "build" / "manuscripts" / "import_blb_report.md"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
