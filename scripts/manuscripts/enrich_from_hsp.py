"""Enrich the register from the local HSP mirror (offline except for --live-resolve).

- fills an empty msName from the HSP `title-display` (typographic quotes removed)
- compares settlement / repository / shelfmark with the HSP core data and only logs differences
- msDesc without HSP-ID: `--live-resolve` searches the HSP live and sets the ID only for exactly one
  hit with identical shelfmark and settlement; everything else goes to
  build/manuscripts/hsp_unresolved.md

Usage: python scripts/manuscripts/enrich_from_hsp.py [--live-resolve]
"""
import argparse
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
import lib_hsp as hsp  # noqa: E402
import register as reg  # noqa: E402

OUT = reg.REPO / "build" / "manuscripts"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live-resolve", action="store_true")
    args = ap.parse_args()
    entries = reg.load_entries()
    text = reg.REGISTER.read_text(encoding="utf-8")
    names: dict[str, str] = {}
    hsp_ids: dict[str, str] = {}
    diffs, unresolved = [], []

    for wid, e in entries.items():
        if e.get("hsp_id"):
            kod = hsp.load_kod_local(e["hsp_id"])
            if not kod:
                continue
            title = hsp.clean_kod_title(kod.get("title-display"))
            has_name = e["label"] and e["label"] != ", ".join(
                x for x in (e.get("settlement"), e.get("repository"), e.get("signature")) if x)
            if title and not has_name:
                names[wid] = title
            for label, mine, theirs in (("settlement", e.get("settlement"), kod.get("settlement-display")),
                                        ("repository", e.get("repository"), kod.get("repository-display")),
                                        ("shelfmark", e.get("signature"), kod.get("idno-display"))):
                if mine and theirs and mine != theirs:
                    diffs.append(f"- {wid} {label}: Register „{mine}“ vs. HSP „{theirs}“")
        elif args.live_resolve and e.get("signature"):
            q = " ".join(x for x in (e.get("settlement"), e.get("signature")) if x)
            try:
                hits = [k for k in hsp.search(q, rows=10)
                        if k.get("idno-display") == e["signature"] and k.get("settlement-display") == e.get("settlement")]
            except hsp.HspError as exc:
                unresolved.append(f"- {wid} ({q}): HSP-Fehler {exc}")
                continue
            if len(hits) == 1:
                hsp_ids[wid] = hits[0]["id"]
            else:
                unresolved.append(f"- {wid} ({q}): {len(hits)} exakte Treffer")
        else:
            unresolved.append(f"- {wid} ({e.get('label')}): keine HSP-ID")

    def patch(m):
        block = m.group(0)
        wid = m.group(2)
        if wid in names and "<msName>" not in block:
            block = block.replace("                    </msIdentifier>",
                                  f"                        <msName>{escape(names[wid])}</msName>\n"
                                  "                    </msIdentifier>", 1)
        if wid in hsp_ids and 'type="hsp"' not in block:
            block = re.sub(r"( *)(<msName>|</msIdentifier>)",
                           lambda mm: f'{mm.group(1)}<altIdentifier type="hsp"><idno>{hsp_ids[wid]}</idno></altIdentifier>\n'
                                      f"{mm.group(1)}{mm.group(2)}", block, count=1)
        return block

    new = re.sub(r'( *)<msDesc xml:id="(lassberg-witness-\d+)"[^>]*>.*?</msDesc>\n', patch, text, flags=re.S)
    if new != text:
        reg.REGISTER.write_text(new, encoding="utf-8")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "hsp_unresolved.md").write_text(
        "# HSP: nicht aufgelöste Einträge\n\n" + ("\n".join(unresolved) or "(keine)") +
        "\n\n# Abweichungen Register vs. HSP\n\n" + ("\n".join(diffs) or "(keine)") + "\n", encoding="utf-8")
    print(f"msName gesetzt: {len(names)}; HSP-ID gesetzt: {len(hsp_ids)}; unaufgelöst: {len(unresolved)}; Abweichungen: {len(diffs)}")


if __name__ == "__main__":
    main()
