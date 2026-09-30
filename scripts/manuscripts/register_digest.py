"""Write build/manuscripts/register_digest.tsv (id, msName, settlement, shelfmark, former) - the
context list handed to the scan subagents. Usage: python scripts/manuscripts/register_digest.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import register as reg  # noqa: E402

rows = ["id\tmsName\tsettlement\tshelfmark\tformer"]
for wid, e in reg.load_entries().items():
    name = e["label"] if e["label"] != ", ".join(x for x in (e.get("settlement"), e.get("repository"), e.get("signature")) if x) else ""
    rows.append("\t".join([wid, name, e.get("settlement") or "", e.get("signature") or "",
                           "; ".join(e.get("alt_ids", {}).get("former", []))]))
out = reg.REPO / "build" / "manuscripts" / "register_digest.tsv"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(rows) + "\n", encoding="utf-8")
print(f"{len(rows) - 1} entries -> {out}")
