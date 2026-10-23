#!/usr/bin/env python3
"""Check data/register/lassberg-letters.xml field by field against Harris 1991 and write the
findings to build/harris/register_check.tsv. Nothing is written to the register.

Harris sources (both derived from Harris_Freiherr_von_Lassberg.pdf, PDF pages 71-112):
  data/harris/vision/<page>.tsv   visual transcription (primary)
  build/harris/harris.tsv         tesseract OCR, parse_harris.py (independent cross-check)
A finding is `sicher` when the OCR agrees with the visual transcription on that field, else
`pruefen` (look at the scan; page given in the `page` column).

Checks per register entry (joined via <note type="nummer_harris">):
  datum           sent date vs Harris date ("Dass." = date of the previous row)
  datum_genauer   register has only year/"Unbekannt", Harris a more precise date
  ort             place of sending vs Harris Absendeort ("ohne Ortsangabe" = "Unbekannt")
  korrespondent   the non-Laßberg party vs Harris Empfänger/Absender (abbreviations expanded)
  briefnummer     <note type="journalnummer"> vs Harris BNr. (letters from Laßberg)
  verwahrung      institution vs Harris Vw.ort sigle (sigle -> institution learnt from the
                  register majority; only flagged for unambiguous sigla)
Coverage: Harris numbers without register entry, register numbers missing in Harris, duplicates.

Usage:  python scripts/harris/check_register.py
"""
from __future__ import annotations

import csv
import datetime
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from lxml import etree
from rapidfuzz import fuzz

REPO = Path(__file__).resolve().parents[2]
REGISTER = REPO / "data" / "register" / "lassberg-letters.xml"
VISION_DIR = REPO / "data" / "harris" / "vision"
OCR = REPO / "build" / "harris" / "harris.tsv"
VISION_OUT = REPO / "build" / "harris" / "harris_vision.tsv"
OUT = REPO / "build" / "harris" / "register_check.tsv"
NS = {"tei": "http://www.tei-c.org/ns/1.0"}
LASSBERG_GND = "118778862"
MONTHS = {"jan": 1, "feb": 2, "mär": 3, "mar": 3, "apr": 4, "mai": 5, "jun": 6, "jul": 7,
          "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dez": 12, "dec": 12}
ABBREV = {"fbg": "fürstenberg", "hosi": "hohenzollern sigmaringen", "höw": "oettingen wallerstein",
          "öw": "oettingen wallerstein", "ow": "oettingen wallerstein", "howa": "hohenlohe waldenburg",
          "bad": "baden", "f f": "fürstlich fürstenbergisch", "unbek": "unbekannt",
          "schweiz": "schweizerische", "württ": "württembergisch",
          "albany": "stolberg gedern"}  # Luise Gräfin von Albany, geb. zu Stolberg-Gedern
COLUMNS = ["letter_key", "harris_nr", "page", "pruefung", "befund", "register", "harris", "harris_ocr", "hinweis"]


def fold(s: str) -> str:
    """lower, ß->ss, umlauts and their ae/oe/ue spellings collapsed (Näf = Naef, Götz = Goetz)"""
    s = (s or "").lower().replace("ß", "ss")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"([aou])e", r"\1", s)
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", s).split())


# --- Harris -----------------------------------------------------------------------------------

def section(nr: int) -> str:
    return ("von" if nr <= 1524 else "von_undatiert" if nr <= 1565
            else "an" if nr <= 3182 else "an_undatiert")


def harris_date(raw: str, year: str, prev: str) -> tuple[str, bool]:
    """-> (ISO date or prefix, uncertain flag). '19.11.^12' -> 1829-11-19; 'Dass.' -> prev;
    '14.(10.)' -> 1849-10-14; 'Feb.?' -> 1807-02; 'A 05.' (Anfang Mai) -> 1845-05; '??' -> year"""
    s = re.sub(r"\^\d+", "", raw or "").strip()
    unsure = "?" in s
    if s.lower().startswith("dass"):
        return prev, unsure
    m = re.match(r"(\d{1,2})\.\s*Dass", s)  # "28. Dass." = day 28 of the previous row's month
    if m and len(prev) == 10:
        return f"{prev[:8]}{int(m.group(1)):02d}", unsure
    m = re.search(r"(\d{1,2})\.\s*\(?(\d{1,2})\.?\)?", s)
    if m and year:
        return f"{year}-{int(m.group(2)):02d}-{int(m.group(1)):02d}", unsure
    m = re.search(r"(?:^|\s)(\d{1,2})\.", s)
    if m and year and s[:1] in ("A", "E", "M"):  # Anfang/Ende/Mitte <Monat>
        return f"{year}-{int(m.group(1)):02d}", True
    for k, v in MONTHS.items():
        if fold(s).startswith(fold(k)):
            return f"{year}-{v:02d}", unsure
    return year or "", True


