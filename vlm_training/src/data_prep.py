"""
Load and combine HF datasets — both line-level and page-level — into a
unified local Arrow cache with columns: image, text, source_type.

source_type in {'line', 'page'}

Usage:
    python vlm_training/src/data_prep.py
    # outputs: data/train  data/val  (Arrow format)
"""

import logging
from datasets import load_dataset, concatenate_datasets

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Dataset registry ───────────────────────────────────────────────────────────
# Each entry: (repo_id, split, source_type, min_text_len)
# source_type="page" -> already has the column; "line" -> inject it
LINE_DATASETS = [
    ("dh-unibe/image-text_kurrent-xix",                      "train", "line", 3),
    ("dh-unibe/image-text_medieval-scripts_xiv-xv-xvi",      "train", "line", 3),
    ("dh-unibe/image-text_zh-regierungsratsprotokolle",       "train", "line", 3),
    ("dh-unibe/image-text_historisches-grundbuch-basel_xix-xx_train", "train", "line", 3),
    ("dh-unibe/image-text_aaeb-xiv-xvii",                    "train", "line", 3),
    ("dh-unibe/image-text_parzival-part-1",                  "train", "line", 3),
    ("dh-unibe/image-text_rats-und-richtebuecher_xv-xvi",    "train", "line", 3),
    ("dh-unibe/image-text_german-20th-century",              "train", "line", 3),
    ("dh-unibe/image-text_koenigsfelden-charters-part-2",    "train", "line", 3),
    ("dh-unibe/image-text_koenigsfelden-charters-part-3",    "train", "line", 3),
    ("dh-unibe/image-text_koenigsfelden-charters-post-1500", "train", "line", 3),
    # Excluded: handwritten-bundesratsprotokolle (auto-transcribed, no ground truth)
]

PAGE_DATASETS = [
    # Register page-level datasets uploaded via ingest_pages.py, e.g.:
    # ("dh-unibe/image-text_lassberg-letters", "train", "page", 20),
]

ALL_DATASETS = LINE_DATASETS + PAGE_DATASETS

KEEP_COLS = {"image", "text", "source_type"}


def _load_one(repo_id, split, source_type, min_text_len):
    logger.info(f"Loading {repo_id} [{split}] ...")
    try:
        ds = load_dataset(repo_id, split=split)
    except Exception as e:
        logger.warning(f"  Skipping {repo_id}: {e}")
        return None

    before = len(ds)
    ds = ds.filter(
        lambda x: x["text"] is not None and len(x["text"].strip()) >= min_text_len
    )
    logger.info(f"  {len(ds):,} rows  (dropped {before - len(ds):,} short texts)")

    # Inject source_type if not already present
    if "source_type" not in ds.column_names:
        ds = ds.map(lambda _: {"source_type": source_type}, batched=False)

    # Drop all columns except the three we need
    drop = [c for c in ds.column_names if c not in KEEP_COLS]
    if drop:
        ds = ds.remove_columns(drop)

    return ds


def load_and_prepare(
    datasets: list[tuple] = ALL_DATASETS,
    val_fraction: float = 0.02,
    seed: int = 42,
    output_dir: str = "data",
):
    parts = [_load_one(*entry) for entry in datasets]
    parts = [p for p in parts if p is not None]

    full = concatenate_datasets(parts).shuffle(seed=seed)
    logger.info(f"Total samples: {len(full):,}")

    from collections import Counter
    counts = Counter(full["source_type"])
    for k, v in counts.items():
        logger.info(f"  {k:6s}: {v:,}")

    splits = full.train_test_split(test_size=val_fraction, seed=seed)
    train_ds, val_ds = splits["train"], splits["test"]

    train_ds.save_to_disk(f"{output_dir}/train")
    val_ds.save_to_disk(f"{output_dir}/val")
    logger.info(
        f"Saved -> {output_dir}/train ({len(train_ds):,}) "
        f"and {output_dir}/val ({len(val_ds):,})"
    )
    return train_ds, val_ds


if __name__ == "__main__":
    load_and_prepare()
