"""
Preprocess full-page JPG+text pairs and push to HF Hub as a dataset.

Usage
-----
# Sidecar .txt files:
python vlm_training/src/ingest_pages.py \\
    --input_dir  data/pages_new \\
    --repo_id    dh-unibe/image-text_lassberg-letters \\
    --collection "Lassberg Letters" \\
    --language   de \\
    --date_range "xix"

# Manifest JSONL:
python vlm_training/src/ingest_pages.py \\
    --input_dir  data/pages_new \\
    --manifest   manifest.jsonl \\
    --repo_id    dh-unibe/image-text_lassberg-letters

Expected sidecar layout:
  data/pages_new/
    page_001.jpg  +  page_001.txt   (or page_001.gt.txt)
    page_002.jpg  +  page_002.txt
    ...
"""

import argparse
import json
import logging
from pathlib import Path

from PIL import Image, UnidentifiedImageError
from datasets import Dataset, DatasetDict, Image as HFImage, Value, Features

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Image preprocessing constants ─────────────────────────────────────────────
MAX_LONG_SIDE = 3000   # px — Qwen3-VL ceiling; larger images are downscaled
MIN_LONG_SIDE = 200    # px — reject thumbnails / corrupt crops
MIN_TEXT_LEN  = 5      # chars — reject empty / near-empty transcriptions


def preprocess_image(img: Image.Image) -> Image.Image:
    """
    Normalise a full-page scan:
      1. Convert to RGB (drop alpha / palette modes)
      2. Downscale if the long side exceeds MAX_LONG_SIDE (preserves aspect ratio)
    No aggressive preprocessing (deskew, binarise) — let the VLM handle noise.
    """
    img = img.convert("RGB")
    w, h = img.size
    long_side = max(w, h)
    if long_side > MAX_LONG_SIDE:
        scale = MAX_LONG_SIDE / long_side
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return img


def load_samples_sidecar(root: Path) -> list[dict]:
    samples = []
    for img_path in sorted(root.rglob("*.jpg")):
        txt_path = img_path.with_suffix(".txt")
        if not txt_path.exists():
            txt_path = img_path.with_suffix(".gt.txt")
        if not txt_path.exists():
            logger.warning(f"No text file for {img_path.name} — skipped")
            continue
        samples.append({"image_path": img_path, "text_path": txt_path})
    return samples


def load_samples_manifest(root: Path, manifest: str) -> list[dict]:
    samples = []
    with open(root / manifest) as f:
        for line in f:
            row = json.loads(line)
            samples.append({
                "image_path": root / row["image"],
                "text_path":  None,
                "text":       row.get("text", "").strip(),
            })
    return samples


def build_rows(
    samples: list[dict],
    collection: str,
    language: str,
    date_range: str,
) -> list[dict]:
    rows, skipped = [], 0
    for s in samples:
        # Load text
        text = s.get("text") or s["text_path"].read_text(encoding="utf-8").strip()
        if len(text) < MIN_TEXT_LEN:
            skipped += 1
            continue

        # Load & validate image
        try:
            img = Image.open(s["image_path"])
        except (UnidentifiedImageError, OSError) as e:
            logger.warning(f"Cannot open {s['image_path'].name}: {e} — skipped")
            skipped += 1
            continue

        w, h = img.size
        if max(w, h) < MIN_LONG_SIDE:
            logger.warning(f"Image too small ({w}x{h}): {s['image_path'].name} — skipped")
            skipped += 1
            continue

        img = preprocess_image(img)
        w2, h2 = img.size

        rows.append({
            "image":       img,
            "text":        text,
            "source_type": "page",          # distinguishes from line-level datasets
            "width":       w2,
            "height":      h2,
            "collection":  collection,
            "language":    language,
            "date_range":  date_range,
            "filename":    s["image_path"].name if "image_path" in s else "",
        })

    logger.info(f"Built {len(rows):,} rows  ({skipped} skipped)")
    return rows


def push_dataset(
    rows: list[dict],
    repo_id: str,
    val_fraction: float = 0.05,
    seed: int = 42,
    private: bool = False,
):
    features = Features({
        "image":       HFImage(),
        "text":        Value("string"),
        "source_type": Value("string"),
        "width":       Value("int32"),
        "height":      Value("int32"),
        "collection":  Value("string"),
        "language":    Value("string"),
        "date_range":  Value("string"),
        "filename":    Value("string"),
    })

    ds = Dataset.from_list(rows, features=features)
    split = ds.train_test_split(test_size=val_fraction, seed=seed)
    ds_dict = DatasetDict({"train": split["train"], "validation": split["test"]})

    logger.info(
        f"Pushing to {repo_id}  "
        f"(train={len(ds_dict['train']):,}  val={len(ds_dict['validation']):,})"
    )
    ds_dict.push_to_hub(
        repo_id,
        private=private,
        commit_message=f"Add {len(rows):,} page samples",
    )
    logger.info("Done")
    return ds_dict


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input_dir",    required=True)
    parser.add_argument("--repo_id",      required=True,
                        help="e.g. dh-unibe/image-text_lassberg-letters")
    parser.add_argument("--manifest",     default=None,
                        help="JSONL manifest filename inside input_dir")
    parser.add_argument("--collection",   default="unknown")
    parser.add_argument("--language",     default="de")
    parser.add_argument("--date_range",   default="")
    parser.add_argument("--val_fraction", type=float, default=0.05)
    parser.add_argument("--private",      action="store_true")
    args = parser.parse_args()

    root = Path(args.input_dir)
    samples = (load_samples_manifest(root, args.manifest)
               if args.manifest else load_samples_sidecar(root))
    logger.info(f"Found {len(samples):,} candidate pairs in {root}")

    rows = build_rows(samples, args.collection, args.language, args.date_range)
    push_dataset(rows, args.repo_id, args.val_fraction, private=args.private)


if __name__ == "__main__":
    main()
