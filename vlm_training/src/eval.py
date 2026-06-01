"""
Evaluate the fine-tuned Qwen3-VL HTR adapter.
Reports Character Error Rate (CER) and Word Error Rate (WER).

Usage:
    python vlm_training/src/eval.py \\
        --adapter output/qwen3-vl-htr \\
        --n_samples 500
"""

import argparse
import logging
import torch
from datasets import load_from_disk
from transformers import AutoProcessor, AutoModelForImageTextToText
from peft import PeftModel
from jiwer import cer, wer

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an expert in historical handwriting recognition. "
    "Transcribe the text in the image exactly as written, "
    "preserving original spelling and punctuation."
)
USER_PROMPT = "Transcribe the handwritten text in this image."


def predict(model, processor, image, max_new_tokens: int = 512) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": [
            {"type": "image", "image": image},
            {"type": "text",  "text": USER_PROMPT},
        ]},
    ]
    text = processor.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = processor(
        text=[text],
        images=[image],
        max_pixels=2048 * 28 * 28,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
        )
    decoded = processor.decode(
        out[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    return decoded.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="Qwen/Qwen3-VL-30B-A3B-Instruct")
    parser.add_argument("--adapter",    required=True, help="Path to saved LoRA adapter")
    parser.add_argument("--data_dir",   default="data/val")
    parser.add_argument("--n_samples",  type=int, default=500)
    parser.add_argument("--max_new_tokens", type=int, default=512)
    args = parser.parse_args()

    logger.info("Loading processor and model ...")
    processor = AutoProcessor.from_pretrained(args.adapter, trust_remote_code=True)
    base = AutoModelForImageTextToText.from_pretrained(
        args.base_model,
        device_map="auto",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, args.adapter)
    model.eval()

    val_ds = load_from_disk(args.data_dir)
    n = min(args.n_samples, len(val_ds))
    val_ds = val_ds.select(range(n))
    logger.info(f"Evaluating on {n} samples ...")

    refs, hyps = [], []
    for i, ex in enumerate(val_ds):
        ref = ex["text"].strip()
        hyp = predict(model, processor, ex["image"], args.max_new_tokens)
        refs.append(ref)
        hyps.append(hyp)
        if (i + 1) % 50 == 0:
            logger.info(f"  {i + 1}/{n} done")

    print(f"\nCER: {cer(refs, hyps):.4f}")
    print(f"WER: {wer(refs, hyps):.4f}")

    print("\n--- Sample predictions ---")
    for r, h in zip(refs[:5], hyps[:5]):
        print(f"REF: {r}")
        print(f"HYP: {h}")
        print()


if __name__ == "__main__":
    main()