def valid(iso: str) -> bool:
    try:
        datetime.date.fromisoformat(iso)
        return True
    except ValueError:
        return False


HEAD = ["nr", "year", "date", "place", "correspondent", "bnr", "vw", "druck", "note"]


def read_vision_file(f: Path) -> list[dict]:
    """tolerates a stray empty column after nr (one transcription file has it)"""
    out = []
    with f.open(encoding="utf-8") as fh:
        for i, row in enumerate(csv.reader(fh, delimiter="\t")):
            if i == 0 or not row:
                continue
            if len(row) > 2 and row[1] == "" and re.match(r"1[78]\d\d$", row[2]):
                del row[1]
            out.append(dict(zip(HEAD, row + [""] * (len(HEAD) - len(row)))))
    return out


def load_vision() -> dict[int, dict]:
    rows, prev = {}, ""
    for f in sorted(VISION_DIR.glob("*.tsv")):
        for r in read_vision_file(f):
            try:
                nr = int(re.sub(r"\D", "", r["nr"]))
            except ValueError:
                continue
            r["page"] = f.stem
            r["section"] = section(nr)
            if r["section"] in ("von", "an"):
                r["iso"], r["unsure"] = harris_date(r["date"], (r.get("year") or "").strip(), prev)
                if len(r["iso"]) == 10:
                    prev = r["iso"]
            else:
                r["iso"], r["unsure"] = "", True
            rows.setdefault(nr, r)
    return rows


def load_ocr() -> dict[int, dict]:
    if not OCR.exists():
        return {}
    with OCR.open(encoding="utf-8") as f:
        return {int(r["nr"]): r for r in csv.DictReader(f, delimiter="\t")}


def sigle(vw: str) -> str:
    """'K BLB/E' -> 'KBLB', 'D FA La 27a' -> 'DFA', 'M SN/E' -> 'MSN'"""
    m = re.match(r"\s*([A-Z]{1,2})\s?([A-Z]{2,4})", vw or "")
    return (m.group(1) + m.group(2)) if m else ""


def norm_bnr(s: str) -> str:
    """Harris notation kept ('!' = not chronological, '?' = unsure), spaces/footnote marks dropped"""
    s = re.sub(r"\^\d+", "", s or "")
    return re.sub(r"\s", "", s).strip("-")


def expand(name: str) -> str:
    n = fold(name)
    for k, v in ABBREV.items():
        n = re.sub(rf"\b{k}\b", v, n)
    return n


def name_ok(harris: str, register: str) -> bool:
    h, r = expand(harris), fold(register)
    if not h or not r or "unbekannt" in h:
        return True
    toks = [t for t in h.split() if len(t) > 2 and t not in ("von", "und", "der", "die", "des")]
    if any(t in r.split() or any(w.startswith(t) for w in r.split()) for t in toks):
        return True
    return fuzz.token_set_ratio(h, r) >= 70


def place_ok(harris: str, register: str) -> bool:
    h, r = fold(harris), fold(register)
    if h in ("ohne ortsangabe", "") and r in ("unbekannt", ""):
        return True
    if not h or not r:
        return h == r
    return h == r or h in r or r in h or fuzz.ratio(h, r) >= 80 or fuzz.partial_ratio(h, r) >= 90


# --- register ---------------------------------------------------------------------------------

def load_register() -> list[dict]:
    out = []
    for c in etree.parse(str(REGISTER)).iterfind(".//tei:correspDesc", NS):
        s = c.find("tei:correspAction[@type='sent']", NS)
        r = c.find("tei:correspAction[@type='received']", NS)

        def names(a):
            return [] if a is None else [
                ("".join(p.itertext()).strip(), p.get("ref") or "") for p in a.findall("tei:persName", NS)]
        d = s.find("tei:date", NS) if s is not None else None
        p = s.find("tei:placeName", NS) if s is not None else None
        note = lambda t: c.findtext(f"tei:note[@type='{t}']", default="", namespaces=NS).strip()  # noqa: E731
        out.append({"key": c.get("key"), "harris_nr": note("nummer_harris"),
                    "date": (d.get("when") or "") if d is not None else "",
                    "place": "".join(p.itertext()).strip() if p is not None else "",
                    "senders": names(s), "recipients": names(r),
                    "journal": note("journalnummer"), "ort": note("aufbewahrungsort"),
                    "inst": note("aufbewahrungsinstitution"), "signatur": note("signatur")})
    return out


def other_party(e: dict, sec: str) -> str:
    side = e["recipients"] if sec.startswith("von") else e["senders"]
    return "; ".join(n for n, ref in side if LASSBERG_GND not in ref)


# --- main -------------------------------------------------------------------------------------

