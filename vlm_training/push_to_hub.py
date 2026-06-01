"""
Push the fine-tuned LoRA adapter (and optionally a merged full model) to HF Hub.

Usage:
    python vlm_training/push_to_hub.py \\
        --adapter  output/qwen3-vl-htr \\
        --repo_id  dh-unibe/qwen3-vl-30b-htr
"""

import argparse
import logging
import torch
from transformers import AutoProcessor, AutoModelForImageTextToText
from peft import PeftModel

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base_model", default="Qwen/Qwen3-VL-30B-A3B-Instruct")
    parser.add_argument("--adapter",    required=True)
    parser.add_argument("--repo_id",    required=True,
                        help="e.g. dh-unibe/qwen3-vl-30b-htr")
    parser.add_argument("--merge",      action="store_true",
                        help="Merge LoRA weights into base model before pushing "
                             "(creates a large ~62 GB upload)")
    parser.add_argument("--private",    action="store_true")
    args = parser.parse_args()

    logger.info("Pushing processor ...")
    processor = AutoProcessor.from_pretrained(args.adapter, trust_remote_code=True)
    processor.push_to_hub(args.repo_id, private=args.private)

    logger.info("Loading base model ...")
    base = AutoModelForImageTextToText.from_pretrained(
        args.base_model,
        device_map="cpu",
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    model = PeftModel.from_pretrained(base, args.adapter)

    if args.merge:
        logger.info("Merging LoRA weights and pushing full model (~62 GB) ...")
        merged = model.merge_and_unload()
        merged.push_to_hub(args.repo_id + "-merged", private=args.private)
    else:
        logger.info("Pushing LoRA adapter only (~200 MB) ...")
        model.push_to_hub(args.repo_id, private=args.private)

    logger.info(f"Done -> https://huggingface.co/{args.repo_id}")


if __name__ == "__main__":
    main()
