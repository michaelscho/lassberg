"""Resolve scan proposals to register entries (Plan Phase 4.4).

For every mention without `witness_id` (in build/manuscripts/proposals/<letter>.json):
  (a) fuzzy match against the register (rapidfuzz, threshold 92, like link_entities_llm.py)
  (b) local HSP description index (signature / content / former shelfmark)
  (c) live HSP search (only for manuscripts outside the mirrored stock) -> new msDesc + mirror
Ambiguous cases keep `resolved.how = "ambiguous"` with candidates; a reviewer (Claude/Sonnet) can
add `"decision": {"hsp_id": "HSP-…" | null, "reason": "…"}` to the mention and rerun.
Without any hit: needs-review msDesc when a name is known and confidence >= 0.8, else key="".

Usage: python scripts/manuscripts/resolve.py [--dry-run] [<letter-id> ...]   (default: all proposals)
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
import lib_hsp as hsp  # noqa: E402
import register as reg  # noqa: E402
from rapidfuzz import fuzz  # noqa: E402

OUT = reg.REPO / "build" / "manuscripts"
PROPOSALS = OUT / "proposals"
LOG = OUT / "applied.jsonl"
THRESHOLD = 92
MIN_CONFIDENCE = 0.5   # below this a proposal is too speculative to touch the TEI or the register


def variants(name: str | None) -> list[str]:
    """'Codex Manesse (Große Heidelberger Liederhandschrift)' -> full, without parenthesis, each parenthesis."""
    if not name:
        return []
    import re
    out = [name, re.sub(r"\s*\([^)]*\)", "", name).strip()] + re.findall(r"\(([^)]{4,})\)", name)
    return [v for v in dict.fromkeys(out) if v]


def name_matches(name: str | None, title: str | None) -> bool:
    return any(_name_matches(v, title) for v in variants(name))


def _name_matches(name: str | None, title: str | None) -> bool:
    """Strict-ish name match: token-sorted ratio >= 90, or the full (>= 2 words, >= 12 chars)
    proposed name contained in the title."""
    a, b = norm(name), norm(title)
    if not a or not b:
        return False
    if fuzz.token_sort_ratio(a, b) >= 90:
        return True
    return len(a.split()) >= 2 and len(a) >= 12 and a in b


def norm(s):
    return " ".join((s or "").lower().replace("‘", "").replace("’", "").split())


def log(rec: dict) -> None:
    rec = {"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **rec}
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def fuzzy_register(entries: dict, name: str | None, shelfmark: str | None) -> str | None:
    best, best_id = 0, None
    for wid, e in entries.items():
        cands = [e.get("label")] + [x for v in (e.get("alt_ids") or {}).get("former", []) for x in [v]]
        if e.get("signature"):
            cands.append(e["signature"])
        for c in cands:
            for q in [*variants(name), shelfmark]:
                if q and c:
                    s = fuzz.ratio(norm(q), norm(c))
                    if s > best:
                        best, best_id = s, wid
    return best_id if best >= THRESHOLD else None


def create_from_hsp(k: dict, letter_id: str, how: str, dry: bool) -> str:
    """New msDesc from a live HSP Kulturobjekt hit."""
    entry = {
        "settlement": k.get("settlement-display"), "repository": k.get("repository-display"),
        "shelfmark": k.get("idno-display"), "hsp_id": k["id"],
        "msname": hsp.clean_kod_title(k.get("title-display")) or None,
        "note": f"Identifiziert via HSP ({how}) beim Handschriften-Scan, zuerst in Brief {letter_id.split('-')[-1]}.",
        "needs_review": how != "exact-shelfmark",
    }
    if dry:
        return "(new)"
    wid = reg.add_msdesc(entry)
    log({"action": "register-create", "witness_id": wid, "hsp_id": k["id"], "letter": letter_id, "how": how})
    from mirror_hsp import mirror_one, save_manifest  # noqa: E402
    manifest = hsp.load_manifest()
    failed = []
    mirror_one(k["id"], wid, manifest, False, failed)
    save_manifest(manifest)
    return wid


def resolve_mention(m: dict, letter_id: str, entries: dict, dry: bool) -> dict:
    ms = m.get("manuscript") or {}
    prop = ms.get("proposed") or {}
    name, shelf = prop.get("name"), prop.get("shelfmark")
    conf = m.get("confidence") or 0

    if conf < MIN_CONFIDENCE and m.get("decision") is None:
        return {"witness_id": None, "how": "low-confidence"}

    if ms.get("witness_id"):
        if ms["witness_id"] in entries:
            return {"witness_id": ms["witness_id"], "how": "scan"}
        return {"witness_id": None, "how": "ambiguous", "note": f"unknown witness_id {ms['witness_id']}"}

    dec = m.get("decision")
    if dec is not None:
        hid = dec.get("hsp_id")
        if not hid:
            return {"witness_id": "", "how": "decision-key-empty"}
        wid = reg.find_by_hsp_or_signature(entries, hid, None)
        if wid:
            return {"witness_id": wid, "how": "decision"}
        kod = hsp.get_kod(hid)
        return {"witness_id": create_from_hsp(kod, letter_id, "decision", dry), "how": "decision-created"}

    wid = fuzzy_register(entries, name, shelf)
    if wid:
        return {"witness_id": wid, "how": "register-fuzzy"}

    queries = [q for q in (shelf, prop.get("hsp_query"), *variants(name)) if q]
    cands = []
    for q in dict.fromkeys(queries):
        for h in hsp.local_search(q, 5):
            if h.get("witness_id") and h["hsp_id"] not in [c["hsp_id"] for c in cands]:
                cands.append(h)
    strong = [c for c in cands if c["snippet"] == "signature match" or name_matches(name, c["msname"])]
    if len(strong) == 1:
        return {"witness_id": strong[0]["witness_id"], "how": "local-index"}
    if len(strong) > 1 or cands:
        return {"witness_id": None, "how": "ambiguous", "candidates": [
            {k: c[k] for k in ("hsp_id", "witness_id", "shelfmark", "msname", "snippet")} for c in (strong or cands)[:5]]}

    live_hits = []
    for q in dict.fromkeys(queries):
        try:
            live_hits += hsp.search(q, rows=10)
        except hsp.HspError as exc:
            return {"witness_id": None, "how": "ambiguous", "note": f"HSP-Fehler: {exc}"}
    live_hits = list({k["id"]: k for k in live_hits}.values())
    exact = [k for k in live_hits if shelf and norm(k.get("idno-display")) == norm(shelf)]
    named = [k for k in live_hits if name_matches(name, hsp.clean_kod_title(k.get("title-display")))]
    if len(exact) == 1:
        return {"witness_id": reg.find_by_hsp_or_signature(entries, exact[0]["id"], None)
                or create_from_hsp(exact[0], letter_id, "exact-shelfmark", dry), "how": "hsp-live"}
    if len(named) == 1 and not exact:
        wid = reg.find_by_hsp_or_signature(entries, named[0]["id"], None)
        return {"witness_id": wid or create_from_hsp(named[0], letter_id, "title-match", dry), "how": "hsp-live"}
    if len(named) > 1 or len(exact) > 1:
        return {"witness_id": None, "how": "ambiguous", "candidates": [
            {"hsp_id": k["id"], "shelfmark": k.get("idno-display"), "msname": hsp.clean_kod_title(k.get("title-display")),
             "place": f"{k.get('settlement-display')}, {k.get('repository-display')}", "date": k.get("orig-date-lang-display")}
            for k in (exact or named)[:6]]}

    if name and conf >= 0.8:
        entry = {"msname": name, "settlement": prop.get("settlement"), "repository": prop.get("repository"),
                 "shelfmark": shelf, "needs_review": True,
                 "note": f"Ohne HSP-Treffer angelegt beim Handschriften-Scan (Brief {letter_id.split('-')[-1]})."}
        if dry:
            return {"witness_id": "(new)", "how": "created-needs-review"}
        wid = reg.add_msdesc(entry)
        log({"action": "register-create", "witness_id": wid, "letter": letter_id, "how": "needs-review"})
        return {"witness_id": wid, "how": "created-needs-review"}
    return {"witness_id": "", "how": "key-empty"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(PROPOSALS.glob("*.json"))
    if args.letters:
        want = {l if l.startswith("lassberg-letter-") else f"lassberg-letter-{l}" for l in args.letters}
        files = [f for f in files if f.stem in want]
    entries = reg.load_entries()
    counts, ambiguous = {}, []
    for f in files:
        prop = json.loads(f.read_text(encoding="utf-8"))
        changed = False
        for m in prop.get("mentions", []):
            if m.get("resolved") and m["resolved"].get("how") != "ambiguous" and "decision" not in m:
                continue
            m["resolved"] = resolve_mention(m, prop["letter_id"], entries, args.dry_run)
            changed = True
            if m["resolved"]["how"] in ("created-needs-review", "hsp-live", "decision-created") and not args.dry_run:
                entries = reg.load_entries()
            counts[m["resolved"]["how"]] = counts.get(m["resolved"]["how"], 0) + 1
            if args.dry_run:
                pn = ((m.get("manuscript") or {}).get("proposed") or {}).get("name")
                print(f"{prop['letter_id'][-4:]} {m['quote'][:32]!r:36} conf={m.get('confidence')} name={pn!r} -> "
                      f"{m['resolved']['how']} {m['resolved'].get('witness_id')}")
            if m["resolved"]["how"] == "ambiguous":
                ambiguous.append({"letter": prop["letter_id"], "quote": m["quote"], **m["resolved"]})
        if changed and not args.dry_run:
            f.write_text(json.dumps(prop, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    (OUT / "decisions_needed.json").write_text(json.dumps(ambiguous, ensure_ascii=False, indent=1), encoding="utf-8")
    print("resolved:", counts, f"| ambiguous: {len(ambiguous)} (see build/manuscripts/decisions_needed.json)")


if __name__ == "__main__":
    main()
