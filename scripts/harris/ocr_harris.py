#!/usr/bin/env python3
"""OCR the letter inventory of Harris 1991 (Harris_Freiherr_von_Lassberg.pdf in the repo root, an
image-only PDF of double pages) into data/harris/ocr/<page>-{L,R}.txt (gitignored).
Needs pdftoppm (poppler), tesseract with the "deu" model and Pillow (system python3; not in
.venv-infra). Pages already done are skipped.

Usage:  python scripts/harris/ocr_harris.py [--first 71 --last 112]
"""
from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
PDF = REPO / "Harris_Freiherr_von_Lassberg.pdf"
OUT = REPO / "data" / "harris" / "ocr"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--first", type=int, default=71)
    ap.add_argument("--last", type=int, default=112)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for n in range(args.first, args.last + 1):
            if (OUT / f"{n:03d}-R.txt").exists():
                continue
            subprocess.run(["pdftoppm", "-f", str(n), "-l", str(n), "-r", "300", "-gray", "-png",
                            str(PDF), f"{tmp}/p"], check=True)
            img = next(Path(tmp).glob("p-*.png"))
            im = Image.open(img)
            w, h = im.size
            for side, box in (("L", (0, 0, w // 2, h)), ("R", (w // 2, 0, w, h))):
                half = Path(tmp) / f"{side}.png"
                im.crop(box).save(half)
                subprocess.run(["tesseract", str(half), str(OUT / f"{n:03d}-{side}"), "-l", "deu",
                                "--psm", "6"], check=True, capture_output=True)
            img.unlink()
            print(f"  page {n}", flush=True)


if __name__ == "__main__":
    main()
