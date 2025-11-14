# src/llm_adjudicate_saia.py
"""
LLM adjudication for NER (SAIA client version).

- Reuses your `SaiaChatClient` (OpenAI-compatible HTTP).
- Preserves offsets by carrying through model spans in `evidence.mentions`.
- Adds a representative `char_span` per consolidated entity when possible.
- Can cap per-model NER items in the prompt via `max_per_model`.

Usage (quick):
    from saia_client import SaiaChatClient
    from llm_adjudicate_saia import adjudicate_entities_with_client

    client = SaiaChatClient()  # uses env: SAIA_API_KEY, SAIA_MODEL, SAIA_BASE_URL
    result = adjudicate_entities_with_client(
        client=client,
        letter_id="1234",
        title="Letter 1234 — Foo to Bar",
        letter_text="...",
        ner_results=ner_bundle,
        max_per_model=500,   # optional, controls prompt size
    )
"""

from __future__ import annotations
import json
from typing import Any, Dict, List, Optional

from saia_client import SaiaChatClient


# ---------------- Schema & prompt that PRESERVE OFFSETS ----------------

SCHEMA_JSON = {
  "letter_id": "string",
  "title": "string",
  "entities": [
    {
      "text": "string",
      "target_label": "PER|LOC|ORG|LIT_WORK|LIT_OBJECT|TIME",
      "added_by_llm": False,
      "char_span": { "start": 0, "end": 0 },   # representative occurrence, if determinable
      "evidence": {
        "mentions": [
          {
            "model": "hmbert|flair_base|flair_large|hf_default|llm",
            "text": "string",
            "label": "original model label",
            "score": 0.0,
            "start": 0,
            "end": 0
          }
        ],
        "vote_count": 0
      }
    }
  ],
  "dropped": [
    {
      "text": "string",
      "label": "string",
      "reason": "false positive | out of scope | duplicate shorter span",
      "evidence": {
        "model": "hmbert|flair_base|flair_large|hf_default",
        "score": 0.0
      }
    }
  ]
}

SYSTEM_PROMPT = f"""
You are a careful historical Named Entity Adjudicator for 18–19th-century German correspondence.
You will receive: (1) metadata and a human-readable title, (2) the full letter text, and (3) raw NER outputs from four models.
Your goal is to return ONE JSON object (no prose) that consolidates true entities, removes false positives, and harmonizes labels to PER, LOC, ORG, LIT_WORK, LIT_OBJECT, TIME.

Rules:
• Prefer inclusive spans (e.g., keep “Buchhändler Müller” over “Müller”).
• Merge duplicates across models into one entity.
• Decide LIT_WORK vs LIT_OBJECT:
  – LIT_WORK: abstract/intellectual works (titles, poems, books as works).
  – LIT_OBJECT: concrete manuscripts, specific exemplars/copies/volumes.
• Keep TIME mentions that are meaningful (dates, months, years in context).
• If something looks wrong (generic words like “lieben”, salutations, etc.), drop it.
• If you notice additional entities NOT in model outputs (especially works/objects),
  add them and set "added_by_llm": true.
• IMPORTANT: Preserve start/end offsets by copying the contributing model mentions into evidence.mentions.
  If possible, also choose ONE representative char_span for each consolidated entity.
• Output must be valid JSON and match this schema exactly:

{json.dumps(SCHEMA_JSON, ensure_ascii=False, indent=2)}
""".strip()


def _compact_ner_for_prompt(ner_results: Dict[str, List[Dict[str, Any]]],
                            max_per_model: Optional[int]) -> Dict[str, List[Dict[str, Any]]]:
    if not max_per_model:
        return ner_results
    compact: Dict[str, List[Dict[str, Any]]] = {}
    for name, arr in ner_results.items():
        compact[name] = arr[:max_per_model] if isinstance(arr, list) else []
    return compact


def build_messages(letter_id: str,
                   title: str,
                   letter_text: str,
                   ner_results: Dict[str, List[Dict[str, Any]]],
                   *,
                   extra_meta: Optional[Dict[str, Any]] = None,
                   max_per_model: Optional[int] = None) -> List[Dict[str, str]]:
    compact = _compact_ner_for_prompt(ner_results, max_per_model)
    meta = {"letter_id": letter_id}
    if extra_meta:
        meta.update(extra_meta)

    user_parts = [
        "TITLE\n=====\n" + title,
        "METADATA\n========\n" + json.dumps(meta, ensure_ascii=False, indent=2),
        "LETTER\n======\n" + letter_text,
        "NER OUTPUTS (raw)\n=================\n" + json.dumps(compact, ensure_ascii=False),
        (
            "TASK\n====\n"
            "Return a single JSON object (only JSON, no explanations) that conforms to the schema in the system message.\n"
            "- merge overlapping/conflicting mentions (choose the longest informative span),\n"
            "- map labels to PER, LOC, ORG, LIT_WORK, LIT_OBJECT, TIME,\n"
            "- add missing entities (mark \"added_by_llm\": true),\n"
            "- PRESERVE OFFSETS: include all contributing mentions (with start/end) under evidence.mentions,\n"
            "- and pick one representative char_span per entity if possible."
        )
    ]

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "\n\n".join(user_parts)},
    ]


def adjudicate_entities_with_client(
    *,
    client: SaiaChatClient,
    letter_id: str,
    title: str,
    letter_text: str,
    ner_results: Dict[str, List[Dict[str, Any]]],
    extra_meta: Optional[Dict[str, Any]] = None,
    temperature: float = 0.0,
    max_tokens: int = 2048,
    top_p: Optional[float] = None,
    max_per_model: Optional[int] = None,
    # You can pass extra OpenAI/SAIA-compatible flags via `extra`
    extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Make the SAIA call using your `SaiaChatClient`. Returns parsed JSON from the model.
    """
    messages = build_messages(
        letter_id=letter_id,
        title=title,
        letter_text=letter_text,
        ner_results=ner_results,
        extra_meta=extra_meta,
        max_per_model=max_per_model,
    )

    # Ask SAIA for JSON-only response
    return client.chat_json(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        extra=extra,
    )
