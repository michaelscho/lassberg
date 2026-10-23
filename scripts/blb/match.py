#!/usr/bin/env python3
"""Match BLB letter units (scripts/lib_blb.py, from the harvested METS) to the letter register
data/register/lassberg-letters.xml and write the review table build/blb/matches.tsv.

Matching: a unit and a register entry match when sender AND recipient agree (GND, else
normalised name, rapidfuzz token_sort_ratio >= NAME_THRESHOLD; names missing from MODS are
parsed from the label "Brief von X an Y"). Among those, the register date is checked against the
unit's BLB dating and against dates written in the letter itself (ALTO cache, fetch_alto.py).

Status per row:
  auto        strong evidence (single candidate in the date range of a single-letter record, or
              day+month+year of the register date found in the letter's head/foot lines in the
              ALTO text), the entry is registered at the BLB, its signatur is empty or identical
              and no other unit claims it -> accept=y preset
  proposed    a candidate was picked (day+month in the text, folder date order, register date
              outside the BLB dating, other institution, signatur conflict, double claim)
              -> check, then accept=y
  ambiguous   several candidates, no text evidence -> pick letter_key from candidates
  unmatched   BLB letter without register candidate (letter not in the register?)
  register    BLB-registered entry no unit was assigned to (with the units of the same pair)
  elsewhere   draft/copy of a letter whose original is held elsewhere (Harris Vw.ort or register
              institution not BLB) -> not taken over, not downloaded
Non-letters in the set (copies, drawings, notes: label without "Brief") are skipped.

Review: set accept=y (and correct letter_key if needed) on rows to take over; accept=n rejects.
Reruns keep accept/letter_key/note of existing rows (keyed by unit_id, resp. letter_key for
"register" rows). Only rows with accept=y are used by download.py and apply_register.py.

Usage:  python scripts/blb/match.py
"""
from __future__ import annotations

import csv
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

from lxml import etree
from rapidfuzz import fuzz

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lib_blb  # noqa: E402

REPO = lib_blb.REPO
REGISTER = REPO / "data" / "register" / "lassberg-letters.xml"
OUT = REPO / "build" / "blb" / "matches.tsv"
HARRIS = REPO / "build" / "harris" / "harris.tsv"
HARRIS_VISION = REPO / "build" / "harris" / "harris_vision.tsv"
NS = {"tei": "http://www.tei-c.org/ns/1.0"}
NAME_THRESHOLD = 88
COLUMNS = ["status", "accept", "letter_key", "unit_id", "record_id", "shelfmark", "unit_type",
           "blb_label", "blb_date", "pages", "alto_pages", "register_date", "register_inst",
           "register_signatur", "candidates", "note"]


def norm(name: str) -> str:
    if "," in name:  # "Laßberg, Joseph von" -> "Joseph von Laßberg"
        last, first = name.split(",", 1)
        name = f"{first} {last}"
    name = name.replace("ß", "ss")
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    name = re.sub(r"\b(freiherr|freifrau|graf|gräfin|grafin|fürst|furst|von|zu|der|die|de|dr|frhr)\b", " ", name)
    return " ".join(re.sub(r"[^a-z ]+", " ", name).split())


def label_parties(label: str) -> tuple[list[dict], list[dict]]:
    """'K 3123,56,1: Brief von A an B, Ort vom 27.03.1831 - ...' -> ([A], [B])"""
    m = re.search(r"Brief von (.+?) an (.+?)(?:,| vom | - |$)", label or "")
    if not m:
        return [], []
    split = lambda s: [{"gnd": None, "name": p.strip()} for p in re.split(r" und |; ", s) if p.strip()]  # noqa: E731
    return split(m.group(1)), split(m.group(2))


