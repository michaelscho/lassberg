# src/main_build.py
"""
Build TEI line streams from exported PAGE-XML, then run NER + LLM adjudication + register linking.
Idempotent: reuses existing JSON outputs unless you force recomputation.

Artifacts per letter (in the PAGE-XML folder):
  - lassberg-letter-<ID>-tei-lines.txt
  - lassberg-letter-<ID>-plain.txt
  - lassberg-letter-<ID>-ner_raw.json         (raw outputs from 4 NER models)
  - lassberg-letter-<ID>-ner_final.json       (LLM-adjudicated, normalized entities)
  - lassberg-letter-<ID>-entities-linked.json (IDs linked to registers/GND/Wikidata)

Usage
-----
Interactive selection, full pipeline (reuse if exists):
  python main_build.py

Force recompute NER+LLM for selected docs:
  python main_build.py --force-ner --force-llm

Always run Flair-large in external env:
  python main_build.py --flair-large-python "C:/.../.german_large/Scripts/python.exe"

GPU for HF/hmBERT (Flair runs on CPU/GPU as requested):
  python main_build.py --device gpu
"""

from __future__ import annotations
import argparse
import sys
import json
from pathlib import Path

import config
from file_selection import (
    select_documents_interactive,
    select_documents_from_file,
)
from pagexml_to_tei import build_line_stream, derive_letter_id_from_title

# NER + LLM adjudication + linking
from ner import run_ner_on_text_file
from saia_client import SaiaChatClient
from llm_adjucate import adjudicate_entities_with_client   
from link_entities_llm import link_entities_with_llm


def _write_text_artifacts(letter_id: str, dest_dir: Path, tei_lines: str, plain_text: str) -> None:
    (dest_dir / f"lassberg-letter-{letter_id}-tei-lines.txt").write_text(tei_lines, encoding="utf-8")
    (dest_dir / f"lassberg-letter-{letter_id}-plain.txt").write_text(plain_text, encoding="utf-8")


