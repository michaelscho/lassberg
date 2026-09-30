"""Mirror HSP Kulturobjekte + all their descriptions for the registered manuscripts into data/hsp/.

data/hsp/ is gitignored (licences, esp. restricted/InC catalogue descriptions).

Usage:
    python scripts/manuscripts/mirror_hsp.py                # all msDesc with an HSP-ID, incremental
    python scripts/manuscripts/mirror_hsp.py --refresh      # re-download everything
    python scripts/manuscripts/mirror_hsp.py --add HSP-...  # one Kulturobjekt (e.g. a new manuscript)
    python scripts/manuscripts/mirror_hsp.py --limit 5      # first N only (testing)
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).parent))
import lib_hsp as hsp  # noqa: E402
import register as reg  # noqa: E402


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


TOUCHED: set[str] = set()


def save_manifest(m: dict) -> None:
    """Merge our own entries into the on-disk manifest (safe with concurrent --add runs)."""
    disk = hsp.load_manifest()
    disk.update({k: m[k] for k in TOUCHED if k in m})
    (hsp.HSP_DIR / "manifest.json").write_text(json.dumps(disk, ensure_ascii=False, indent=1, sort_keys=True),
                                               encoding="utf-8")


def mirror_one(hsp_id: str, witness_id: str | None, manifest: dict, refresh: bool, failed: list) -> None:
    before = set(manifest)
    (hsp.HSP_DIR / "kod").mkdir(parents=True, exist_ok=True)
    (hsp.HSP_DIR / "desc").mkdir(parents=True, exist_ok=True)
    kod_json, kod_xml = hsp.kod_paths(hsp_id)
    try:
        if refresh or not kod_json.exists():
            data = hsp.get_kod(hsp_id)
            kod_json.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            manifest[hsp_id + ":json"] = {"witness_id": witness_id, "kind": "kod", "fetched_at": now(),
                                          "sha256": hsp.sha256(kod_json.read_bytes()),
                                          "source_url": f"{hsp.API}/kods/{hsp_id}",
                                          "licence_url": None, "licence_status": "unknown"}
        if refresh or not kod_xml.exists():
            xml = hsp.get_tei(hsp_id)
            kod_xml.write_bytes(xml)
            lic = hsp.licence_of(xml)
            manifest[hsp_id] = {"witness_id": witness_id, "kind": "kod", "fetched_at": now(),
                                "sha256": hsp.sha256(xml), "source_url": f"{hsp.API}/tei/{hsp_id}",
                                "licence_url": lic["url"], "licence_status": lic["status"]}
        for did in hsp.description_ids(kod_xml.read_bytes()):
            p = hsp.desc_path(did)
            if p.exists() and not refresh and did in manifest:
                continue
            try:
                xml = hsp.get_tei(did)
            except hsp.HspError as exc:
                failed.append((did, str(exc)))
                continue
            p.write_bytes(xml)
            lic = hsp.licence_of(xml)
            manifest[did] = {"witness_id": witness_id, "kind": "desc", "kod_id": hsp_id,
                             "fetched_at": now(), "sha256": hsp.sha256(xml),
                             "source_url": f"{hsp.API}/tei/{did}",
                             "licence_url": lic["url"], "licence_status": lic["status"]}
    except hsp.HspError as exc:
        failed.append((hsp_id, str(exc)))
    finally:
        TOUCHED.update(k for k in manifest if k not in before or manifest[k].get("fetched_at", "") >= START)


START = now()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--add", metavar="HSP-ID")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    manifest = hsp.load_manifest()
    failed: list = []
    if args.add:
        entries = reg.load_entries()
        wid = next((i for i, e in entries.items() if e.get("hsp_id") == args.add), None)
        targets = [(args.add, wid)]
    else:
        targets = [(e["hsp_id"], i) for i, e in reg.load_entries().items() if e.get("hsp_id")]
        if args.limit:
            targets = targets[:args.limit]
    hsp.HSP_DIR.mkdir(parents=True, exist_ok=True)
    for n, (hid, wid) in enumerate(targets, 1):
        mirror_one(hid, wid, manifest, args.refresh, failed)
        if n % 10 == 0 or n == len(targets):
            save_manifest(manifest)
            print(f"[{n}/{len(targets)}] mirrored", flush=True)
    save_manifest(manifest)
    manifest = hsp.load_manifest()
    kinds = Counter((v["kind"], v["licence_status"]) for k, v in manifest.items() if not k.endswith(":json"))
    print("Manifest:", dict(kinds))
    print(f"Failed: {len(failed)}")
    for fid, msg in failed:
        print("  ", fid, msg)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
