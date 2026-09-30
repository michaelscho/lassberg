"""Apply resolved scan proposals to the letter TEI files, formatting-preserving (string edits).

The LLM proposes, this code writes (Plan Phase 4.5). Only the transcription div
(type original|print) is touched. Machine-set/changed <rs> get resp="#manuscript-scan"; no
<change> is written to revisionDesc (status model).

Usage: python scripts/manuscripts/apply_proposals.py [--dry-run] (<letter-id> ... | --all)
Log: build/manuscripts/applied.jsonl, report: build/manuscripts/report.md
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).parent))
import register as reg  # noqa: E402
from tei_text import find_all, load_letter, norm_quote  # noqa: E402

OUT = reg.REPO / "build" / "manuscripts"
PROPOSALS = OUT / "proposals"
LOG = OUT / "applied.jsonl"
KEY_PREFIX = "../register/lassberg-manuscripts.xml#"
RESP = "#manuscript-scan"


def set_attrs(raw: str, updates: dict) -> str:
    for name, value in updates.items():
        pat = re.compile(rf'(\s{re.escape(name)}\s*=\s*)"[^"]*"')
        if pat.search(raw):
            raw = pat.sub(lambda m: f'{m.group(1)}"{escape(value)}"', raw, count=1)
        else:
            raw = re.sub(r"\s*(/?>)$", lambda m: f' {name}="{escape(value)}"{m.group(1)}', raw, count=1)
    return raw


def spans_overlap(a, b):
    return a[0] < b[1] and b[0] < a[1]


def apply_letter(prop: dict, entries: dict, dry: bool) -> tuple[list, list]:
    lid = prop["letter_id"]
    path, src, toks, rng, lin = load_letter(lid)
    applied, skipped = [], []
    if not lin:
        return applied, [{"letter": lid, "why": "no transcription div"}]
    edits: list[tuple[int, int, str]] = []   # (abs_start, abs_end, replacement)
    used_spans = []
    mention_targets: dict[str, str] = {}      # wid -> label

    for m in prop.get("mentions", []):
        res = m.get("resolved") or {}
        wid = res.get("witness_id")
        if wid is None:
            skipped.append({"letter": lid, "quote": m["quote"], "why": f"unresolved ({res.get('how')})"})
            continue
        key = f"{KEY_PREFIX}{wid}" if wid else ""
        quote, occ = norm_quote(m["quote"]), int(m.get("occurrence") or 1)
        action = m.get("action")
        rec = {"letter": lid, "action": action, "quote": quote, "witness_id": wid or None,
               "confidence": m.get("confidence"), "how": res.get("how")}

        target = None
        matches = [r for r in lin.rs if r["text"] == quote]
        if action == "retype" and len(matches) >= occ:
            target = matches[occ - 1]
        elif action == "wrap":
            starts = find_all(lin.text, quote)
            if len(starts) < occ:
                skipped.append({**rec, "why": "quote not found"})
                continue
            a = starts[occ - 1]
            b = a + len(quote)
            same = [r for r in lin.rs if (r["lin_start"], r["lin_end"]) == (a, b)]
            if same:
                target = same[0]
            elif any(spans_overlap((a, b), (r["lin_start"], r["lin_end"])) for r in lin.rs):
                skipped.append({**rec, "why": "overlaps existing rs"})
                continue
        else:
            skipped.append({**rec, "why": "quote/rs not found"})
            continue

        if target is not None:
            t = toks[target["start_tok"]]
            cur = target["attrs"]
            if cur.get("type") == "witness" and cur.get("key") == key and cur.get("resp"):
                skipped.append({**rec, "why": "already applied"})
                if wid:
                    mention_targets.setdefault(wid, res)  # still ensure the note entry
                continue
            new_raw = set_attrs(t.raw, {"type": "witness", "key": key, "resp": RESP})
            edits.append((t.pos, t.pos + len(t.raw), new_raw))
            rec["mode"] = "retype"
        else:
            si, s_raw0, _ = lin.pos[a]
            ei, _, e_raw1 = lin.pos[b - 1]
            # balanced-tag check between start and end token
            depth, ok = 0, True
            for i in range(si + 1, ei):
                tk = toks[i]
                if tk.name == "rs":
                    ok = False
                    break
                if tk.kind == "start":
                    depth += 1
                elif tk.kind == "end":
                    depth -= 1
                    if depth < 0:
                        ok = False
                        break
            if not ok or depth != 0:
                skipped.append({**rec, "why": "partial overlap with non-empty element"})
                continue
            abs_s = toks[si].pos + s_raw0
            abs_e = toks[ei].pos + e_raw1
            if any(spans_overlap((abs_s, abs_e), u) for u in used_spans):
                skipped.append({**rec, "why": "overlaps another edit"})
                continue
            used_spans.append((abs_s, abs_e))
            open_tag = f'<rs type="witness" key="{escape(key)}" resp="{RESP}">'
            edits.append((abs_s, abs_s, open_tag))
            edits.append((abs_e, abs_e, "</rs>"))
            rec["mode"] = "wrap"
        applied.append(rec)
        if wid:
            mention_targets.setdefault(wid, res)

    # note type="mentioned"
    note_edit = None
    if mention_targets:
        depth = None
        for i, t in enumerate(toks):
            if t.kind == "start" and t.name == "note" and t.attrs.get("type") == "mentioned":
                depth = i
            elif depth is not None and t.kind == "end" and t.name == "note":
                note_block = "".join(x.raw for x in toks[depth:i])
                add = ""
                for wid in mention_targets:
                    if f"{KEY_PREFIX}{wid}" in note_block:
                        continue
                    label = entries[wid]["label"] if wid in entries else wid
                    add += (f'<ref type="cmif:mentionsBibl" target="{KEY_PREFIX}{wid}"><rs>{escape(label)}</rs></ref> ')
                if add:
                    lead = "" if toks[i - 1].kind == "text" and toks[i - 1].raw.endswith((" ", "\n")) else " "
                    note_edit = (t.pos, t.pos, lead + add)
                break
    if note_edit:
        edits.append(note_edit)

    if edits and not dry:
        out = src
        for s, e, rep in sorted(edits, key=lambda x: (x[0], x[1]), reverse=True):
            out = out[:s] + rep + out[e:]
        path.write_text(out, encoding="utf-8")
    return applied, skipped


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("letters", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    files = sorted(PROPOSALS.glob("*.json"))
    if not args.all:
        want = {l if l.startswith("lassberg-letter-") else f"lassberg-letter-{l}" for l in args.letters}
        files = [f for f in files if f.stem in want]
    entries = reg.load_entries()
    all_applied, all_skipped = [], []
    for f in files:
        prop = json.loads(f.read_text(encoding="utf-8"))
        a, s = apply_letter(prop, entries, args.dry_run)
        all_applied += a
        all_skipped += s
    if not args.dry_run:
        OUT.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as fh:
            for rec in all_applied:
                fh.write(json.dumps({"ts": datetime.now(timezone.utc).isoformat(timespec="seconds"), **rec},
                                    ensure_ascii=False) + "\n")
        rep = ["# Bericht Handschriften-Scan", "",
               f"- angewandt: {len(all_applied)} (retype {sum(1 for r in all_applied if r.get('mode') == 'retype')}, "
               f"wrap {sum(1 for r in all_applied if r.get('mode') == 'wrap')})",
               f"- übersprungen: {len(all_skipped)}", "", "## Übersprungen", ""]
        rep += [f"- {r['letter']}: „{r.get('quote', '')}“ – {r['why']}" for r in all_skipped]
        rep += ["", "## Konfidenz < 0.7", ""]
        rep += [f"- {r['letter']}: „{r['quote']}“ → {r['witness_id']} ({r['confidence']})"
                for r in all_applied if (r.get("confidence") or 1) < 0.7]
        rep[0] = f"## Lauf {datetime.now(timezone.utc).isoformat(timespec='seconds')} ({len(files)} Briefe)"
        with (OUT / "report.md").open("a", encoding="utf-8") as fh:
            fh.write("\n".join(rep) + "\n\n")
    print(f"applied {len(all_applied)}, skipped {len(all_skipped)}{' (dry run)' if args.dry_run else ''}")
    for r in all_skipped:
        print("  skip:", r["letter"], r.get("quote", ""), "-", r["why"])


if __name__ == "__main__":
    main()
