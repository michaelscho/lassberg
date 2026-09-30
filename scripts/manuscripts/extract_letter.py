"""Print the transcription text of a letter with existing <rs> markup, for the manuscript scan.

Usage: python scripts/manuscripts/extract_letter.py <letter-id|number> [...]
Output: header line + text; existing rs shown as [[type|register-id: text]].
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from tei_text import annotated_text, load_letter  # noqa: E402

for lid in sys.argv[1:]:
    p, src, toks, rng, lin = load_letter(lid)
    print(f"=== {p.stem}")
    if not lin:
        print("(no transcription div)")
        continue
    print(annotated_text(lin, toks))
    print()
