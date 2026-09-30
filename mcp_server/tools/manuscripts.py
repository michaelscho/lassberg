"""Manuscript tools (register + Handschriftenportal), plain functions with no MCP dependency.

Ids: manuscripts are "lassberg-witness-NNNN" (4-digit zero-padded), letters
"lassberg-letter-NNNN". HSP ids look like "HSP-666242f4-0675-3121-b0d6-be697c7a9b20".
Data comes from build/entities.json + build/letters.jsonl (register, mentions) and the local HSP
mirror data/hsp/ (gitignored; missing manuscripts are fetched live from the HSP and mirrored).
The HSP data is a snapshot as of each file's `fetched_at`; description licences are always returned.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts" / "manuscripts"))

import lib_hsp as hsp  # noqa: E402

_cache: dict = {}


def _load(name: str):
    path = REPO_ROOT / "build" / name
    mtime = path.stat().st_mtime
    hit = _cache.get(name)
    if hit and hit[0] == mtime:
        return hit[1]
    if name.endswith(".jsonl"):
        data = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
    _cache[name] = (mtime, data)
    return data


def _witnesses() -> dict:
    return _load("entities.json")["witnesses"]


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", (s or "").lower())).strip()


def _mention_counts() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for l in _load("letters.jsonl"):
        for wid in (l.get("mentions") or {}).get("witnesses", []):
            out.setdefault(wid, []).append(l["id"])
    return out


def _summary_row(wid: str, e: dict, mentions: dict) -> dict:
    return {"witness_id": wid, "label": e.get("label"), "settlement": e.get("settlement"),
            "repository": e.get("repository"), "shelfmark": e.get("signature"), "hsp_id": e.get("hsp_id"),
            "n_letters": len(mentions.get(wid, []))}


def find_manuscript(query: str, limit: int = 10) -> list[dict]:
    """Fuzzy search in the manuscript register (name, shelfmark, former shelfmarks, place, HSP id)."""
    from rapidfuzz import fuzz
    q = _norm(query)
    mentions = _mention_counts()
    scored = []
    for wid, e in _witnesses().items():
        if query.strip() in (wid, e.get("hsp_id")):
            scored.append((100, wid, e))
            continue
        cands = [e.get("label"), e.get("signature"), e.get("repository"), e.get("settlement"),
                 e.get("provenance")] + (e.get("alt_ids", {}).get("former") or [])
        best = max((fuzz.partial_ratio(q, _norm(c)) if len(q) >= 4 else (100 if q in _norm(c).split() else 0)
                    for c in cands if c), default=0)
        if best >= 85:
            scored.append((best, wid, e))
    scored.sort(key=lambda x: (-x[0], -len(mentions.get(x[1], [])), x[1]))
    return [{**_summary_row(wid, e, mentions), "score": s} for s, wid, e in scored[:limit]]


def manuscript_mentions(witness_id: str) -> list[dict]:
    """Letters that mention a manuscript, with date, sender/recipient and a text excerpt around
    the annotated passage (from the transcription)."""
    from tei_text import load_letter
    ents = _load("entities.json")
    persons = ents["persons"]
    out = []
    for l in _load("letters.jsonl"):
        if witness_id not in (l.get("mentions") or {}).get("witnesses", []):
            continue
        excerpts = []
        if l.get("file"):
            try:
                _, _, toks, rng, lin = load_letter(l["id"])
                for r in (lin.rs if lin else []):
                    if r["attrs"].get("type") == "witness" and (r["attrs"].get("key") or "").endswith(witness_id):
                        a, b = max(0, r["lin_start"] - 120), min(len(lin.text), r["lin_end"] + 120)
                        excerpts.append(("…" if a else "") + lin.text[a:b] + ("…" if b < len(lin.text) else ""))
            except Exception as exc:  # excerpt is best effort
                excerpts.append(f"(excerpt unavailable: {exc})")
        name = lambda pid: (persons.get(pid) or {}).get("label") if pid else None  # noqa: E731
        out.append({"letter_id": l["id"], "date": l["sent"]["date"], "sender": name(l["sent"]["person"]),
                    "recipient": name(l["received"]["person"]), "excerpts": excerpts})
    out.sort(key=lambda r: (r["date"] or "", r["letter_id"]))
    return out


def hsp_search(query: str, limit: int = 10, live: bool = False) -> list[dict]:
    """Search the local HSP description index (content, author, former shelfmark, provenance);
    live=True adds hits from the live HSP Kulturobjekt search (spell correction: verify hits)."""
    hits = [{"source": "local", **h} for h in hsp.local_search(query, limit)]
    if live:
        known = {h["hsp_id"] for h in hits}
        try:
            for k in hsp.search(query, rows=limit):
                if k["id"] not in known:
                    hits.append({"source": "live", "hsp_id": k["id"], "shelfmark": k.get("idno-display"),
                                 "msname": hsp.clean_kod_title(k.get("title-display")),
                                 "settlement": k.get("settlement-display"), "repository": k.get("repository-display"),
                                 "date": "; ".join(k.get("orig-date-lang-display") or [])})
        except hsp.HspError as exc:
            hits.append({"source": "error", "error": str(exc)})
    return hits


def hsp_manuscript(id: str, description: str = "summary") -> dict:
    """Core data, portal URL and catalogue description(s) of a manuscript from the local HSP mirror
    (fetched live and mirrored if missing). `id` = lassberg-witness-NNNN or an HSP id."""
    wid = None
    if id.startswith("lassberg-witness-"):
        e = _witnesses().get(id)
        if not e:
            return {"error": f"unknown witness id {id}"}
        wid, hid = id, e.get("hsp_id")
        if not hid:
            return {"witness_id": wid, "error": "register entry has no HSP id", "register": e}
    else:
        hid = id
        wid = next((k for k, e in _witnesses().items() if e.get("hsp_id") == hid), None)
    kod = hsp.load_kod_local(hid)
    if kod is None:
        try:
            from mirror_hsp import mirror_one, save_manifest
            manifest, failed = hsp.load_manifest(), []
            mirror_one(hid, wid, manifest, False, failed)
            save_manifest(manifest)
            kod = hsp.load_kod_local(hid)
        except Exception as exc:
            return {"witness_id": wid, "hsp_id": hid, "error": f"not in local mirror and live fetch failed: {exc}"}
    if kod is None:
        return {"witness_id": wid, "hsp_id": hid, "error": "HSP data unavailable"}
    manifest = hsp.load_manifest()
    res = {
        "witness_id": wid, "hsp_id": hid, "portal_url": hsp.portal_url(hid),
        "core": {k: kod.get(k) for k in ("settlement-display", "repository-display", "idno-display", "title-display",
                                          "orig-date-lang-display", "orig-place-display", "leaves-count-display",
                                          "material-display", "dimensions-display", "object-type-display")},
        "fetched_at": (manifest.get(hid) or {}).get("fetched_at"),
        "core_licence": {k: (manifest.get(hid) or {}).get(k) for k in ("licence_status", "licence_url")},
        "descriptions": [],
        "note": "HSP data is a snapshot (fetched_at); each description carries its own licence.",
    }
    for did in hsp.local_descriptions(hid):
        d = hsp.parse_description(hsp.desc_path(did).read_bytes())
        entry = {"id": did, "citation": d["citation"], "licence_status": d["licence_status"],
                 "licence_url": d["licence_url"], "portal_url": hsp.portal_url(did),
                 "fetched_at": (manifest.get(did) or {}).get("fetched_at")}
        if description == "summary":
            entry.update({"headline": d["headline"], "head": d["head"], "summary": d["summary"],
                          "items": d["items"][:30], "history": d["history"][:2000],
                          "former_shelfmarks": d["msidentifier"].get("former_shelfmarks", [])})
        elif description == "full":
            entry["fulltext"] = d["fulltext"][:30000]
            entry["truncated"] = len(d["fulltext"]) > 30000
        res["descriptions"].append(entry)
    return res
