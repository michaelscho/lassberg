#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, re, json, time, logging, hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception_type
from lxml import etree
import requests
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_date
from openai import OpenAI

# -----------------------
# HARD-CODED FILE PATHS
# -----------------------
INPUT_TEI_PATH  = Path("../data/register/lassberg-literature.xml")
OUTPUT_TEI_PATH = Path("../data/register/lassberg-literature.ENRICHED.xml")

# -----------------------
# CONFIG
# -----------------------
MODEL = os.environ.get("OPENAI_MODEL", "gpt-5-mini-2025-08-07")
#TEMPERATURE = 0.1
MAX_TOKENS = 2000

CACHE_DIR = Path(os.environ.get("TEI_UPGRADE_CACHE", ".tei_upgrade_cache"))
CACHE_DIR.mkdir(exist_ok=True)

TEI_NS = "http://www.tei-c.org/ns/1.0"
NSMAP = {"tei": TEI_NS}

IDNO_TYPES = {
    "uri","gnd","gw","vd16","vd17","vd18","handschriftencensus",
    "geschichtsquellen","opac-ri","googlebooks","doi"
}

HEADERS = {
    "User-Agent": "TEI-Enricher/1.0 (+mailto:you@example.org)"
}

GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY")

# -----------------------
# PROMPTS
# -----------------------
SYSTEM_PROMPT = """You are a meticulous bibliographic editor and TEI specialist.
You receive: (1) ONE original TEI <bibl> or <biblStruct>, and (2) harvested metadata JSON from trusted authority URIs (GND/lobid, Handschriftencensus, Geschichtsquellen, RI-OPAC, Google Books, DOI).

Authority preference rule (IMPORTANT):
- If both Handschriftencensus and Geschichtsquellen provide conflicting facts, PREFER Handschriftencensus.

Your job:
- Produce ONE normalized TEI P5 <biblStruct> fragment (no commentary) that corrects structure and fills fields ONLY with information present in either the original XML or the harvested JSON context. If something is unknown, leave it out—do not invent.
- Prefer <biblStruct> with <analytic>/<monogr> for articles/chapters; plain <monogr> for books; type="work" for conceptual medieval works (authority IDs only).
- Preserve or map the original @xml:id if present.
- Dates: use @when or @from/@to; if JSON gives a clear year or range, use it; otherwise omit.
- Titles: add @level="m|a|j|s" and xml:lang when evident; keep titles clean (no person/editor prose inside <title>).
- People/places: if local anchors (e.g., #lassberg-...) are present in the original, keep them via @ref; otherwise use plain text names.
- Identifiers: keep all authority IDs you’re given; map plain links to <idno type="uri">.
- Do NOT include <bibl> in the output—always <biblStruct>.
- Output must be a single well-formed XML fragment beginning with <biblStruct ...> and ending with </biblStruct>.
"""

USER_TEMPLATE = """Convert the entry below into one <biblStruct>, using ONLY facts from the original or the context JSON. If Handschriftencensus and Geschichtsquellen disagree, PREFER Handschriftencensus.

<original>
{fragment}
</original>

<context-json>
{context_json}
</context-json>
"""

# -----------------------
# OPENAI
# -----------------------
def openai_client() -> OpenAI:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI()

class TransientError(Exception): pass

@retry(
    reraise=True,
    stop=stop_after_attempt(5),
    wait=wait_exponential_jitter(initial=1, max=20),
    retry=retry_if_exception_type(TransientError),
)
def call_llm(client: OpenAI, fragment: str, context: Dict[str, Any]) -> str:
    try:
        resp = client.responses.create(
            model=MODEL,
            #temperature=TEMPERATURE,
            max_output_tokens=MAX_TOKENS,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_TEMPLATE.format(
                    fragment=fragment,
                    context_json=json.dumps(context, ensure_ascii=False, indent=2)
                )},
            ],
        )
        txt = getattr(resp, "output_text", None)
        if not txt:
            chunks = []
            for item in getattr(resp, "output", []) or []:
                if getattr(item, "type", "") == "message":
                    for part in getattr(item, "content", []) or []:
                        if part.get("type") == "output_text":
                            chunks.append(part.get("text",""))
            txt = "".join(chunks).strip()
        if not txt:
            raise TransientError("Empty response")

        m = re.search(r"<biblStruct\b.*?</biblStruct>", txt, flags=re.DOTALL)
        if not m:
            raise TransientError("No <biblStruct> block found")
        return m.group(0).strip()
    except Exception as e:
        msg = str(e)
        if any(k in msg.lower() for k in ["timeout","rate limit","temporarily","connection reset","503","overloaded"]):
            raise TransientError(msg)
        raise

# -----------------------
# UTIL
# -----------------------
def parse_xml(path: Path) -> etree._ElementTree:
    parser = etree.XMLParser(remove_blank_text=False)
    return etree.parse(str(path), parser)

