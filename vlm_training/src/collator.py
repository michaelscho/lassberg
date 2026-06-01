"""
HTRCollator — source-aware data collator for mixed line + page batches.

Resolution budgets (Qwen3-VL uses 28x28 px patches):
  line  ->  max_pixels = 256  * 28 * 28  ~200K px   -> ~256  visual tokens
  page  ->  max_pixels = 2048 * 28 * 28  ~1.6M px   -> ~2048 visual tokens
"""

import torch
from PIL import Image
from transformers import AutoProcessor

PIXEL_BUDGET = {
    "line": 256  * 28 * 28,
    "page": 2048 * 28 * 28,
}
MAX_SEQ_LEN = {
    "line":  512,
    "page": 4096,
}

SYSTEM_PROMPT = (
    "You are an expert in historical handwriting recognition. "
    "Transcribe the text in the image exactly as written, "
    "preserving original spelling and punctuation."
)
USER_PROMPT = "Transcribe the handwritten text in this image."


def _infer_source_type(image: Image.Image) -> str:
    """Fallback: infer from image dimensions if source_type column is absent."""
    return "page" if max(image.size) > 800 else "line"


class HTRCollator:
    def __init__(self, processor: AutoProcessor, training: bool = True):
        self.processor = processor
        self.training  = training

    def _build_messages(self, image, text, training: bool) -> list[dict]:
        msgs = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "image", "image": image},
                {"type": "text",  "text": USER_PROMPT},
            ]},
        ]
        if training:
            msgs.append({"role": "assistant", "content": text.strip()})
        return msgs

    def _mask_prompt(self, labels: torch.Tensor) -> torch.Tensor:
        """Mask everything up to and including the assistant header so loss
        is only computed on the transcription output."""
        assistant_ids = self.processor.tokenizer.encode(
            "<|im_start|>assistant\n", add_special_tokens=False
        )
        n = len(assistant_ids)
        for i in range(len(labels) - n):
            if labels[i : i + n].tolist() == assistant_ids:
                labels[: i + n] = -100
                return labels
        labels[:] = -100   # fallback: mask everything
        return labels

    def __call__(self, examples: list[dict]) -> dict:
        all_ids, all_mask, all_pv, all_grid, all_labels = [], [], [], [], []

        for ex in examples:
            source  = ex.get("source_type") or _infer_source_type(ex["image"])
            max_px  = PIXEL_BUDGET[source]
            max_len = MAX_SEQ_LEN[source]

            msgs     = self._build_messages(ex["image"], ex["text"], self.training)
            text_str = self.processor.apply_chat_template(
                msgs, tokenize=False, add_generation_prompt=not self.training
            )

            enc = self.processor(
                text=[text_str],
                images=[ex["image"]],
                max_pixels=max_px,
                padding=False,
                truncation=True,
                max_length=max_len,
                return_tensors="pt",
            )

            ids = enc["input_ids"][0]
            all_ids.append(ids)
            all_mask.append(enc["attention_mask"][0])
            all_pv.append(enc["pixel_values"])
            all_grid.append(enc["image_grid_thw"])

            if self.training:
                labels = ids.clone()
                labels[labels == self.processor.tokenizer.pad_token_id] = -100
                labels = self._mask_prompt(labels)
                all_labels.append(labels)

        # ── Pad all sequences to the longest in this batch ────────────────────
        max_seq = max(t.shape[0] for t in all_ids)
        pad_id  = self.processor.tokenizer.pad_token_id
        B       = len(examples)

        input_ids      = torch.full((B, max_seq), pad_id, dtype=torch.long)
        attention_mask = torch.zeros(B, max_seq, dtype=torch.long)

        for i, (ids, mask) in enumerate(zip(all_ids, all_mask)):
            L = ids.shape[0]
            input_ids[i, :L]      = ids
            attention_mask[i, :L] = mask

        batch = {
            "input_ids":      input_ids,
            "attention_mask": attention_mask,
            "pixel_values":   torch.cat(all_pv,   dim=0),
            "image_grid_thw": torch.cat(all_grid, dim=0),
        }

        if self.training:
            labels_padded = torch.full((B, max_seq), -100, dtype=torch.long)
            for i, lab in enumerate(all_labels):
                labels_padded[i, :lab.shape[0]] = lab
            batch["labels"] = labels_padded

        return batch
