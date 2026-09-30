#!/usr/bin/env python3
"""Website export for manuscripts (offline; reads build/ + the local HSP mirror data/hsp/).

Writes
  json/explore/manuscripts.json      small index of all registered manuscripts
  json/hsp/<witness-id>.json         per manuscript; description CONTENT only if the description's
                                     licence is free (licence gate, lib_hsp.FREE_LICENCE_PREFIXES),
                                     otherwise only citation + link
  json/hsp-local/<witness-id>.json   (--local) same WITHOUT the gate, plus json/hsp-local/index.json.
                                     gitignored; the frontend prefers it when served locally.

Usage: python scripts/export_manuscripts.py [--local]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib_hsp as hsp  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
ATTRIBUTION = {"text": "Daten: Handschriftenportal", "url": "https://handschriftenportal.de/"}
CONTENT_KEYS = ("headline", "head", "summary", "items", "history", "index_terms", "bibliography", "fulltext")


def description_doc(desc_id: str, manifest: dict, gate: bool) -> dict:
    d = hsp.parse_description(hsp.desc_path(desc_id).read_bytes())
    doc = {"id": desc_id, "citation": d["citation"], "portal_url": hsp.portal_url(desc_id),
           "licence_status": d["licence_status"], "licence_url": d["licence_url"],
           "fetched_at": (manifest.get(desc_id) or {}).get("fetched_at")}
    if not gate or (d["licence_status"] == "free" and hsp.is_free_licence(d["licence_url"])):
        doc["content"] = {k: d[k] for k in CONTENT_KEYS}
        doc["former_shelfmarks"] = d["msidentifier"].get("former_shelfmarks", [])
    else:
        doc["content"] = None  # cite-and-link only
    return doc


def witness_doc(wid: str, e: dict, letters: list[dict], gate: bool, manifest: dict | None = None) -> dict:
    manifest = manifest if manifest is not None else hsp.load_manifest()
    hid = e.get("hsp_id")
    doc = {
        "id": wid, "label": e.get("label"), "settlement": e.get("settlement"), "repository": e.get("repository"),
        "shelfmark": e.get("signature"), "hsp_id": hid, "provenance": e.get("provenance"),
        "portal_url": hsp.portal_url(hid) if hid else None,
        "letters": letters, "hsp": None, "descriptions": [], "attribution": ATTRIBUTION,
        "mode": "public" if gate else "local-full",
    }
    kod = hsp.load_kod_local(hid) if hid else None
    if kod:
        kmeta = manifest.get(hid) or {}
        doc["hsp"] = {
            "core": {k: kod.get(k) for k in ("settlement-display", "repository-display", "idno-display",
                                             "title-display", "orig-date-lang-display", "orig-place-display",
                                             "leaves-count-display", "material-display", "dimensions-display",
                                             "object-type-display")},
            "fetched_at": kmeta.get("fetched_at"), "licence_status": kmeta.get("licence_status"),
            "licence_url": kmeta.get("licence_url"),
        }
        doc["descriptions"] = [description_doc(d, manifest, gate) for d in hsp.local_descriptions(hid)]
    return doc


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true", help="write the ungated json/hsp-local/ version")
    args = ap.parse_args()
    entities = json.loads((REPO / "build" / "entities.json").read_text(encoding="utf-8"))
    persons = entities["persons"]
    per_ms: dict[str, list[dict]] = {}
    for line in (REPO / "build" / "letters.jsonl").read_text(encoding="utf-8").splitlines():
        l = json.loads(line)
        for wid in (l.get("mentions") or {}).get("witnesses", []):
            per_ms.setdefault(wid, []).append({
                "id": l["id"], "date": l["sent"]["date"],
                "sender": (persons.get(l["sent"]["person"]) or {}).get("label") if l["sent"]["person"] else None,
                "recipient": (persons.get(l["received"]["person"]) or {}).get("label") if l["received"]["person"] else None})
    manifest = hsp.load_manifest()
    out_dir = REPO / "json" / ("hsp-local" if args.local else "hsp")
    index = []
    for wid, e in entities["witnesses"].items():
        letters = sorted(per_ms.get(wid, []), key=lambda x: (x["date"] or "", x["id"]))
        doc = witness_doc(wid, e, letters, gate=not args.local, manifest=manifest)
        write_json(out_dir / f"{wid}.json", doc)
        kod_core = (doc["hsp"] or {}).get("core") or {}
        free_core = (doc["hsp"] or {}).get("licence_status") == "free"
        index.append({
            "id": wid, "label": e.get("label"), "shelfmark": e.get("signature"), "settlement": e.get("settlement"),
            "repository": e.get("repository"), "hsp_id": e.get("hsp_id"), "portal_url": doc["portal_url"],
            "n_letters": len(letters), "letter_ids": [l["id"] for l in letters],
            "search": " ".join(x for x in [kod_core.get("title-display"), kod_core.get("orig-place-display")] if x)
            if free_core else "",
        })
    if args.local:
        write_json(out_dir / "index.json", {"mode": "local-full", "count": len(index),
                                            "note": "Contains non-free HSP descriptions - never publish."})
        print(f"wrote {len(index)} manuscripts -> {out_dir} (local, ungated)")
    else:
        write_json(REPO / "json" / "explore" / "manuscripts.json", index)
        print(f"wrote {len(index)} manuscripts -> {out_dir} + json/explore/manuscripts.json")


if __name__ == "__main__":
    main()