def main():
    vision, ocr, reg = load_vision(), load_ocr(), load_register()
    if not vision:
        raise SystemExit(f"no visual transcription in {VISION_DIR}")
    VISION_OUT.parent.mkdir(parents=True, exist_ok=True)
    with VISION_OUT.open("w", encoding="utf-8", newline="") as f:
        cols = ["nr", "page", "section", "year", "date", "iso", "place", "correspondent", "bnr", "vw", "druck", "note"]
        w = csv.DictWriter(f, cols, delimiter="\t", extrasaction="ignore")
        w.writeheader()
        w.writerows({**vision[n], "nr": n} for n in sorted(vision))

    # sigle -> institution, learnt from the register itself (majority over all joined entries)
    votes = defaultdict(Counter)
    for e in reg:
        h = vision.get(int(e["harris_nr"])) if e["harris_nr"].isdigit() else None
        if h and sigle(h["vw"]):
            votes[sigle(h["vw"])][e["inst"]] += 1
    inst_of = {s: c.most_common(1)[0][0] for s, c in votes.items()
               if c.most_common(1)[0][1] >= 3 and c.most_common(1)[0][1] / sum(c.values()) >= 0.8}

    rows, stats = [], Counter()

    def add(e, h, check, befund, rv, hv, ov="", hint=""):
        sure = bool(ov) and fold(ov) == fold(hv)
        rows.append({"letter_key": e["key"] if e else "", "harris_nr": h.get("nr_int", "") if h else "",
                     "page": h.get("page", "") if h else "", "pruefung": "sicher" if sure else "pruefen",
                     "befund": f"{check}: {befund}", "register": rv, "harris": hv, "harris_ocr": ov,
                     "hinweis": hint})
        stats[check] += 1

    seen = Counter(e["harris_nr"] for e in reg if e["harris_nr"].isdigit())
    for e in reg:
        if not e["harris_nr"].isdigit():
            continue
        nr = int(e["harris_nr"])
        h = vision.get(nr)
        o = ocr.get(nr, {})
        if not h:
            add(e, {"nr_int": nr}, "abdeckung", "Harris-Nr. nicht in der Transkription", e["harris_nr"], "")
            continue
        h["nr_int"] = nr
        sec = h["section"]
        if sec in ("von", "an"):
            hd, rd = h["iso"], e["date"]
            if len(hd) == 10 and not valid(hd):
                add(e, h, "datum", "Harris-Datum unmöglich", rd, hd, o.get("date", ""), h["date"])
            elif len(hd) == 10 and re.match(r"\d{4}-\d{2}-\d{2}$", rd) and hd != rd:
                add(e, h, "datum", "abweichend", rd, hd, o.get("date", ""), h["date"] + (" (unsicher)" if h["unsure"] else ""))
            elif re.match(r"\d{4}", rd) and hd[:len(rd)] != rd[:len(hd)] and hd:
                add(e, h, "datum", "abweichend (Teildatum)", rd, hd, o.get("date", ""), h["date"])
            elif len(hd) > len(rd if re.match(r"\d{4}", rd) else "") and hd and not h["unsure"]:
                add(e, h, "datum_genauer", "Harris genauer", rd, hd, o.get("date", ""), h["date"])
            if not place_ok(h["place"], e["place"]):
                add(e, h, "ort", "abweichend", e["place"], h["place"])
        if not name_ok(h["correspondent"], other_party(e, sec)):
            add(e, h, "korrespondent", "abweichend", other_party(e, sec), h["correspondent"])
        if sec.startswith("von"):
            hb, rb = norm_bnr(h.get("bnr", "")), norm_bnr(e["journal"])
            if hb != rb and (hb or rb):
                add(e, h, "briefnummer", "abweichend", e["journal"], h.get("bnr", ""),
                    o.get("bnr", "") if norm_bnr(o.get("bnr", "")) == hb else "")
        s = sigle(h["vw"])
        if s in inst_of and e["inst"] != inst_of[s]:
            add(e, h, "verwahrung", f"Sigle {s} = {inst_of[s]}", f"{e['ort']} / {e['inst']}", h["vw"],
                o.get("vw", "") if sigle(o.get("vw", "")) == s else "")
    for nr, c in seen.items():
        if c > 1:
            add(None, {"nr_int": nr}, "abdeckung", f"Harris-Nr. {c}x im Register vergeben", nr, "",
                hint=", ".join(e["key"] for e in reg if e["harris_nr"] == str(nr)))
    for nr, h in vision.items():
        if str(nr) not in seen:
            h["nr_int"] = nr
            add(None, h, "abdeckung", "Harris-Brief fehlt im Register", "", f"{h['date']} {h['place']} {h['correspondent']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    print(f"{len(vision)} Harris rows (visual), {len(reg)} register entries -> {len(rows)} findings in {OUT}")
    print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(stats.items())))
    print(f"  sicher (OCR bestätigt): {sum(r['pruefung'] == 'sicher' for r in rows)}")


if __name__ == "__main__":
    main()
