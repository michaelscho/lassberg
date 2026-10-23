"""Badische Landesbibliothek (BLB) Visual Library client: OAI-PMH harvest, METS parsing into
letter units, image/ALTO download and ALTO 3 -> PAGE 2019 conversion.

The ONLY place with BLB URLs. Interfaces (https://digital.blb-karlsruhe.de/wiki/schnittstellen):
  OAI-PMH   https://digital.blb-karlsruhe.de/oai/  set "blbknajvl" = Joseph von Laßberg
  image     /download/webcache/0/<pageId>          full resolution JPEG (ALTO coords are in it)
  ALTO 3    /download/fulltext/alto3/<pageId>
  record    /lassberg/content/titleinfo/<logId>    works for the file AND for each letter in it
  IIIF 2.0  /i3f/v20/<recordId>/manifest, canvas id = /i3f/v20/<recordId>/canvas/<pageId>
            (manifests exist only per record, not per contained letter)
Images: PDM 1.0 (METS accessCondition); BLB transcriptions: CC BY 4.0.

Local layout (gitignored, ~12 GB):  data/blb/_oai/mets/<recordId>.xml (harvest cache),
data/blb/_alto/<pageId>.xml (ALTO cache),
data/blb/<letter-key>/{NNNN.jpg, NNNN.alto.xml, NNNN.page.xml, blb.json}
"""
from __future__ import annotations

import re
import time
from pathlib import Path

import requests
from lxml import etree

REPO = Path(__file__).resolve().parents[1]
BLB_DIR = REPO / "data" / "blb"
METS_DIR = BLB_DIR / "_oai" / "mets"

HOST = "https://digital.blb-karlsruhe.de"
OAI = f"{HOST}/oai/"
OAI_SET = "blbknajvl"
USER_AGENT = "lassberg-edition (+https://michaelscho.github.io/lassberg/)"
MIN_INTERVAL = 0.3
TIMEOUT = 60
LICENCE_IMAGES = "https://creativecommons.org/publicdomain/mark/1.0/"

NS = {"mets": "http://www.loc.gov/METS/", "mods": "http://www.loc.gov/mods/v3",
      "xlink": "http://www.w3.org/1999/xlink"}
XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
LASSBERG_GND = "118778862"


def image_url(page_id: str) -> str:
    return f"{HOST}/download/webcache/0/{page_id}"


def alto_url(page_id: str) -> str:
    return f"{HOST}/download/fulltext/alto3/{page_id}"


def record_url(log_id: str) -> str:
    return f"{HOST}/lassberg/content/titleinfo/{log_id}"


def manifest_url(record_id: str) -> str:
    return f"{HOST}/i3f/v20/{record_id}/manifest"


def canvas_url(record_id: str, page_id: str) -> str:
    return f"{HOST}/i3f/v20/{record_id}/canvas/{page_id}"


# --- HTTP -------------------------------------------------------------------------------------

_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT
_last = 0.0


