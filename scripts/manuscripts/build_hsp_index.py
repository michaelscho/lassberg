"""Build the local FTS5 identification index data/hsp/index.sqlite (gitignored) from the register
and the local HSP mirror. One row per registered manuscript that has a mirrored Kulturobjekt.

Usage: python scripts/manuscripts/build_hsp_index.py
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
import lib_hsp as hsp  # noqa: E402
import register as reg  # noqa: E402

COLS = ["shelfmark", "former_shelfmarks", "msname", "title", "date", "orig_place", "authors_works",
        "persons", "provenance", "fulltext"]


def build(register_path: Path = reg.REGISTER) -> int:
    entries = reg.load_entries(register_path)
    hsp.INDEX_DB.parent.mkdir(parents=True, exist_ok=True)
    if hsp.INDEX_DB.exists():
        hsp.INDEX_DB.unlink()
    con = sqlite3.connect(hsp.INDEX_DB)
    con.execute("CREATE TABLE ms (hsp_id TEXT PRIMARY KEY, witness_id TEXT, " + ", ".join(f"{c} TEXT" for c in COLS) + ")")
    con.execute("CREATE VIRTUAL TABLE ms_fts USING fts5(" + ", ".join(COLS) +
                ", content='ms', content_rowid='rowid', tokenize='unicode61 remove_diacritics 2')")
    n = 0
    for wid, e in entries.items():
        hid = e.get("hsp_id")
        if not hid:
            continue
        kod = hsp.load_kod_local(hid)
        if kod is None:
            continue
        former = [x for x in (e.get("alt_ids", {}).get("former") or [])]
        titles, authors_works, persons, provenance, full, date_bits = [], [], [], [], [], []
        _, kod_xml = hsp.kod_paths(hid)
        if kod_xml.exists():
            kd = hsp.parse_description(kod_xml.read_bytes())
            former += kd["msidentifier"].get("former_shelfmarks", [])
        for did in hsp.local_descriptions(hid):
            d = hsp.parse_description(hsp.desc_path(did).read_bytes())
            former += d["msidentifier"].get("former_shelfmarks", [])
            titles += [d["head"]]
            date_bits += [d["headline"]]
            authors_works += [d["summary"]] + [" ".join(x for x in (i["author"], i["title"], i["locus"], i["incipit"]) if x)
                                              for i in d["items"]]
            persons += [t["text"] for t in d["index_terms"]]
            provenance += [d["history"]]
            full += [d["fulltext"]]
        msname = e.get("label") if e.get("label") and e["label"] != wid and " , " not in e["label"] else ""
        if not msname or msname.startswith(e.get("settlement") or "\0"):
            msname = hsp.clean_kod_title(kod.get("title-display"))
        row = {
            "shelfmark": e.get("signature") or kod.get("idno-display") or "",
            "former_shelfmarks": " | ".join(dict.fromkeys(x for x in former if x)),
            "msname": msname,
            "title": " ".join(x for x in [hsp.clean_kod_title(kod.get("title-display"))] + titles if x),
            "date": " ".join([*(kod.get("orig-date-lang-display") or []), *date_bits]),
            "orig_place": kod.get("orig-place-display") or "",
            "authors_works": " ".join(x for x in authors_works if x),
            "persons": " ".join(dict.fromkeys(x for x in persons if x)),
            "provenance": " ".join(x for x in provenance if x),
            "fulltext": " ".join(full),
        }
        con.execute("INSERT INTO ms (hsp_id, witness_id, " + ", ".join(COLS) + ") VALUES (?,?," + ",".join("?" * len(COLS)) + ")",
                    [hid, wid] + [row[c] for c in COLS])
        n += 1
    con.execute("INSERT INTO ms_fts(ms_fts) VALUES('rebuild')")
    con.commit()
    con.close()
    return n


if __name__ == "__main__":
    print(f"indexed {build()} manuscripts -> {hsp.INDEX_DB}")