def serialize(elem: etree._Element) -> str:
    return etree.tostring(elem, encoding="unicode")

def sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def cache_get(url: str) -> Optional[Dict[str, Any]]:
    p = CACHE_DIR / (sha1(url) + ".json")
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None

def cache_put(url: str, data: Dict[str, Any]) -> None:
    p = CACHE_DIR / (sha1(url) + ".json")
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()

def safe_get_text(el: Optional[BeautifulSoup], default=""):
    return normalize_text(el.get_text(" ", strip=True)) if el else default

# -----------------------
# HARVESTERS (per authority)
# -----------------------
def harvest_gnd(id_value: str) -> Dict[str, Any]:
    url = f"https://lobid.org/gnd/{id_value}.json"
    cached = cache_get(url)
    if cached: return cached
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    out = {"source": "gnd", "url": url, "raw": data}
    out["preferredName"] = data.get("preferredName")
    out["variantName"] = data.get("variantName")
    out["title"] = data.get("title")
    out["dates"] = data.get("dateOfBirth") or data.get("dateOfPublication") or data.get("date")
    out["type"] = data.get("type")
    cache_put(url, out)
    time.sleep(0.2)
    return out

def harvest_handschriftencensus(url: str) -> Dict[str, Any]:
    cached = cache_get(url)
    if cached: return cached
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("h1")
    labels = {}
    for row in soup.select("table, dl"):
        text = row.get_text(" ", strip=True)
        if any(k in text for k in ["Autor","Werk","Titel"]):
            labels["block"] = text[:400]
            break
    out = {
        "source": "handschriftencensus",
        "url": url,
        "title": safe_get_text(title),
        "note": labels.get("block","")
    }
    cache_put(url, out)
    time.sleep(0.3)
    return out

def harvest_geschichtsquellen(url: str) -> Dict[str, Any]:
    cached = cache_get(url)
    if cached: return cached
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    h1 = soup.find("h1")
    meta = soup.find("div", {"id":"meta"}) or soup.find("main")
    out = {
        "source": "geschichtsquellen",
        "url": url,
        "title": safe_get_text(h1),
        "note": safe_get_text(meta)[:600]
    }
    cache_put(url, out)
    time.sleep(0.3)
    return out

def harvest_ri_opac(url: str) -> Dict[str, Any]:
    cached = cache_get(url)
    if cached: return cached
    r = requests.get(url, headers=HEADERS, timeout=25)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    page_title = soup.find("title")
    h1 = soup.find("h1")
    out = {
        "source": "opac-ri",
        "url": url,
        "title": normalize_text((h1 or page_title).get_text()) if (h1 or page_title) else "",
    }
    m = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", soup.get_text(" ", strip=True))
    if m:
        out["year_guess"] = m.group(0)
    cache_put(url, out)
    time.sleep(0.2)
    return out

