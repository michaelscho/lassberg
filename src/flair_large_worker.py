# flair_large_worker.py
"""
Minimal helper to run Flair-large (flair/ner-german-large) in a separate venv.

This script:
- loads SequenceTagger("flair/ner-german-large"),
- runs NER on --text-file,
- writes entities to --out-json in the same schema as the main script.

Create a dedicated env for it (example):
    python -m venv flairenv
    flairenv\Scripts\pip install "flair==0.13.1" "transformers==4.33.3" torch

Call from main script with:
    --flair-large-python "C:/path/to/flairenv/Scripts/python.exe"
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import List, Dict, Any

from flair.models import SequenceTagger
from flair.data import Sentence, Label
import os

def read_text(path: str | os.PathLike, max_chars: int | None = None) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Text file not found: {p}")
    txt = p.read_text(encoding="utf-8", errors="ignore")
    return txt[:max_chars] if (max_chars and len(txt) > max_chars) else txt

def run_flair_large(text: str, device: str = "cpu") -> List[Dict[str, Any]]:
    tagger = SequenceTagger.load("flair/ner-german-large")
    tagger.to("cpu" if device == "cpu" else "cuda")
    sent = Sentence(text)
    tagger.predict(sent)
    out: List[Dict[str, Any]] = []
    for span in sent.get_spans("ner"):
        lab: Label = span.labels[0]
        out.append({
            "text": span.text,
            "label": lab.value,
            "score": float(lab.score),
            "start": span.start_position,
            "end": span.end_position,
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--device", choices=["cpu","gpu"], default="cpu")
    ap.add_argument("--max-chars", type=int, default=None)
    args = ap.parse_args()

    text = read_text(args.text_file, max_chars=args.max_chars)
    ents = run_flair_large(text, device=args.device)
    Path(args.out_json).write_text(json.dumps(ents, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