def get(url: str) -> requests.Response:
    """Rate-limited GET with retries; raises on final failure."""
    global _last
    err = None
    for attempt in range(4):
        wait = MIN_INTERVAL - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()
        try:
            r = _session.get(url, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
            err = RuntimeError(f"HTTP {r.status_code} for {url}")
            if r.status_code == 404:
                break
        except requests.RequestException as e:
            err = e
        time.sleep(3 * (attempt + 1))
    raise err


def list_identifiers() -> list[str]:
    ids, url = [], f"{OAI}?verb=ListIdentifiers&metadataPrefix=mets&set={OAI_SET}"
    while url:
        x = get(url).text
        ids += re.findall(r"<identifier>([^<]+)</identifier>", x)
        tok = re.search(r"<resumptionToken[^>]*>([^<]+)</resumptionToken>", x)
        url = f"{OAI}?verb=ListIdentifiers&resumptionToken={tok.group(1)}" if tok else None
    return ids


def fetch_mets(oai_id: str) -> bytes:
    return get(f"{OAI}?verb=GetRecord&metadataPrefix=mets&identifier={oai_id}").content


# --- METS -> letter units ---------------------------------------------------------------------

def _gnd(uri: str | None) -> str | None:
    m = re.search(r"gnd/([0-9X-]+)", uri or "")
    return m.group(1) if m else None


def _names(mods, role: str) -> list[dict]:
    out = []
    for n in mods.findall("mods:name", NS):
        if n.findtext(".//mods:roleTerm[@type='code']", namespaces=NS) == role:
            out.append({"gnd": _gnd(n.get("valueURI")),
                        "name": n.findtext("mods:displayForm", namespaces=NS) or ""})
    return out


def parse_record(path: Path) -> list[dict]:
    """One METS record -> its letter units. The record's own logical div (ID log<recordId>; may
    be nested under a parent 'file' div or have unrelated sibling divs) is either one letter, or a
    folder whose child divs TYPE=letter|additional|fragment each carry their own shelfmark and
    become one unit each ('additional' = Beilage, kept separate but flagged via unit_type).
    Other children (TYPE=section: Umschlag, "Zu: K ...") are left out. Inventories yield nothing."""
    t = etree.parse(str(path))
    rid = path.stem
    own = t.find(f".//mets:structMap[@TYPE='LOGICAL']//mets:div[@ID='log{rid}']", NS)
    if own is None or own.get("TYPE") not in ("file", "monograph", "letter"):
        return []
    mods = t.find(f".//mets:dmdSec[@ID='md{rid}']//mods:mods", NS)
    if mods is None:
        mods = t.find(".//mods:mods", NS)
    pages = {}  # physId -> {page_id, order, alto}
    alto = {f.get("ID")[4:] for f in t.findall(".//mets:fileGrp[@USE='FULLTEXT']/mets:file", NS)}
    for d in t.findall(".//mets:structMap[@TYPE='PHYSICAL']//mets:div[@TYPE='page']", NS):
        pid = d.get("ID")[4:]
        pages[d.get("ID")] = {"page_id": pid, "order": int(d.get("ORDER")), "alto": pid in alto}
    links = {}
    for sm in t.findall(".//mets:structLink/mets:smLink", NS):
        links.setdefault(sm.get(f"{{{NS['xlink']}}}from"), []).append(sm.get(f"{{{NS['xlink']}}}to"))

    def pages_of(log_id):
        to = [p for p in links.get(log_id, []) if p != "physroot"]
        if not to and "physroot" in links.get(log_id, []):
            return sorted(pages.values(), key=lambda p: p["order"])
        return sorted((pages[p] for p in to if p in pages), key=lambda p: p["order"])

    dates = {d.get("point") or "single": d.text
             for d in mods.findall(".//mods:originInfo/mods:dateCreated[@encoding='w3cdtf']", NS)}
    date_from = dates.get("start") or dates.get("single")
    shelf = mods.findtext(".//mods:shelfLocator", namespaces=NS)
    acc = mods.find(".//mods:accessCondition", NS)
    base = {
        "record_id": rid,
        "file_label": own.get("LABEL"),
        "file_shelfmark": shelf,
        "senders": _names(mods, "cre"),
        "recipients": _names(mods, "rcp"),
        "date_from": date_from,
        "date_to": dates.get("end") or date_from,
        "date_text": next((d.text for d in mods.findall(".//mods:originInfo/mods:dateCreated", NS)
                           if d.get("encoding") is None), None),
        "urn": mods.findtext(".//mods:identifier[@type='urn']", namespaces=NS),
        "licence": acc.get(XLINK_HREF) if acc is not None else None,
    }
    kids = [d for d in own.findall("mets:div", NS)
            if d.get("TYPE") in ("letter", "additional", "fragment") and d.get("LABEL")]
    if not any(d.get("TYPE") == "letter" for d in kids):
        return [{**base, "unit_id": rid, "unit_type": "letter", "shelfmark": shelf,
                 "in_folder": 0, "pages": pages_of(own.get("ID"))}]
    return [{**base, "unit_id": d.get("ID")[3:], "unit_type": d.get("TYPE"),
             "shelfmark": d.get("LABEL"), "in_folder": len(kids), "pages": pages_of(d.get("ID"))}
            for d in kids]


def load_units() -> list[dict]:
    units = []
    for f in sorted(METS_DIR.glob("*.xml"), key=lambda p: int(p.stem)):
        units += parse_record(f)
    return units


# --- ALTO 3 -> PAGE 2019 ----------------------------------------------------------------------

PAGE_NS = "http://schema.primaresearch.org/PAGE/gts/pagecontent/2019-07-15"


def alto_to_page(alto_bytes: bytes, image_filename: str) -> bytes:
    """Minimal conversion: TextBlock -> TextRegion, TextLine -> TextLine (rectangle Coords from
    HPOS/VPOS/WIDTH/HEIGHT, Baseline = bottom edge, since BLB's ALTO carries no baselines); text
    in TextEquiv/Unicode at line and region level. No Word level on purpose: src/pagexml_to_tei.py
    reads the first Unicode below each TextLine (word coordinates stay in the .alto.xml). Coordinates are the full-resolution image's pixels (verified against IIIF canvas)."""
    a = etree.fromstring(alto_bytes)
    an = a.nsmap.get(None) or "http://www.loc.gov/standards/alto/ns-v3#"
    A = lambda tag: f"{{{an}}}{tag}"  # noqa: E731
    P = lambda tag: f"{{{PAGE_NS}}}{tag}"  # noqa: E731
    page_el = a.find(f".//{A('Page')}")

    def box(el):
        x, y = int(float(el.get("HPOS", 0))), int(float(el.get("VPOS", 0)))
        w, h = int(float(el.get("WIDTH", 0))), int(float(el.get("HEIGHT", 0)))
        return x, y, w, h

    def coords(parent, el):
        x, y, w, h = box(el)
        etree.SubElement(parent, P("Coords"), points=f"{x},{y} {x + w},{y} {x + w},{y + h} {x},{y + h}")
        return x, y, w, h

    def text_equiv(parent, text):
        te = etree.SubElement(parent, P("TextEquiv"))
        etree.SubElement(te, P("Unicode")).text = text

    root = etree.Element(P("PcGts"), nsmap={None: PAGE_NS})
    meta = etree.SubElement(root, P("Metadata"))
    etree.SubElement(meta, P("Creator")).text = "lassberg-edition scripts/lib_blb.py (ALTO 3 from BLB Karlsruhe)"
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    etree.SubElement(meta, P("Created")).text = now
    etree.SubElement(meta, P("LastChange")).text = now
    page = etree.SubElement(root, P("Page"), imageFilename=image_filename,
                            imageWidth=str(int(float(page_el.get("WIDTH", 0)))),
                            imageHeight=str(int(float(page_el.get("HEIGHT", 0)))))
    regions = a.findall(f".//{A('TextBlock')}")
    if regions:
        ro = etree.SubElement(etree.SubElement(page, P("ReadingOrder")), P("OrderedGroup"),
                              id="ro_1")
        for i, tb in enumerate(regions):
            etree.SubElement(ro, P("RegionRefIndexed"), index=str(i), regionRef=f"r{i + 1}")
    ln = 0
    for i, tb in enumerate(regions):
        reg = etree.SubElement(page, P("TextRegion"), id=f"r{i + 1}", type="paragraph")
        coords(reg, tb)
        reg_lines = []
        for tl in tb.findall(A("TextLine")):
            ln += 1
            line = etree.SubElement(reg, P("TextLine"), id=f"l{ln}")
            x, y, w, h = coords(line, tl)
            etree.SubElement(line, P("Baseline"), points=f"{x},{y + h} {x + w},{y + h}")
            parts = []
            for s in tl:
                if s.tag == A("String"):
                    parts.append(s.get("CONTENT", ""))
                elif s.tag == A("SP"):
                    parts.append(" ")
                elif s.tag == A("HYP"):
                    parts.append(s.get("CONTENT", "-"))
            text = re.sub(r" +", " ", "".join(parts)).strip()
            text_equiv(line, text)
            reg_lines.append(text)
        text_equiv(reg, "\n".join(reg_lines))
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", pretty_print=True)


# --- ALTO cache (shared by match.py's text-date hints and download.py) ------------------------

ALTO_CACHE = BLB_DIR / "_alto"


def cached_alto(page_id: str, fetch: bool = True) -> bytes | None:
    f = ALTO_CACHE / f"{page_id}.xml"
    if f.exists():
        return f.read_bytes()
    if not fetch:
        return None
    ALTO_CACHE.mkdir(parents=True, exist_ok=True)
    data = get(alto_url(page_id)).content
    f.write_bytes(data)
    return data


def alto_text(alto_bytes: bytes) -> str:
    a = etree.fromstring(alto_bytes)
    lines = []
    for tl in a.iter("{*}TextLine"):
        lines.append(" ".join(s.get("CONTENT", "") for s in tl.iter("{*}String")))
    return "\n".join(lines)
