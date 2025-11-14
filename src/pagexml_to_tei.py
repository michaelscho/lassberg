# pagexml_to_tei.py
"""
Build a TEI-like line stream from exported PAGE-XML files.

- Reads PAGE-XML for a given letter from:  <config.export_folder>/lassberg-letter-<NNNN>/
- Writes nothing by default; returns strings.
- Produces:
    * tei_lines: string with <pb/> and <lb/> markers and line text
    * plain_text: tag-stripped text (for NER, normalization, etc.)
- Matches your legacy semantics:
    * <pb n="i" corresp="../pagexml/lassberg-letter-<NNNN>/lassberg-letter-<NNNN>-i.xml"/>
    * <lb xml:id="lassberg-letter-<NNNN>-i-j" n="j" corresp="<TextLine/@id>"/> LineText
    * If a line contains '¬', the *next* <lb/> carries break="no" and the '¬' is removed.

You can override the `corresp_base` (defaults to '../pagexml') when your TEI
wrapper lives in a different relative location.

Usage:
    from pagexml_to_tei import build_line_stream

    res = build_line_stream("1151")  # 4-digit id as string
    print(res.tei_lines[:500])
    print(res.plain_text[:500])
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import re

import lxml.etree as LET
import config


# --------- helpers ---------

_ID_RE = re.compile(r"lassberg[-_ ]letter[-_ ](\d+)", re.IGNORECASE)

def derive_letter_id_from_title(title: Optional[str], fallback_numeric: int | str) -> str:
    """
    Extract the numeric letter id from titles like 'lassberg-letter-1151'
    or 'done_lassberg-letter-42'. Return zero-padded 4-digit string.
    """
    t = (title or "").lower().replace("done_", "")
    m = _ID_RE.search(t)
    base = m.group(1) if m else str(fallback_numeric)
    return str(int(base)).zfill(4)


@dataclass
class BuildResult:
    letter_id: str
    tei_lines: str
    plain_text: str
    page_count: int
    line_count: int
    per_page_lines: List[int]
    source_dir: Path
    page_files: List[Path]


# --------- core builder ---------

def build_line_stream(
    letter_id: str,
    *,
    export_root: Optional[str | Path] = None,
    corresp_base: str = "../pagexml",
) -> BuildResult:
    """
    Build TEI line stream and plain text for one letter.

    Parameters
    ----------
    letter_id : str
        4-digit Laßberg letter id ('1151', '0042', ...)
    export_root : str | Path | None
        Root folder containing the exported PAGE-XML. If None, uses config.export_folder.
        Expected structure: <export_root>/lassberg-letter-<NNNN>/*.xml
    corresp_base : str
        Base path used inside pb/@corresp (default: '../pagexml'), so final corresp is:
        '{corresp_base}/lassberg-letter-<NNNN>/lassberg-letter-<NNNN>-<i>.xml'

    Returns
    -------
    BuildResult
    """
    root = Path(export_root) if export_root is not None else Path(config.export_folder)
    src_dir = (root / f"lassberg-letter-{letter_id}").resolve()

    if not src_dir.exists():
        raise FileNotFoundError(f"PAGE-XML folder not found: {src_dir}")

    # Collect PAGE-XML files, sorted by page index if possible, otherwise by name
    pages = sorted(src_dir.glob("*.xml"), key=_page_sort_key(letter_id))
    if not pages:
        raise FileNotFoundError(f"No PAGE-XML files found in {src_dir}")

    tei_parts: List[str] = []
    plain_parts: List[str] = []

    per_page_counts: List[int] = []
    total_lines = 0
    lb_break_next = False  # carry-over for break="no" due to trailing '¬'

    for i, page_path in enumerate(pages, start=1):
        # Emit <pb/>
        corresp = f"{corresp_base}/lassberg-letter-{letter_id}/lassberg-letter-{letter_id}-{i}.xml"
        tei_parts.append(f'<pb n="{i}" corresp="{corresp}"/>')

        # Parse PAGE-XML and collect lines in reading order
        page_line_count = 0
        lines = _extract_lines_from_pagexml(page_path)

        # Number lines continuously per *page* (legacy: resets each page)
        for j, (line_id_attr, text) in enumerate(lines, start=1):
            # Hyphen marker handling: if this line *contains* '¬', remove it and mark next lb with break="no"
            if "¬" in text:
                text = text.replace("¬", "")
                next_break_no = True
            else:
                next_break_no = False

            # Build <lb/>
            lb_attrs = [f'xml:id="lassberg-letter-{letter_id}-{i}-{j}"', f'n="{j}"']
            if line_id_attr:
                lb_attrs.append(f'corresp="{line_id_attr}"')
            if lb_break_next:
                lb_attrs.insert(0, 'break="no"')  # place first for readability

            tei_parts.append(f"<lb {' '.join(lb_attrs)}/>{text}")

            # Plain text mirror (no tags)
            plain_parts.append(text)

            page_line_count += 1
            total_lines += 1

            # Set carry-over for next lb
            lb_break_next = next_break_no

        per_page_counts.append(page_line_count)

    tei_lines = "\n".join(tei_parts)
    plain_text = " ".join(plain_parts)  # legacy pipeline later collapsed newlines anyway

    return BuildResult(
        letter_id=letter_id,
        tei_lines=tei_lines,
        plain_text=plain_text,
        page_count=len(pages),
        line_count=total_lines,
        per_page_lines=per_page_counts,
        source_dir=src_dir,
        page_files=pages,
    )


# --------- internals ---------

def _page_sort_key(letter_id: str):
    """
    Prefer numeric sort by suffix '-<i>.xml' (where i is 1..N). Fallback to name.
    """
    rex = re.compile(rf"lassberg[-_ ]letter[-_ ]{re.escape(letter_id)}-(\d+)\.xml$", re.IGNORECASE)

    def key(p: Path):
        m = rex.search(p.name)
        return (0, int(m.group(1))) if m else (1, p.name.lower())
    return key


def _extract_lines_from_pagexml(page_path: Path) -> List[tuple[str | None, str]]:
    """
    Return a list of (TextLine@id, text) from a PAGE-XML file.

    Strategy:
      - find all TextRegion, then TextLine within, in document order
      - take the first Unicode text under each TextLine
      - robust to missing text (skips empty lines)
    """
    tree = LET.parse(str(page_path))
    root = tree.getroot()

    lines: List[tuple[str | None, str]] = []

    # Gather in source order
    for region in root.findall(".//{*}TextRegion"):
        for tl in region.findall(".//{*}TextLine"):
            uid = tl.get("id")
            uni = tl.find(".//{*}Unicode")
            if uni is None or uni.text is None:
                continue
            text = uni.text.replace("\n", "").strip()
            if not text:
                continue
            lines.append((uid, text))

    return lines