def label_dates(label: str) -> tuple[str | None, str | None]:
    """'... 27.03.1831-04.12.1831' -> ('1831-03-27', '1831-12-04'); single date -> (d, d)"""
    ds = [f"{y}-{int(m):02d}-{int(d):02d}" for d, m, y in re.findall(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", label or "")]
    return (ds[0], ds[-1]) if ds else (None, None)


def names_match(a: str, b: str) -> bool:
    """Normalised names: near-identical, or the shorter one (>= 2 tokens) contained in the
    longer ('Harrach Franz Anton Seraphicus' in 'Franz Anton Seraphicus Graf von Harrach zu
    Rohrau')."""
    na, nb = norm(a or ""), norm(b or "")
    if not (na and nb) or UNKNOWN & {na, nb}:
        return False
    if fuzz.token_sort_ratio(na, nb) >= NAME_THRESHOLD:
        return True
    return min(len(na.split()), len(nb.split())) >= 2 and fuzz.token_set_ratio(na, nb) >= 95


UNKNOWN = {"", "unbekannt", "unknown", "n n", "nn", "anonym", "anonymus"}


def unknown(xs: list[dict]) -> bool:
    return not xs or all(norm(x.get("name") or "") in UNKNOWN for x in xs)


def parties_match(xs: list[dict], ys: list[dict]) -> str | None:
    """'gnd' (same GND) | 'name' (names agree, a GND missing) | 'gnd_conflict' (names agree,
    GNDs differ: register or BLB authority to check) | 'unknown' (one side unknown/empty) | None"""
    found = set()
    for x in xs:
        for y in ys:
            if x.get("gnd") and x.get("gnd") == y.get("gnd"):
                return "gnd"
            if names_match(x.get("name"), y.get("name")):
                found.add("gnd_conflict" if x.get("gnd") and y.get("gnd") else "name")
    for q in ("name", "gnd_conflict"):
        if q in found:
            return q
    return "unknown" if unknown(xs) or unknown(ys) else None



def in_range(date: str, d0: str | None, d1: str | None) -> bool:
    if not date or not re.match(r"\d{4}", date) or not d0:
        return False
    d1 = d1 or d0
    return date[:len(d0)] >= d0 and date[:len(d1)] <= d1


def load_register() -> list[dict]:
    reg = []
    for c in etree.parse(str(REGISTER)).iterfind(".//tei:correspDesc", NS):
        def people(typ):
            a = c.find(f"tei:correspAction[@type='{typ}']", NS)
            if a is None:
                return []
            return [{"gnd": (re.search(r"gnd/([0-9X-]+)", p.get("ref") or "") or [None, None])[1],
                     "name": "".join(p.itertext()).strip()} for p in a.findall("tei:persName", NS)]
        sent = c.find("tei:correspAction[@type='sent']/tei:date", NS)
        reg.append({
            "key": c.get("key"), "senders": people("sent"), "recipients": people("received"),
            "date": (sent.get("when") or sent.get("from") or sent.get("notBefore") or "") if sent is not None else "",
            "inst": c.findtext("tei:note[@type='aufbewahrungsinstitution']", default="", namespaces=NS).strip(),
            "signatur": c.findtext("tei:note[@type='signatur']", default="", namespaces=NS).strip(),
            "harris_nr": c.findtext("tei:note[@type='nummer_harris']", default="", namespaces=NS).strip(),
        })
    harris = load_harris()
    for e in reg:
        e["harris"] = harris.get(e["harris_nr"], {})
    return reg


def load_harris() -> dict[str, dict]:
    """Harris 1991 by number: the visual transcription build/harris/harris_vision.tsv
    (scripts/harris/check_register.py) if present, else the OCR build/harris/harris.tsv.
    -> {nr: {date (ISO), bnr (digits), vw (sigle), vw_flags, is_blb}}"""
    if HARRIS_VISION.exists():
        out = {}
        with HARRIS_VISION.open(encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                m = re.match(r"\s*([A-Z]{1,2})\s?([A-Z]{2,4})(?:/([A-Z]+))?", r["vw"] or "")
                sig = m.group(1) + m.group(2) if m else ""
                num = re.search(r"\d+", re.sub(r"\^\d+", "", r["bnr"] or ""))
                out[r["nr"]] = {"date": r["iso"], "bnr": num.group(0) if num else "", "vw": sig,
                                "vw_flags": (m.group(3) or "") if m else "", "is_blb": "y" if sig == "KBLB" else ""}
        return out
    if not HARRIS.exists():
        return {}
    with HARRIS.open(encoding="utf-8") as f:
        return {r["nr"]: r for r in csv.DictReader(f, delimiter="\t")}


def entry_dates(e) -> list[str]:
    """register date, plus Harris' date where it differs (register may carry transfer errors)"""
    hd = e["harris"].get("date", "")
    return [e["date"]] + ([hd] if len(hd) == 10 and hd != e["date"][:10] else [])


def is_blb(e) -> bool:
    return "Badische" in e["inst"] or e["harris"].get("is_blb") == "y"


def original_elsewhere(e) -> bool:
    """Original held by another institution (Harris Vw.ort or register institution): a BLB
    witness of such a letter is a draft/copy and is not taken over (user decision 2026-10-23).
    Drafts whose original is lost (Harris "K BLB/E") count as the letter."""
    if is_blb(e):
        return False
    return bool(e["harris"].get("vw") or e["inst"])


def unit_bnr(u) -> str | None:
    """Laßberg's letter number at the head of his letters ("56 . A .", "295 ."), see Harris BNr."""
    for p in u["pages"]:
        data = lib_blb.cached_alto(p["page_id"], fetch=False) if p["alto"] else None
        lines = [ln for ln in lib_blb.alto_text(data).split("\n") if ln.strip()] if data else []
        if lines:
            # "56 . A . audlicher august ." - the number may share the line with a note; not
            # followed by a month/digit (that would be a date)
            m = re.match(r"^\W*(\d{1,4})\s*\.(?:\s*[A-Z]\s*\.)?(?!\s*(?:\d|[A-Za-zä]+\.?\s+\d{2,4}))", lines[0])
            return m.group(1) if m else None
    return None


def norm_sig(s: str) -> str:
    return re.sub(r"\s+", "", s or "").lower()


# --- dates in the letter text (ALTO cache) ----------------------------------------------------

# month word stems (any continuation allowed: "Septbrs", "Octobris", "Jäner", "Hornung", "7bris",
# old German "Wintermonats", "Brachmonats")
MONTHS = {1: "jan jän jen", 2: "feb horn", 3: "mär mae mar mer lenzmon", 4: "apr ostermon",
          5: "mai may mey maj wonnemon", 6: "jun brach", 7: "jul heum", 8: "aug erntemon",
          9: "sep 7b herbstmon", 10: "okt oct 8b weinmon", 11: "nov 9b wintermon",
          12: "dez dec xb 10b christm"}
_MONTH_OF = {w: m for m, ws in MONTHS.items() for w in ws.split()}
_MONTH_RX = "|".join(sorted(map(re.escape, _MONTH_OF), key=len, reverse=True))
RX_NUM = re.compile(r"(?<!\d)(\d{1,2})\s*[./]\s*(\d{1,2})\s*[./]\s*(\d{2,4})(?!\d)")
RX_NAMED = re.compile(rf"(?<!\d)(\d{{1,2}})\s*\.?\s*(?:ten|ter|te|en|n)?\s*\.?\s*({_MONTH_RX})\w*\.?[ ,.]{{0,4}}(\d{{2,4}})?")


def _month(word: str) -> int:
    return next(m for w, m in sorted(_MONTH_OF.items(), key=lambda x: -len(x[0])) if word.startswith(w))


# fixed feasts used for dating ("am Tage des heiligen Ritters Georg 1818"); movable feasts left out
FEASTS = {"georg": (23, 4), "johann": (24, 6), "johannis": (24, 6), "martin": (11, 11),
          "michael": (29, 9), "michaelis": (29, 9), "stephan": (26, 12), "jakob": (25, 7),
          "jacob": (25, 7), "laurenz": (10, 8), "laurentius": (10, 8), "gallus": (16, 10),
          "galli": (16, 10), "konrad": (26, 11), "conrad": (26, 11), "nikolaus": (6, 12),
          "niclaus": (6, 12), "andreas": (30, 11), "thomas": (21, 12), "lichtmess": (2, 2),
          "lichtmeß": (2, 2), "weihnacht": (25, 12), "christtag": (25, 12), "neujahr": (1, 1),
          "dreikönig": (6, 1), "drei könig": (6, 1), "petri und pauli": (29, 6), "peter und paul": (29, 6),
          "bartholomä": (24, 8), "matthias": (24, 2), "ulrich": (4, 7), "otmar": (16, 11),
          "othmar": (16, 11), "pelagius": (28, 8), "verena": (1, 9), "fridolin": (6, 3)}
RX_FEAST = re.compile(r"(?:tag|fest)\w*\s+(?:des|der|vor|nach)?\s*(?:heil\w*|hl\.?|st\.?|sankt)?\s*"
                      r"(?:\w+\s+){0,2}?(" + "|".join(map(re.escape, FEASTS)) + r")\w*[^\d\n]{0,20}(?:\n[^\d\n]{0,5})?(\d{4})?")


def date_mentions(text: str) -> list[tuple[int, int, int | None]]:
    t = text.lower()
    out = [(int(d), int(m), int(y)) for d, m, y in RX_NUM.findall(t)]
    out += [(int(d), _month(m), int(y) if y else None) for d, m, y in RX_NAMED.findall(t)]
    out += [(*FEASTS[f], int(y) if y else None) for f, y in RX_FEAST.findall(t)]
    return [(d, m, y) for d, m, y in out if 1 <= d <= 31 and 1 <= m <= 12]


def text_score(mentions, date: str) -> int:
    """3 = day+month+year of the register date found, 2 = day+month (year not written), else 0."""
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", date or "")
    if not m:
        return 0
    y, mo, d = map(int, m.groups())
    best = 0
    for dd, mm, yy in mentions:
        if (dd, mm) != (d, mo):
            continue
        if yy is None:
            best = max(best, 2)
        elif yy == y or yy == y % 100:
            return 3
    return best


def unit_mentions(u) -> list:
    """Dates in the head (first 10 lines of the first page with text) and foot (last 15 lines of
    the last page with text) of the letter, where dating lines sit; blank pages (versos,
    envelopes, empty ALTO) are skipped. Empty if the ALTO is not cached."""
    texts = []
    for p in u["pages"]:
        data = lib_blb.cached_alto(p["page_id"], fetch=False) if p["alto"] else None
        lines = [ln for ln in lib_blb.alto_text(data).split("\n") if ln.strip()] if data else []
        if lines:
            texts.append(lines)
    if not texts:
        return []
    return date_mentions("\n".join(texts[0][:10] + texts[-1][-15:]))


RX_SHELF = re.compile(r"K\s*\d+(?:\s*,\s*\d+[a-z]?)*")


def is_letter(u) -> bool:
    label = u["file_label"] or ""
    # "Bearbeitung von X an Y": BLB's label for some letters (e.g. K 2911,112, K 2911,134)
    return bool(u["in_folder"]) or "Brief" in label or "Korrespondenz" in label \
        or bool(re.search(r": Bearbeitung von .+ an ", label))


def main():
    units = []
    for u in lib_blb.load_units():
        if not (u["pages"] and u["shelfmark"]):
            continue
        sm = RX_SHELF.search(u["shelfmark"])
        if u["in_folder"]:  # letter div labels may carry the letter's own date: "08.05.1836 - K 3495,1"
            d0, d1 = label_dates(u["shelfmark"])
            if d0:
                u["date_from"], u["date_to"] = d0, d1
        u["shelfmark"] = sm.group(0) if sm else u["shelfmark"]
        s, r = label_parties(u["file_label"])
        u["senders"] = u["senders"] or s
        u["recipients"] = u["recipients"] or r
        if not u["date_from"]:
            u["date_from"], u["date_to"] = label_dates(u["file_label"])
        units.append(u)
    skipped = [u for u in units if not is_letter(u)]
    units = [u for u in units if is_letter(u)]
    reg = load_register()

    # score every (unit, register entry) with matching correspondents; at most one side may be
    # 'unknown' (Laßberg's side must always match)
    # (Harris: register date or Harris date; BNr = Laßberg's letter number at the head of the text)
    scored = {}  # unit_id -> [(entry, in_range, text_score, [party qualities], bnr_match)]
    elsewhere = defaultdict(list)  # unit_id -> register entries whose original is held elsewhere
    for u in units:
        ment, bnr = unit_mentions(u), unit_bnr(u)
        sc = []
        for e in reg:
            qs = [parties_match(u["senders"], e["senders"]), parties_match(u["recipients"], e["recipients"])]
            if None in qs or qs.count("unknown") > 1:
                continue
            ds = entry_dates(e)
            ts = max(text_score(ment, d) for d in ds)
            rg = any(in_range(d, u["date_from"], u["date_to"]) for d in ds)
            bm = bool(bnr) and e["harris"].get("bnr") == bnr
            if "unknown" in qs and not (ts or bm or rg and (u["date_from"] or "")[:10] == (u["date_to"] or "")[:10]):
                continue  # unknown correspondent: only with a single-day dating, text date or BNr
            if original_elsewhere(e):
                single_day = len(u["date_from"] or "") == 10 and u["date_from"] == u["date_to"]
                sure = all(q in ("gnd", "name") for q in qs)
                if sure and (ts >= 2 or bm or (rg and single_day)):  # same letter, not just the same period
                    elsewhere[u["unit_id"]].append(e)
                continue  # BLB holds only a draft/copy of a letter whose original survives elsewhere
            sc.append((e, rg, ts, qs, bm))
        scored[u["unit_id"]] = sc

    def pick(u):
        """-> (entry, method, competing entries) or (None, reason, competing)"""
        sc = scored[u["unit_id"]]
        rng = [x for x in sc if x[1]]
        # BNr. numbering restarts over the years: counts only with both correspondents identified
        # and a date that fits (BLB dating range or day+month in the text)
        bnr = [x for x in sc if x[4] and (x[1] or x[2] >= 2) and all(q in ("gnd", "name") for q in x[3])]
        if len(bnr) == 1:
            return bnr[0], "bnr", rng
        txt = sorted((x for x in sc if x[2] >= 2), key=lambda x: (x[2], x[1]), reverse=True)
        if txt and (len(txt) == 1 or (txt[0][2], txt[0][1]) > (txt[1][2], txt[1][1])):
            return txt[0], f"text{txt[0][2]}" + ("" if txt[0][1] else "-outofrange"), rng
        if len(rng) == 1 and not u["in_folder"]:
            return rng[0], "range", rng
        rng_blb = [x for x in rng if is_blb(x[0])]
        if len(rng_blb) == 1 and not u["in_folder"]:  # same pair+date also registered elsewhere
            return rng_blb[0], "rangeblb", rng
        return None, (f"{len(rng)} Kandidaten" if rng else "pair_only" if sc else "none"), rng

    picks = {u["unit_id"]: pick(u) for u in units}
    claims = defaultdict(list)
    for uid, (x, _, _) in picks.items():
        if x:
            claims[x[0]["key"]].append(uid)

    # folders (METS has no per-letter dates): letters found by text date are anchors; between two
    # anchors (and before the first / after the last) the open letters are assigned in date order
    # to the open BLB candidates whose date lies in that gap, if both counts agree
    by_record = defaultdict(list)
    for u in units:
        if u["in_folder"] and u["unit_type"] == "letter":
            by_record[u["record_id"]].append(u)
    for rid, us in by_record.items():
        cs = {x[0]["key"]: x[0] for u in us for x in scored[u["unit_id"]]
              if x[1] and is_blb(x[0]) and re.match(r"\d{4}-\d{2}-\d{2}", x[0]["date"])
              and all(q in ("gnd", "name") for q in x[3])}
        anchors = [(i, picks[u["unit_id"]][0][0]["date"]) for i, u in enumerate(us) if picks[u["unit_id"]][0]]
        bounds = [(-1, "0000")] + anchors + [(len(us), "9999")]
        for (i0, d0), (i1, d1) in zip(bounds, bounds[1:]):
            gap = [u for u in us[i0 + 1:i1] if not picks[u["unit_id"]][0]]
            free = sorted((e for k, e in cs.items() if k not in claims and d0 < e["date"] < d1),
                          key=lambda e: e["date"])
            if gap and len(free) == len(gap):
                for u, e in zip(gap, free):
                    x = next((x for x in scored[u["unit_id"]] if x[0]["key"] == e["key"]), None)
                    if x:
                        picks[u["unit_id"]] = (x, "order", picks[u["unit_id"]][2])
                        claims[e["key"]].append(u["unit_id"])

    def row(status, u=None, e=None, cands=(), note=""):
        r = dict.fromkeys(COLUMNS, "")
        r.update(status=status, accept="y" if status == "auto" else "", note=note)
        if u:
            r.update(unit_id=u["unit_id"], record_id=u["record_id"], shelfmark=u["shelfmark"],
                     unit_type=u["unit_type"], blb_label=u["file_label"],
                     blb_date=f"{u['date_from'] or ''}..{u['date_to'] or ''}",
                     pages=len(u["pages"]), alto_pages=sum(p["alto"] for p in u["pages"]))
        if e:
            r.update(letter_key=e["key"], register_date=e["date"], register_inst=e["inst"],
                     register_signatur=e["signatur"])
        r["candidates"] = "; ".join(f"{c['key']}|{c['date']}|{c['inst']}" for c in cands)
        return r

    METHOD_NOTE = {"bnr": "Laßbergs Briefnummer (Harris BNr.) im Brieftext",
                   "range": "einziger Kandidat im Datumsbereich",
                   "rangeblb": "einziger BLB-Kandidat im Datumsbereich (weitere an anderen Standorten)",
                   "text3": "Tag+Monat+Jahr im Brieftext", "text2": "Tag+Monat im Brieftext",
                   "order": "Mappe, Zuordnung nach Reihenfolge zwischen datierten Briefen"}
    rows, assigned = [], set()
    for u in units:
        x, method, rng = picks[u["unit_id"]]
        cands = [y[0] for y in rng]
        e = x[0] if x else None
        if not e and elsewhere[u["unit_id"]] and method in ("none", "pair_only"):
            rows.append(row("elsewhere", u, None, elsewhere[u["unit_id"]],
                            "Entwurf/Abschrift, Original an anderem Ort - nicht übernommen"))
            continue
        if not e:
            if method == "none":
                rows.append(row("unmatched", u, None, [], "kein Registereintrag für dieses Korrespondentenpaar"))
            elif method == "pair_only":
                po = [x[0] for x in scored[u["unit_id"]]]
                rows.append(row("unmatched", u, None, po[:12], "Paar im Register, aber kein Datum passt"))
            else:
                rows.append(row("ambiguous", u, None, cands, method))
            continue
        base, _, outside = method.partition("-")
        why = [METHOD_NOTE[base]] + (["Registerdatum außerhalb der BLB-Datierung"] if outside else [])
        conflict = len(claims[e["key"]]) > 1
        ok_sig = not e["signatur"] or norm_sig(e["signatur"]) == norm_sig(u["shelfmark"])
        why += [] if is_blb(e) else [f"Register: {e['inst'] or 'ohne Institution'}"]
        if is_blb(e) and "Badische" not in e["inst"]:
            why.append(f"Harris: K BLB (Register: {e['inst'] or 'ohne Institution'})")
        if len(entry_dates(e)) > 1:
            why.append(f"Harris datiert {e['harris']['date']} (Register {e['date']})")
        why += [] if ok_sig else [f"Signatur im Register: {e['signatur']}"]
        why += ["Registerbrief mehrfach beansprucht: " + ",".join(claims[e["key"]])] if conflict else []
        sure_names = all(q in ("gnd", "name") for q in x[3])
        why += [] if sure_names else [
            {"gnd_conflict": "GND weicht ab (Name passt)", "unknown": "Korrespondent unbekannt/leer"}[q]
            for q in x[3] if q in ("gnd_conflict", "unknown")]
        strong = sure_names and (method in ("text3", "bnr") or (method in ("range", "rangeblb") and not u["in_folder"]))
        status = "auto" if strong and is_blb(e) and ok_sig and not conflict else "proposed"
        rows.append(row(status, u, e, cands, "; ".join(why)))
        assigned.add(e["key"])
    unit_cands = defaultdict(list)
    for u in units:
        for x in scored[u["unit_id"]]:
            unit_cands[x[0]["key"]].append(u)
    for e in reg:
        if is_blb(e) and e["key"] not in assigned:
            us = unit_cands.get(e["key"], [])
            r = row("register", None, e, [], "")
            r["candidates"] = "; ".join(f"{u['unit_id']}|{u['shelfmark']}|{u['date_from']}..{u['date_to']}" for u in us[:12])
            r["note"] = "Korrespondentenpaar bei BLB vorhanden, Zuordnung offen" if us else "kein BLB-Datensatz gefunden"
            rows.append(r)

    # keep manual decisions from a previous run
    old = {}
    if OUT.exists():
        with OUT.open(encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter="\t"):
                old[r["unit_id"] or "reg:" + r["letter_key"]] = r
    for r in rows:
        o = old.get(r["unit_id"] or "reg:" + r["letter_key"])
        if o and o["accept"] != ("y" if o["status"] == "auto" else ""):  # decided by hand
            r["accept"], r["letter_key"], r["note"] = o["accept"], o["letter_key"], o["note"]

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, COLUMNS, delimiter="\t")
        w.writeheader()
        w.writerows(rows)
    stats = defaultdict(int)
    for r in rows:
        stats[r["status"]] += 1
    print(f"{len(units)} BLB letter units ({len(skipped)} non-letter units skipped), "
          f"{sum(is_blb(e) for e in reg)} BLB-registered letters -> {OUT}")
    print("  " + ", ".join(f"{k}: {v}" for k, v in sorted(stats.items())))
    print(f"  accepted (accept=y): {sum(r['accept'] == 'y' for r in rows)}")


if __name__ == "__main__":
    main()
