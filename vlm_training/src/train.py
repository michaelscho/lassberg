"""
QLoRA fine-tuning of Qwen3-VL-30B-A3B-Instruct for historical HTR.

Architecture note
-----------------
Qwen3-VL-30B-A3B is a Mixture-of-Experts VLM (qwen3_vl_moe):
  - 31B total parameters, ~3B active per forward pass
  - Weights in bf16 ~62 GB; with 4-bit NF4 (QLoRA) ~16 GB
  - Fits comfortably on 2x A40 (48 GB each) via device_map="auto"

Launch:
    python vlm_training/src/train.py
"""

import logging
import torch
from datasets import load_from_disk
from transformers import AutoProcessor, AutoModelForImageTextToText, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, TaskType
from trl import SFTTrainer, SFTConfig

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from collator import HTRCollator

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MODEL_ID   = "Qwen/Qwen3-VL-30B-A3B-Instruct"
OUTPUT_DIR = "output/qwen3-vl-htr"

# ── 4-bit NF4 quantization (QLoRA) ────────────────────────────────────────────
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,   # saves ~0.4 bits/param extra
)

logger.info("Loading processor ...")
processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)

logger.info("Loading model (4-bit NF4, device_map=auto) ...")
model = AutoModelForImageTextToText.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto",          # spreads across all available GPUs automatically
    trust_remote_code=True,
    torch_dtype=torch.bfloat16,
    attn_implementation="flash_attention_2",  # remove if flash-attn not installed
)
model.config.use_cache = False

# ── LoRA config ────────────────────────────────────────────────────────────────
# For MoE: target attention + active expert FFN projections.
# Avoids targeting all expert weights (too many, marginal gain for HTR).
lora_config = LoraConfig(
    task_type=TaskType.CAUSAL_LM,
    r=64,
    lora_alpha=128,
    lora_dropout=0.05,
    bias="none",
    target_modules=[
        "q_proj", "k_proj", "v_proj", "o_proj",   # attention
        "gate_proj", "up_proj", "down_proj",        # active expert FFN
    ],
    modules_to_save=["lm_head"],
)
model = get_peft_model(model, lora_config)
model.print_trainable_parameters()
# Expected: ~80-120M trainable params (~0.3% of 31B)

# ── Data ───────────────────────────────────────────────────────────────────────
train_ds = load_from_disk("data/train")
val_ds   = load_from_disk("data/val")

# ── Training config ────────────────────────────────────────────────────────────
# batch_size=1 + grad_accum=16 -> effective batch of 16
# Page samples can exceed 4K tokens, so batch_size > 1 risks OOM.
training_args = SFTConfig(
    output_dir=OUTPUT_DIR,
    num_train_epochs=3,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=16,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.05,
    bf16=True,
    optim="paged_adamw_8bit",
    logging_steps=50,
    eval_strategy="steps",
    eval_steps=500,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=3,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    report_to="wandb",
    run_name="qwen3-vl-htr-mixed",
    dataloader_num_workers=2,
    remove_unused_columns=False,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
)

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_ds,
    eval_dataset=val_ds,
    data_collator=HTRCollator(processor, training=True),
    processing_class=processor.tokenizer,
)

trainer.train()
trainer.save_model(OUTPUT_DIR)
processor.save_pretrained(OUTPUT_DIR)
logger.info(f"Adapter saved to {OUTPUT_DIR}")
