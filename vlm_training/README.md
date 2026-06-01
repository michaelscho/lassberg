# VLM HTR Training Pipeline

QLoRA fine-tuning of [Qwen3-VL-30B-A3B-Instruct](https://huggingface.co/Qwen/Qwen3-VL-30B-A3B-Instruct)
for historical handwriting recognition (HTR), using the [dh-unibe](https://huggingface.co/dh-unibe)
datasets as training material.

## Hardware requirements

2x NVIDIA A40 (48 GB each). The model (31B MoE, 3B active) fits via `device_map="auto"` with
4-bit NF4 quantization (~16 GB weights).

## Pipeline overview

```
Incoming JPGs + txts
       |
  ingest_pages.py        preprocess & push to HF Hub
       |
  HF Hub dataset         same schema as dh-unibe line datasets + source_type column
       |
  data_prep.py           merge line + page HF datasets into local Arrow cache
       |
  train.py               QLoRA fine-tune (source-aware collator)
       |
  eval.py                CER / WER on validation split
       |
  push_to_hub.py         upload LoRA adapter to HF Hub
```

## Quick start

```bash
# 1. Install dependencies
pip install -r vlm_training/requirements.txt
pip install flash-attn --no-build-isolation   # optional but recommended

# 2. Ingest your page-level scans and push to HF Hub
python vlm_training/src/ingest_pages.py \
    --input_dir  data/pages_new \
    --repo_id    dh-unibe/image-text_lassberg-letters \
    --collection "Lassberg Letters" \
    --language   de \
    --date_range xix

# 3. Register the new repo in PAGE_DATASETS inside data_prep.py, then:
python vlm_training/src/data_prep.py
#   writes: data/train  data/val

# 4. Train
python vlm_training/src/train.py

# 5. Evaluate
python vlm_training/src/eval.py \
    --adapter output/qwen3-vl-htr \
    --n_samples 1000

# 6. Push adapter to Hub
python vlm_training/push_to_hub.py \
    --adapter  output/qwen3-vl-htr \
    --repo_id  dh-unibe/qwen3-vl-30b-htr
```

## Dataset sources

### Line-level (from dh-unibe HF Hub)

| Dataset | Samples | Content |
|---|---|---|
| image-text_kurrent-xix | ~158K | 19th-c. Kurrent handwriting |
| image-text_medieval-scripts_xiv-xv-xvi | ~100K+ | Medieval Latin/German |
| image-text_zh-regierungsratsprotokolle | ~100K+ | Zurich council minutes |
| image-text_historisches-grundbuch-basel_xix-xx | ~100K+ | Basel property register |
| image-text_aaeb-xiv-xvii | ~2.5K | Cantonal archive, multilingual |
| image-text_parzival-part-1 | ~3.6K | Medieval manuscript |
| image-text_rats-und-richtebuecher_xv-xvi | ~10K+ | Council records |
| image-text_german-20th-century | ~8.5K | 20th-c. German handwriting |

### Page-level (uploaded via ingest_pages.py)

Register datasets in `PAGE_DATASETS` inside `src/data_prep.py`.

## Source-aware collator

The `HTRCollator` applies different visual token budgets per sample type:

| source_type | max_pixels | max_seq_len | Use case |
|---|---|---|---|
| `line` | 256 × 28² ≈ 200K | 512 | Text-line crops |
| `page` | 2048 × 28² ≈ 1.6M | 4096 | Full-page scans |

## Memory budget (2x A40)

| Component | QLoRA (default) |
|---|---|
| Model weights (4-bit NF4) | ~16 GB |
| LoRA adapters | ~0.3 GB |
| Activations + grad checkpointing | ~8 GB |
| Optimizer (paged 8-bit Adam) | ~2 GB |
| **Total** | **~26 GB (single GPU)** |
