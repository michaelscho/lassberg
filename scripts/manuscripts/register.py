"""Read/append helpers for data/register/lassberg-manuscripts.xml (formatting-preserving).

Entries are appended as text before `</listBibl>` so the hand-formatted register file is not
re-serialised.
"""
from __future__ import annotations

import re
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[2]
REGISTER = REPO / "data" / "register" / "lassberg-manuscripts.xml"
PREFIX = "lassberg-witness-"
KEY_PREFIX = "../register/lassberg-manuscripts.xml#"
I = "                "  # entry indent (16 spaces, as in the other registers)


def next_id(text: str) -> str:
    nums = [int(n) for n in re.findall(rf'xml:id="{PREFIX}(\d+)"', text)]
    return f"{PREFIX}{(max(nums) + 1 if nums else 1):04d}"


def _el(indent: int, tag: str, value: str | None, attrs: str = "") -> str:
    return f'{I}{" " * indent}<{tag}{attrs}>{escape(value)}</{tag}>\n'


def render_msdesc(xml_id: str, e: dict) -> str:
    """e keys: settlement, repository, shelfmark, hsp_id, msname, gnd, handschriftencensus,
    former (list[str]), work_key + work_title, provenance, note, needs_review."""
    ana = ' ana="needs-review"' if e.get("needs_review") else ""
    out = [f'{I}<msDesc xml:id="{xml_id}"{ana}>\n', f"{I}    <msIdentifier>\n"]
    if e.get("settlement"):
        out.append(_el(8, "settlement", e["settlement"]))
    if e.get("repository"):
        out.append(_el(8, "repository", e["repository"]))
    if e.get("shelfmark"):
        out.append(_el(8, "idno", e["shelfmark"], ' type="shelfmark"'))
    if e.get("hsp_id"):
        out.append(f'{I}        <altIdentifier type="hsp"><idno>{escape(e["hsp_id"])}</idno></altIdentifier>\n')
    for kind in ("gnd", "handschriftencensus"):
        if e.get(kind):
            out.append(f'{I}        <altIdentifier type="{kind}"><idno>{escape(e[kind])}</idno></altIdentifier>\n')
    for f in e.get("former") or []:
        out.append(f'{I}        <altIdentifier type="former"><idno>{escape(f)}</idno></altIdentifier>\n')
    if e.get("msname"):
        out.append(_el(8, "msName", e["msname"]))
    out.append(f"{I}    </msIdentifier>\n")
    if e.get("work_key"):
        out.append(f'{I}    <msContents><msItem><title key="{escape(e["work_key"])}">{escape(e.get("work_title") or "")}</title></msItem></msContents>\n')
    if e.get("provenance"):
        out.append(f"{I}    <history><provenance>{escape(e['provenance'])}</provenance></history>\n")
    if e.get("note"):
        out.append(_el(4, "note", e["note"]))
    out.append(f"{I}</msDesc>\n")
    return "".join(out)


def add_msdesc(entry: dict, path: Path = REGISTER) -> str:
    """Append one msDesc, return its xml:id."""
    return add_msdescs([entry], path)[0]


def add_msdescs(entries: list[dict], path: Path = REGISTER) -> list[str]:
    text = path.read_text(encoding="utf-8")
    marker = "            </listBibl>"
    idx = text.rindex(marker)
    ids, block = [], ""
    for e in entries:
        nums = [int(n) for n in re.findall(rf'xml:id="{PREFIX}(\d+)"', text + block)]
        xml_id = f"{PREFIX}{(max(nums) + 1 if nums else 1):04d}"
        block += render_msdesc(xml_id, e)
        ids.append(xml_id)
    path.write_text(text[:idx] + block + text[idx:], encoding="utf-8")
    return ids


def load_entries(path: Path = REGISTER) -> dict:
    """Parsed entries via the pipeline parser: {id: {label, settlement, repository, signature,
    hsp_id, alt_ids, ...}}."""
    import sys
    sys.path.insert(0, str(REPO / "scripts"))
    from parse_tei import Warnings, parse_manuscripts
    return parse_manuscripts(path, Warnings())


def find_by_hsp_or_signature(entries: dict, hsp_id: str | None, signature: str | None,
                             repository: str | None = None) -> str | None:
    for eid, e in entries.items():
        if hsp_id and e.get("hsp_id") == hsp_id:
            return eid
    for eid, e in entries.items():
        if signature and e.get("signature") == signature and (
                not repository or not e.get("repository") or e["repository"] == repository):
            return eid
    return None


def update_msdesc(xml_id: str, msname: str | None = None, note: str | None = None,
                  work_key: str | None = None, work_title: str | None = None,
                  path: Path = REGISTER) -> None:
    """Add msName / msContents / note to an existing msDesc (text-level, only when absent)."""
    text = path.read_text(encoding="utf-8")
    m = re.search(rf'( *)<msDesc xml:id="{re.escape(xml_id)}"[^>]*>.*?</msDesc>\n', text, re.S)
    if not m:
        raise KeyError(xml_id)
    block = m.group(0)
    new = block
    if msname and "<msName>" not in new:
        new = new.replace("                    </msIdentifier>",
                          f"                        <msName>{escape(msname)}</msName>\n                    </msIdentifier>", 1)
    if work_key and "<msContents>" not in new:
        line = (f'                    <msContents><msItem><title key="{escape(work_key)}">'
                f'{escape(work_title or "")}</title></msItem></msContents>\n')
        new = new.replace("                    <history>", line + "                    <history>", 1) \
            if "<history>" in new else new.replace("                </msDesc>", line + "                </msDesc>", 1)
    if note and "<note>" not in new:
        new = new.replace("                </msDesc>", f"                    <note>{escape(note)}</note>\n                </msDesc>", 1)
    path.write_text(text.replace(block, new, 1), encoding="utf-8")
