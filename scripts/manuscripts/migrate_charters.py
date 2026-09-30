"""One-off migration: manuscripts filed as bibl type="charter" in the literature register become
msDesc entries; all references in data/letters are re-pointed; the old bibl is removed only when
no reference remains (Plan Phase 2.5). Mapping: build/manuscripts/migration_charters.json.

Usage: python scripts/manuscripts/migrate_charters.py [--dry-run]
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import register as reg  # noqa: E402

REPO = reg.REPO
LIT = REPO / "data" / "register" / "lassberg-literature.xml"
MAP = REPO / "build" / "manuscripts" / "migration_charters.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    items = json.loads(MAP.read_text(encoding="utf-8"))["items"]
    entries = reg.load_entries()
    lit = LIT.read_text(encoding="utf-8")
    for it in items:
        lid = it["literature_id"]
        if f'xml:id="{lid}"' not in lit:
            print(f"{lid}: already migrated")
            continue
        if it.get("existing_witness"):
            wid = it["existing_witness"]
            if not args.dry_run:
                reg.update_msdesc(wid, it.get("msname"), it.get("note"), it.get("work_key"), it.get("work_title"))
        else:
            e = it["entry"]
            wid = reg.find_by_hsp_or_signature(entries, e["hsp_id"], e["shelfmark"], e["repository"])
            if not wid and not args.dry_run:
                wid = reg.add_msdesc(e)
                entries = reg.load_entries()
            wid = wid or "(new)"
        old = f"../register/lassberg-literature.xml#{lid}"
        new = f"../register/lassberg-manuscripts.xml#{wid}"
        n = 0
        for f in sorted((REPO / "data" / "letters").glob("*.xml")):
            s = f.read_text(encoding="utf-8")
            if old in s:
                n += s.count(old)
                if not args.dry_run:
                    f.write_text(s.replace(old, new), encoding="utf-8")
        print(f"{lid} -> {wid}: {n} references re-pointed")
        if args.dry_run:
            continue
        left = [f.name for f in (REPO / "data" / "letters").glob("*.xml") if lid in f.read_text(encoding="utf-8")]
        others = [m for m in re.findall(rf'{lid}"', lit)]
        if left:
            print(f"  NOT removed, still referenced in {left}")
            continue
        lit = LIT.read_text(encoding="utf-8")
        lit2 = re.sub(rf' *<bibl xml:id="{lid}"[^>]*>.*?</bibl>\n', "", lit, count=1, flags=re.S)
        assert lit2 != lit
        LIT.write_text(lit2, encoding="utf-8")


if __name__ == "__main__":
    main()
