"""Handschriftenportal (HSP) client, local mirror access and description parsing.

The ONLY place with HSP URLs: the HSP API is undocumented (and sends no CORS headers); once the
official API exists, only this module has to change. Everything else (MCP tools, mirror,
website export, scan scripts) goes through the functions here.

Mirror layout (gitignored, licences!):  data/hsp/kod/<KOD-ID>.{json,xml}, data/hsp/desc/<DESC-ID>.xml,
data/hsp/manifest.json, data/hsp/index.sqlite
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path

import requests
from lxml import etree

REPO = Path(__file__).resolve().parents[1]
HSP_DIR = REPO / "data" / "hsp"
INDEX_DB = HSP_DIR / "index.sqlite"

API = "https://handschriftenportal.de/api"
PORTAL = "https://handschriftenportal.de/search?hspobjectid="
USER_AGENT = "lassberg-edition (+https://michaelscho.github.io/lassberg/)"
MIN_INTERVAL = 1.0
TIMEOUT = 30
TEI_NS = {"t": "http://www.tei-c.org/ns/1.0"}

# Licence gate (website export): only these licence URL prefixes count as free. Everything else,
# including unknown, is cite-and-link only.
FREE_LICENCE_PREFIXES = (
    "https://creativecommons.org/publicdomain/zero/",
    "http://creativecommons.org/publicdomain/zero/",
    "https://creativecommons.org/licenses/by/",
    "http://creativecommons.org/licenses/by/",
    "https://creativecommons.org/licenses/by-sa/",
    "http://creativecommons.org/licenses/by-sa/",
)

_last_request = 0.0


class HspError(RuntimeError):
    pass


def _get(url: str, params: dict | None = None) -> requests.Response:
    global _last_request
    wait = MIN_INTERVAL - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    try:
        resp = requests.get(url, params=params, timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})
    except requests.RequestException as exc:
        raise HspError(f"HSP request failed ({url}): {exc}") from exc
    finally:
        _last_request = time.monotonic()
    if resp.status_code != 200:
        raise HspError(f"HSP returned HTTP {resp.status_code} for {resp.url}")
    return resp


# --------------------------------------------------------------------------------- live API

def search(q: str, rows: int = 10, start: int = 0) -> list[dict]:
    """Kulturobjekt search. NB: the HSP applies spelling correction - always check the hit's
    idno-display / title-display yourself."""
    data = _get(f"{API}/kods/search", {"q": q, "rows": rows, "start": start}).json()
    return data.get("payload", [])[:rows]


def get_kod(hsp_id: str) -> dict:
    return _get(f"{API}/kods/{hsp_id}").json()


def get_tei(hsp_id: str) -> bytes:
    """TEI of a Kulturobjekt or of a description (both addressed by their HSP-ID)."""
    return _get(f"{API}/tei/{hsp_id}").content


def description_ids(kod_tei: bytes | str) -> list[str]:
    root = etree.fromstring(kod_tei if isinstance(kod_tei, bytes) else kod_tei.encode("utf-8"))
    seen, out = set(), []
    for idx in root.iter("{%s}index" % TEI_NS["t"]):
        ref = (idx.get("copyOf") or "").lstrip("#")
        if ref.startswith("HSP-") and ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def portal_url(hsp_id: str) -> str:
    return PORTAL + hsp_id


# --------------------------------------------------------------------------------- licences

def licence_of(tei: bytes | str) -> dict:
    """{status: free|restricted|unknown, url}. Free only if every <availability> says free AND
    every licence URL is on the positive list."""
    root = etree.fromstring(tei if isinstance(tei, bytes) else tei.encode("utf-8"))
    avail = root.findall(".//t:teiHeader//t:availability", TEI_NS)
    if not avail:
        return {"status": "unknown", "url": None}
    urls = [l.get("target") for a in avail for l in a.findall(".//t:licence", TEI_NS) if l.get("target")]
    statuses = {a.get("status") for a in avail}
    url = urls[0] if urls else None
    if statuses == {"free"} and urls and all(is_free_licence(u) for u in urls):
        return {"status": "free", "url": url}
    if "restricted" in statuses:
        return {"status": "restricted", "url": url}
    return {"status": "unknown", "url": url}


def is_free_licence(url: str | None) -> bool:
    return bool(url) and url.startswith(FREE_LICENCE_PREFIXES)


# --------------------------------------------------------------------------------- mirror

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def kod_paths(hsp_id: str) -> tuple[Path, Path]:
    return HSP_DIR / "kod" / f"{hsp_id}.json", HSP_DIR / "kod" / f"{hsp_id}.xml"


def desc_path(desc_id: str) -> Path:
    return HSP_DIR / "desc" / f"{desc_id}.xml"


def load_manifest() -> dict:
    p = HSP_DIR / "manifest.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def load_kod_local(hsp_id: str) -> dict | None:
    p, _ = kod_paths(hsp_id)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def local_descriptions(hsp_id: str) -> list[str]:
    """Description IDs of a mirrored Kulturobjekt that exist locally."""
    _, x = kod_paths(hsp_id)
    if not x.exists():
        return []
    return [d for d in description_ids(x.read_bytes()) if desc_path(d).exists()]


# --------------------------------------------------------------------------------- parsing

def _txt(el) -> str:
    if el is None:
        return ""
    s = re.sub(r"\s+", " ", " ".join(el.itertext())).strip()
    return re.sub(r"\s+([,.;:!?)\]’‘“”])", r"\1", re.sub(r"([(\[])\s+", r"\1", s))


def clean_kod_title(title_display: str | None) -> str:
    """title-display like '‘Kolmarer Liederhandschrift’' -> 'Kolmarer Liederhandschrift'."""
    return re.sub(r"[‘’‚“”„›‹]", "", title_display or "").strip()


def parse_description(xml: bytes | str) -> dict:
    """Works on a local description (or Kulturobjekt) TEI file."""
    root = etree.fromstring(xml if isinstance(xml, bytes) else xml.encode("utf-8"))
    t = TEI_NS
    ms = root.find(".//t:text//t:msDesc", t)
    if ms is None:
        ms = root.find(".//t:sourceDesc/t:msDesc", t)
    lic = licence_of(xml)
    out = {
        "citation": _txt(root.find(".//t:teiHeader//t:titleStmt/t:title", t)),
        "licence_url": lic["url"],
        "licence_status": lic["status"],
        "msidentifier": {}, "head": "", "headline": "", "summary": "", "items": [],
        "history": "", "index_terms": [], "bibliography": [], "fulltext": "",
    }
    if ms is None:
        return out
    ident = ms.find("t:msIdentifier", t)
    if ident is not None:
        former, other = [], []
        for alt in ident.findall("t:altIdentifier", t):
            v = _txt(alt.find("t:idno", t))
            if not v:
                continue
            (former if alt.get("type") == "former" else other).append(
                {"type": alt.get("type"), "value": v, "collection": _txt(alt.find("t:collection", t))})
        idno = [i for i in ident.findall("t:idno", t) if not i.get("type")]
        out["msidentifier"] = {
            "settlement": _txt(ident.find("t:settlement", t)),
            "repository": _txt(ident.find("t:repository", t)),
            "shelfmark": _txt(idno[0]) if idno else "",
            "former_shelfmarks": [f["value"] for f in former],
            "alt_identifiers": other,
        }
    head = ms.find("t:head", t)
    if head is not None:
        out["head"] = _txt(head.find("t:title", t))
        out["headline"] = _txt(head.find("t:note[@type='headline']", t))
    out["summary"] = _txt(ms.find(".//t:msContents/t:summary", t))
    for item in ms.iterfind(".//t:msItem", t):
        entry = {
            "locus": _txt(item.find("t:note[@type='text']", t)),
            "author": _txt(item.find("t:author", t)),
            "title": _txt(item.find("t:title", t)),
            "incipit": _txt(item.find("t:incipit", t)),
        }
        if any(entry.values()):
            out["items"].append(entry)
    out["history"] = " ".join(_txt(p) for p in ms.iterfind(".//t:history/t:p", t))
    for idx in ms.iterfind(".//t:index", t):
        name = idx.get("indexName") or ""
        if name.startswith("norm_"):
            continue
        for term in idx.findall("t:term", t):
            text = _txt(term)
            if text:
                out["index_terms"].append({"index": name, "type": term.get("type"), "text": text,
                                           "ref": term.get("ref")})
    out["bibliography"] = [_txt(b) for b in ms.iterfind(".//t:additional/t:listBibl//t:bibl", t) if _txt(b)]
    out["fulltext"] = _txt(ms)
    return out


# --------------------------------------------------------------------------------- local search

SIGNATURE_RE = re.compile(r"\b(cod|cgm|cpg|cpl|clm|ms|hs|nr|cim|mscr|hb|ub|mgq|mgf|ms\.)\b|\d", re.I)


def _norm_sig(s: str) -> str:
    return re.sub(r"[^a-z0-9äöüß]+", " ", (s or "").lower()).strip()


def local_search(query: str, limit: int = 10) -> list[dict]:
    """Search the local index (data/hsp/index.sqlite): signature-like queries first (exact/fuzzy
    on shelfmark + former shelfmarks), otherwise FTS5 BM25 with snippet."""
    if not INDEX_DB.exists():
        return []
    con = sqlite3.connect(INDEX_DB)
    con.row_factory = sqlite3.Row
    hits: dict[str, dict] = {}
    try:
        q = query.strip()
        if SIGNATURE_RE.search(q):
            try:
                from rapidfuzz import fuzz
            except ImportError:  # pragma: no cover
                fuzz = None
            nq = _norm_sig(q)
            for row in con.execute("SELECT hsp_id, witness_id, shelfmark, former_shelfmarks, msname FROM ms"):
                cands = [row["shelfmark"]] + [x for x in (row["former_shelfmarks"] or "").split(" | ") if x]
                best = 0.0
                for c in cands:
                    nc = _norm_sig(c)
                    if not nc:
                        continue
                    if nc == nq:
                        best = 100.0
                    elif fuzz:
                        # whole-token match avoids "63" matching "163"
                        s = fuzz.ratio(nq, nc)
                        best = max(best, s)
                if best >= 90:
                    hits[row["hsp_id"]] = {"hsp_id": row["hsp_id"], "witness_id": row["witness_id"],
                                           "shelfmark": row["shelfmark"], "msname": row["msname"],
                                           "score": best, "snippet": "signature match"}
        fts = " ".join(f'"{w}"*' for w in re.findall(r"\w+", q))
        if fts:
            rows = con.execute(
                "SELECT hsp_id, witness_id, shelfmark, msname, bm25(ms_fts) AS s, "
                "snippet(ms_fts, -1, '[', ']', ' … ', 12) AS snip "
                "FROM ms_fts JOIN ms ON ms.rowid = ms_fts.rowid WHERE ms_fts MATCH ? "
                "ORDER BY s LIMIT ?", (fts, limit)).fetchall()
            for r in rows:
                hits.setdefault(r["hsp_id"], {"hsp_id": r["hsp_id"], "witness_id": r["witness_id"],
                                              "shelfmark": r["shelfmark"], "msname": r["msname"],
                                              "score": round(-r["s"], 3), "snippet": r["snip"]})
    finally:
        con.close()
    return sorted(hits.values(), key=lambda h: -h["score"])[:limit]