def _write_json(dest_dir: Path, filename: str, data: dict) -> Path:
    p = dest_dir / filename
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build TEI line streams from exported PAGE-XML, run NER, LLM adjudication, and register linking."
    )
    # Selection
    parser.add_argument("--backend", choices=["transkribus", "escriptorium"], default="transkribus")
    parser.add_argument("--file", type=str, default=None,
                        help="TXT with titles/ids (one per line). If omitted, starts interactive selection.")
    parser.add_argument("--match-on", choices=["title", "id"], default="title")
    parser.add_argument("--case-sensitive", action="store_true")

    # Interactive filters & sorting
    parser.add_argument("--exclude-done", action="store_true")
    parser.add_argument("--only-done", action="store_true")
    parser.add_argument("--filter", type=str, default=None)
    parser.add_argument("--sort-by", choices=["id", "title", "pages"], default="title")
    parser.add_argument("--desc", action="store_true")
    parser.add_argument("--page-size", type=int, default=15)

    # Builder options
    parser.add_argument("--export-root", type=str, default=None,
                        help="Root folder with PAGE-XML (default: config.export_folder).")
    parser.add_argument("--corresp-base", type=str, default="../pagexml")
    parser.add_argument("--no-write", action="store_true", help="Skip writing TEI/plain (still writes JSON if computed).")

    # Idempotency flags (reuse existing JSON unless forced)
    parser.add_argument("--force-ner", action="store_true", help="Recompute NER even if *-ner_raw.json exists.")
    parser.add_argument("--force-llm", action="store_true", help="Recompute adjudication even if *-ner_final.json exists.")
    parser.add_argument("--force-link", action="store_true", help="Recompute linking even if *-entities-linked.json exists.")

    # NER options
    parser.add_argument("--device", choices=["cpu", "gpu"], default="cpu")
    parser.add_argument("--hmbert-revision", type=str, default=None)
    parser.add_argument("--max-chars", type=int, default=None)
    parser.add_argument("--chunk-chars", type=int, default=1500)
    parser.add_argument("--overlap", type=int, default=120)
    parser.add_argument("--flair-large-python", type=str, default=None,
                        help="PATH to other venv's python for flair/ner-german-large (recommended).")

    # SAIA / LLM settings
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--max-tokens", type=int, default=2048)
    parser.add_argument("--max-per-model", type=int, default=None,
                        help="If set, cap NER items per model included in the adjudication prompt.")
    parser.add_argument("--llm-timeout", type=int, default=800,
                        help="HTTP timeout (seconds) for SAIA requests.")

    # Register files for linking
    parser.add_argument("--register-root", type=str, default=str(Path("..") / "data" / "register"),
                        help="Folder with lassberg-persons.xml, -places.xml, -literature.xml")

    args = parser.parse_args()

    # 1) Select documents
    try:
        if args.file:
            chosen = select_documents_from_file(
                args.file,
                backend=args.backend,
                transkribus_kwargs={"collection_id": config.collection_id},
                match_on=args.match_on,
                case_sensitive=args.case_sensitive,
                sort_by=args.sort_by,
                descending=args.desc,
            )
        else:
            chosen = select_documents_interactive(
                backend=args.backend,
                transkribus_kwargs={"collection_id": config.collection_id},
                exclude_done=args.exclude_done,
                only_done=args.only_done,
                text_filter=args.filter,
                sort_by=args.sort_by,
                descending=args.desc,
                page_size=args.page_size,
            )
    except Exception as e:
        print(f"Selection failed: {e}")
        sys.exit(1)

    if not chosen:
        print("No documents selected. Exiting.")
        return

    export_root = Path(args.export_root) if args.export_root else Path(config.export_folder)
    print(f"Reading PAGE-XML from: {export_root.resolve()}\n")

    # 2) SAIA client (once)
    try:
        saia_client = SaiaChatClient(timeout=args.llm_timeout)
    except Exception as e:
        print(f"⚠️ Could not initialize SAIA client: {e}")
        sys.exit(1)

    # Register paths (for linker)
    reg_root = Path(args.register_root)
    persons_xml = reg_root / "lassberg-persons.xml"
    places_xml = reg_root / "lassberg-places.xml"
    literature_xml = reg_root / "lassberg-literature.xml"

    for doc in chosen:
        letter_id = derive_letter_id_from_title(doc.title, fallback_numeric=doc.id)

        # 3) Build TEI line streams (plain & tei-lines)
        try:
            res = build_line_stream(
                letter_id,
                export_root=export_root,
                corresp_base=args.corresp_base,
            )
        except FileNotFoundError as e:
            print(f"- {doc.id} ({doc.title}): {e}")
            continue
        except Exception as e:
            print(f"- {doc.id} ({doc.title}): TEI build failed: {e}")
            continue

        # Optionally write TEI/plain
        if not args.no_write:
            _write_text_artifacts(res.letter_id, res.source_dir, res.tei_lines, res.plain_text)

        # Common paths
        txt_path = res.source_dir / f"lassberg-letter-{res.letter_id}-plain.txt"
        ner_raw_path = res.source_dir / f"lassberg-letter-{res.letter_id}-ner_raw.json"
        ner_final_path = res.source_dir / f"lassberg-letter-{res.letter_id}-ner_final.json"
        linked_path = res.source_dir / f"lassberg-letter-{res.letter_id}-entities-linked.json"

        # 4) NER (reuse if exists and not forced)
        try:
            if ner_raw_path.exists() and not args.force_ner:
                ner_bundle = _load_json(ner_raw_path)
                print(f"  reusing NER: {ner_raw_path.name}")
            else:
                ner_bundle = run_ner_on_text_file(
                    txt_path=txt_path,
                    device=args.device,
                    hmbert_revision=args.hmbert_revision,
                    max_chars=args.max_chars,
                    chunk_chars=args.chunk_chars,
                    overlap_chars=args.overlap,              # NOTE: correct kwarg name
                    flair_large_python=args.flair_large_python,  # External venv (recommended)
                    verbose=True,
                )
                _write_json(res.source_dir, ner_raw_path.name, ner_bundle)
        except Exception as e:
            print(f"- {doc.id} ({doc.title}): NER failed: {e}")
            continue

        # 5) LLM adjudication (reuse if exists and not forced)
        try:
            if ner_final_path.exists() and not args.force_llm:
                adjudicated = _load_json(ner_final_path)
                print(f"  reusing adjudication: {ner_final_path.name}")
            else:
                adjudicated = adjudicate_entities_with_client(
                    client=saia_client,
                    letter_id=res.letter_id,
                    title=f"Letter {res.letter_id} — {doc.title}",
                    letter_text=res.plain_text,
                    ner_results=ner_bundle,
                    extra_meta={"source_folder": str(res.source_dir)},
                    temperature=args.temperature,
                    max_tokens=args.max_tokens,
                    max_per_model=args.max_per_model,
                )
                _write_json(res.source_dir, ner_final_path.name, adjudicated)
        except Exception as e:
            print(f"- {doc.id} ({doc.title}): LLM adjudication failed: {e}")
            continue

        # 6) Register linking (reuse if exists and not forced)
        try:
            if linked_path.exists() and not args.force_link:
                print(f"  reusing links: {linked_path.name}")
            else:
                linked = link_entities_with_llm(
                    adjudicated,
                    letter_text=txt_path.read_text(encoding="utf-8"),
                    registers={
                        "persons_xml": str(persons_xml),
                        "places_xml": str(places_xml),
                        "literature_xml": str(literature_xml),
                    },
                    saia_client=saia_client,
                    #enable_external=True,        # set False to avoid GND/Wikidata fallback
                    prefer_register=True,
                    fuzzy_threshold=92,
                    context_window=60,
                    suggestions_path=str(res.source_dir / f"lassberg-letter-{res.letter_id}-register-suggestions.json"),
                )
                _write_json(res.source_dir, linked_path.name, linked)
        except Exception as e:
            print(f"- {doc.id} ({doc.title}): Linking failed: {e}")
            continue

        # Summary
        print(f"- {doc.id}: {doc.title}")
        print(f"  letter: lassberg-letter-{res.letter_id}")
        print(f"  pages:  {res.page_count}  lines: {res.line_count}")
        print(f"  folder: {res.source_dir}")
        if not args.no_write:
            print(f"  wrote : {res.source_dir}/lassberg-letter-{res.letter_id}-tei-lines.txt")
            print(f"         {res.source_dir}/lassberg-letter-{res.letter_id}-plain.txt")
        print(f"         {ner_raw_path}")
        print(f"         {ner_final_path}")
        print(f"         {linked_path}")
        print("")

    print("Done.")


if __name__ == "__main__":
    main()