def harvest_googlebooks(url_or_id: str) -> Dict[str, Any]:
    out = {"source": "googlebooks", "id": url_or_id}
    if GOOGLE_BOOKS_API_KEY:
        vol_id = None
        if "books.google" in url_or_id and "id=" in url_or_id:
            m = re.search(r"[?&]id=([^&]+)", url_or_id)
            vol_id = m.group(1) if m else None
        elif re.fullmatch(r"[\w-]+", url_or_id):
            vol_id = url_or_id
        if vol_id:
            api = f"https://www.googleapis.com/books/v1/volumes/{vol_id}?key={GOOGLE_BOOKS_API_KEY}"
            cached = cache_get(api)
            if cached: return cached
            r = requests.get(api, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                data = r.json()
                info = data.get("volumeInfo", {})
                out.update({
                    "url": api,
                    "title": info.get("title"),
                    "subtitle": info.get("subtitle"),
                    "authors": info.get("authors"),
                    "publisher": info.get("publisher"),
                    "publishedDate": info.get("publishedDate"),
                    "industryIdentifiers": info.get("industryIdentifiers"),
                })
                cache_put(api, out)
                time.sleep(0.2)
                return out
    return out

def harvest_generic_uri(url: str) -> Dict[str, Any]:
    cached = cache_get(url)
    if cached: return cached
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.find("title")
        out = {"source":"uri", "url": url, "title": safe_get_text(title)}
        cache_put(url, out)
        time.sleep(0.2)
        return out
    except Exception:
        return {"source":"uri", "url": url}

# -----------------------
# CONTEXT BUILD & PREFS
# -----------------------
def build_context_from_idnos(idnos: List[etree._Element]) -> Dict[str, Any]:
    harvested: List[Dict[str, Any]] = []

    for node in idnos:
        t = (node.get("type") or "").strip().lower()
        val = normalize_text(node.text)
        if not val:
            continue
        try:
            if t == "gnd":
                gnd_id = val.split("/")[-1] if "/" in val else val
                harvested.append(harvest_gnd(gnd_id))
            elif t == "handschriftencensus":
                harvested.append(harvest_handschriftencensus(val))
            elif t == "geschichtsquellen":
                harvested.append(harvest_geschichtsquellen(val))
            elif t in {"opac-ri","riopac","regesta-imperii","ri"}:
                harvested.append(harvest_ri_opac(val))
            elif t == "googlebooks":
                harvested.append(harvest_googlebooks(val))
            elif t in {"doi"}:
                harvested.append({"source":"doi", "doi": val, "url": f"https://doi.org/{val}"})
            elif t in {"vd16","vd17","vd18","gw"}:
                harvested.append({"source": t, "id": val})
            elif t in {"uri","varia"}:
                harvested.append(harvest_generic_uri(val))
            else:
                if re.match(r"^https?://", val):
                    harvested.append(harvest_generic_uri(val))
                else:
                    harvested.append({"source": t or "unknown-id", "id": val})
        except Exception as e:
            harvested.append({"source": t or "unknown", "value": val, "error": str(e)})

    # ---- Preference: Handschriftencensus over Geschichtsquellen
    has_hsc = any(h.get("source") == "handschriftencensus" for h in harvested)
    has_gsq = any(h.get("source") == "geschichtsquellen" for h in harvested)
    if has_hsc and has_gsq:
        # Reorder to put HSC first and annotate preference
        harvested.sort(key=lambda h: 0 if h.get("source")=="handschriftencensus" else 1)

    # small heuristic summary
    summary: Dict[str, Any] = {
        "harvested": harvested,
        "authority_preference": ["handschriftencensus","geschichtsquellen"] if has_hsc and has_gsq else []
    }
    # candidate titles/years (optional hints)
    titles = [h.get("title") for h in harvested if h.get("title")]
    if titles:
        summary["candidateTitles"] = list(dict.fromkeys(titles))[:3]
    years = []
    for h in harvested:
        y = h.get("year_guess") or h.get("publishedDate")
        if isinstance(y, str):
            try:
                years.append(str(parse_date(y, default=None).year))
            except Exception:
                m = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", y)
                if m: years.append(m.group(0))
    if years:
        summary["candidateYears"] = sorted(set(years))[:3]
    return summary

def build_llm_context(bibl_elem: etree._Element) -> Dict[str, Any]:
    idnos = bibl_elem.xpath(".//tei:idno", namespaces=NSMAP)
    ctx = build_context_from_idnos(idnos)
    ctx["idnos_raw"] = [{
        "type": (n.get("type") or "").strip(),
        "text": normalize_text(n.text)
    } for n in idnos if (n.text or "").strip()]
    return ctx

# -----------------------
# XML PIPELINE
# -----------------------
def new_listbibl_from_structs(structs_xml: List[str]) -> etree._Element:
    lb = etree.Element(f"{{{TEI_NS}}}listBibl")
    for frag in structs_xml:
        try:
            node = etree.fromstring(frag)
            lb.append(node)
        except Exception:
            note = etree.Element(f"{{{TEI_NS}}}note")
            note.text = frag
            lb.append(note)
    return lb

def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    client = openai_client()

    if not INPUT_TEI_PATH.exists():
        raise SystemExit(f"Input TEI not found: {INPUT_TEI_PATH}")

    tree = parse_xml(INPUT_TEI_PATH)
    root = tree.getroot()

    list_bibl = root.xpath("//tei:listBibl", namespaces=NSMAP)
    if not list_bibl:
        raise SystemExit("No <listBibl> found.")
    list_bibl = list_bibl[0]

    candidates = list_bibl.xpath("./tei:bibl | ./tei:biblStruct", namespaces=NSMAP)
    logging.info(f"Found {len(candidates)} entries")

    improved, errors = [], 0

    for i, b in enumerate(candidates, start=1):
        xml_id = b.get("{http://www.w3.org/XML/1998/namespace}id") or ""
        logging.info(f"[{i}/{len(candidates)}] Upgrading {xml_id or '<no @xml:id>'}")

        original_xml = serialize(b)
        context = build_llm_context(b)

        try:
            upgraded = call_llm(client, original_xml, context)
            etree.fromstring(upgraded)  # validate
            improved.append(upgraded)
        except Exception as e:
            errors += 1
            logging.warning(f"  -> Failed: {e}. Keeping original entry.")
            improved.append(original_xml)

        time.sleep(0.25)  # be gentle to all services

    new_lb = new_listbibl_from_structs(improved)
    parent = list_bibl.getparent()
    parent.replace(list_bibl, new_lb)

    OUTPUT_TEI_PATH.parent.mkdir(parents=True, exist_ok=True)
    tree.write(OUTPUT_TEI_PATH, encoding="utf-8", xml_declaration=True, pretty_print=True)
    logging.info(f"Done. Wrote {OUTPUT_TEI_PATH}. Failures: {errors}/{len(candidates)}")

if __name__ == "__main__":
    # No CLI args; paths are hardcoded above.
    main()
