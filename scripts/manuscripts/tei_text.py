"""Formatting-preserving text access to the transcription <div> of a letter TEI file.

Letters are hand-formatted in Oxygen (tags wrapped over several lines), so re-serialising with
lxml would rewrite whole files. Instead the file is tokenised into tags and text, a "linear
text" of the transcription div (whitespace collapsed, `<lb break="no"/>` joined) is built with a
char -> raw-position map, and edits are applied as string insertions/replacements.
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
LETTERS = REPO / "data" / "letters"

TOKEN_RE = re.compile(r"(<!--.*?-->|<\?.*?\?>|<!\[CDATA\[.*?\]\]>|<[^>]*>)|([^<]+)", re.S)
NAME_RE = re.compile(r"^</?([\w:.-]+)")
ATTR_RE = re.compile(r'([\w:.-]+)\s*=\s*"([^"]*)"')
CHAR_RE = re.compile(r"&[#\w]+;|.", re.S)
WS = " \t\r\n"


@dataclass
class Tok:
    kind: str          # start | end | empty | text | other
    raw: str
    pos: int           # absolute offset in file
    name: str = ""
    attrs: dict = field(default_factory=dict)


def tokenize(src: str) -> list[Tok]:
    toks = []
    for m in TOKEN_RE.finditer(src):
        raw = m.group(0)
        if m.group(2) is not None:
            toks.append(Tok("text", raw, m.start()))
            continue
        if raw.startswith(("<!--", "<?", "<![CDATA[")) or raw.startswith("<!"):
            toks.append(Tok("other", raw, m.start()))
            continue
        nm = NAME_RE.match(raw)
        name = nm.group(1) if nm else ""
        if raw.startswith("</"):
            kind = "end"
        elif raw.endswith("/>"):
            kind = "empty"
        else:
            kind = "start"
        toks.append(Tok(kind, raw, m.start(), name, dict(ATTR_RE.findall(raw)) if kind != "end" else {}))
    return toks


def find_transcription(toks: list[Tok]) -> tuple[int, int] | None:
    """Token index range (start_tok, end_tok) of the first div[@type=original|print]."""
    depth = None
    for i, t in enumerate(toks):
        if depth is None:
            if t.kind == "start" and t.name == "div" and t.attrs.get("type") in ("original", "print"):
                depth, start = 1, i
        else:
            if t.kind == "start" and t.name == "div":
                depth += 1
            elif t.kind == "end" and t.name == "div":
                depth -= 1
                if depth == 0:
                    return start, i
    return None


@dataclass
class Linear:
    text: str
    # per linear char: (tok_idx, raw_start, raw_end) within token, or None for virtual chars
    pos: list
    rs: list           # existing <rs>: dicts(start_tok, end_tok, attrs, lin_start, lin_end, text)


def linearize(toks: list[Tok], rng: tuple[int, int]) -> Linear:
    chars: list[str] = []
    pos: list = []
    rs_open: list = []
    rs_list: list = []
    skip_ws = False

    def add_ws(p):
        if chars and chars[-1] != " ":
            chars.append(" ")
            pos.append(p)

    for i in range(rng[0] + 1, rng[1]):
        t = toks[i]
        if t.kind == "text":
            for m in CHAR_RE.finditer(t.raw):
                ch = html.unescape(m.group(0))
                if ch in WS:
                    if skip_ws:
                        continue
                    add_ws((i, m.start(), m.end()))
                else:
                    skip_ws = False
                    chars.append(ch)
                    pos.append((i, m.start(), m.end()))
        elif t.kind in ("empty", "start", "end") and t.name in ("lb", "pb"):
            if t.name == "lb" and t.attrs.get("break") == "no":
                while chars and chars[-1] == " ":
                    chars.pop()
                    pos.pop()
                skip_ws = True
            else:
                add_ws(None)
        elif t.name == "rs":
            if t.kind == "start":
                rs_open.append((i, t.attrs, len(chars)))
            elif t.kind == "end" and rs_open:
                si, attrs, ls = rs_open.pop()
                rs_list.append({"start_tok": si, "end_tok": i, "attrs": attrs, "lin_start": ls,
                                "lin_end": len(chars), "text": "".join(chars[ls:]).strip()})
    return Linear("".join(chars), pos, rs_list)


def norm_quote(q: str) -> str:
    return re.sub(r"\s+", " ", q).strip()


def find_all(text: str, quote: str) -> list[int]:
    out, i = [], text.find(quote)
    while i >= 0:
        out.append(i)
        i = text.find(quote, i + 1)
    return out


def letter_path(letter_id: str) -> Path:
    lid = letter_id if letter_id.startswith("lassberg-letter-") else f"lassberg-letter-{letter_id}"
    return LETTERS / f"{lid}.xml"


def load_letter(letter_id: str):
    p = letter_path(letter_id)
    src = p.read_text(encoding="utf-8")
    toks = tokenize(src)
    rng = find_transcription(toks)
    lin = linearize(toks, rng) if rng else None
    return p, src, toks, rng, lin


def annotated_text(lin: Linear, toks: list[Tok]) -> str:
    """Linear text with existing <rs> shown as [[type|key: text]] - for LLM input."""
    marks = []
    for r in lin.rs:
        a = r["attrs"]
        key = a.get("key", "")
        key = key.split("#")[-1] if key else ""
        marks.append((r["lin_start"], f"[[{a.get('type','?')}|{key}: "))
        marks.append((r["lin_end"], "]]"))
    marks.sort(key=lambda x: (x[0], 0 if x[1] == "]]" else 1))
    out, last = [], 0
    for p, s in marks:
        out.append(lin.text[last:p])
        out.append(s)
        last = p
    out.append(lin.text[last:])
    return "".join(out)
