#!/usr/bin/env python3
"""Parse the OCR of Harris 1991 (Briefinventar, PDF pages 71-112, see ocr_harris.py) into
build/harris/harris.tsv: one row per Harris number.

Sections (by number): 1-1524 dated letters FROM Laßberg, 1525-1565 undated from Laßberg,
1566-3182 dated letters TO Laßberg, 3183- undated to Laßberg. Columns in the book:
  dated from:  Nr) Datum Absendeort Empfänger BNr. Vw.ort Druck
  dated to:    Nr) Datum Absendeort Absender Vw.ort Druck
  undated:     Nr) Korrespondent (Datum ca.) [BNr.] Vw.ort/Sigle Druck
Vw.ort sigla: "K BLB" = Karlsruhe BLB, "/E" Entwurf, "/A" Abschrift, "/F" Fragment, ... BNr. is
Laßberg's own letter number (also written at the head of his letters).

OCR is imperfect: `korr` keeps place + correspondent as one string, `raw` the whole line; rows
whose date or Vw.ort could not be read are kept with empty fields.

Usage:  python scripts/harris/parse_harris.py [OCR_DIR]   (default: data/harris/ocr)
"""
from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OCR_DIR = REPO / "data" / "harris" / "ocr"
OUT = REPO / "build" / "harris" / "harris.tsv"
FIRST, LAST = "071-R", "112-R"
COLUMNS = ["nr", "section", "date", "date_raw", "korr", "bnr", "vw", "vw_flags", "is_blb", "sigle", "druck", "raw"]

# rows/years may carry 1-2 chars of OCR margin noise ("ı 12)", "2 13)", "i 1801")
RX_ROW = re.compile(r"^(?:\S{1,2}\s+)?[\W_]*(\d{1,4})\s*[)}\]]\s*(.+)$")
RX_YEAR = re.compile(r"^(?:\S{1,2}\s+)?[\W_]*(1[78]\d\d)[\W_]*$")
RX_HEAD = re.compile(r"(?:von|an) Lassberg\s+\d{1,2}\.\s?\d{1,2}\.\s?(1[78]\d\d)\s*[-–]")
RX_DATE = re.compile(r"^\(?(\d{1,2})(?:[.,]\s?|(?=\d{2}\b))(\d{1,2})[.,]?\)?[!?\"”]*$")
# Vw.ort sigla: 1-2 capitals, optional space, 2-4 capitals, optional /flags ("D FA", "K BLB/E", "MSN")
RX_VW = re.compile(r"(?<![\w.])([A-Z]{1,2} ?[A-Z]{2,4})(/[A-Z]{1,2})?(?![\w.])")


def section(nr: int) -> str:
    return ("von_datiert" if nr <= 1524 else "von_undatiert" if nr <= 1565
            else "an_datiert" if nr <= 3182 else "an_undatiert")


def parse_line(nr: int, rest: str, year: str | None, prev_date: str) -> dict:
    r = dict.fromkeys(COLUMNS, "")
    r.update(nr=nr, section=section(nr), raw=rest)
    toks = rest.split()
    body = rest
    if r["section"].endswith("datiert") and not r["section"].endswith("undatiert") and toks:
        r["date_raw"] = toks[0]
        m = RX_DATE.match(toks[0])
        if m and year:
            r["date"] = f"{year}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
        elif toks[0].lower().startswith("dass"):
            r["date"] = prev_date
        elif year:
            r["date"] = year
        body = rest[len(toks[0]):].strip()
    vws = list(RX_VW.finditer(body))
    if vws:
        v = vws[-1]
        r["vw"] = v.group(1).replace(" ", "")
        m = re.match(r"^KB[LIl1][BR8W]?(E)?$", r["vw"])  # OCR variants of "K BLB", "K BLB/E"
        if m:
            r["vw"] = "KBLB"
            r["vw_flags"] = r["vw_flags"] or (m.group(1) or "")
        r["vw_flags"] = (v.group(2) or "").lstrip("/")
        r["is_blb"] = "y" if r["vw"] in ("KBLB", "BLB") else ""
        before, after = body[:v.start()].strip(), body[v.end():].strip()
        if r["section"].startswith("von"):
            m = re.search(r"(\S+)$", before)
            if m and re.match(r"^[!?]*[\d\-?]+[/\d ]*$", m.group(1)):
                r["bnr"] = m.group(1).strip("!?").split("/")[0].strip("-")
                before = before[:m.start()].strip()
        r["korr"] = before.strip(" _|.-")
        parts = after.split()
        if r["section"].endswith("undatiert") and len(parts) > 1:
            r["sigle"] = " ".join(parts[:-1])
            r["druck"] = parts[-1]
        else:
            r["druck"] = " ".join(parts)
    else:
        r["korr"] = body
    return r


def main():
    ocr_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else OCR_DIR
    files = [f for f in sorted(ocr_dir.glob("*.txt")) if FIRST <= f.stem <= LAST]
    rows, year, prev, last = {}, None, "", 0
    for f in files:
        lines = f.read_text(encoding="utf-8").splitlines()
        # running head "von Lassberg 18. 4. 1811-30. 12. 1813": the page starts in that year
        head = next((RX_HEAD.search(ln) for ln in lines[:4] if RX_HEAD.search(ln)), None)
        if head and (not year or head.group(1) >= year):
            year, prev = head.group(1), ""
        for line in lines:
            ym = RX_YEAR.match(line)
            if ym:
                if not year or ym.group(1) >= year:  # headers only move forward (OCR noise)
                    year = ym.group(1)
                    prev = ""
                continue
            m = RX_ROW.match(line)
            if not m:
                continue
            nr = int(m.group(1))
            if not 1 <= nr <= 3300 or nr in rows or (last and not 0 < nr - last <= 60):
                continue  # out of sequence: OCR noise read as a number
            last = nr
            if nr in (1525, 1566, 3183):  # new section: dates start over
                year, prev = None, ""
            r = parse_line(nr, m.group(2).strip(), year, prev)
            # dated sections run chronologically: a step back in month/day means the year header
            # was lost in OCR -> next year
            if year and len(r["date"]) == 10 and len(prev) == 10 and r["date"][5:] < prev[5:] \
                    and r["date"][:4] == prev[:4] and r["date_raw"].lower()[:4] != "dass":
                year = str(int(year) + 1)
                r = parse_line(nr, m.group(2).strip(), year, prev)
            if r["date"]:
                prev = r["date"]
            rows[nr] = r
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, COLUMNS, delimiter="\t")
        w.writeheader()
        w.writerows(rows[k] for k in sorted(rows))
    missing = [n for n in range(1, max(rows) + 1) if n not in rows]
    print(f"{len(rows)} Harris rows -> {OUT}; {len(missing)} numbers not recognised"
          + (f" (e.g. {missing[:15]})" if missing else ""))


if __name__ == "__main__":
    main()
