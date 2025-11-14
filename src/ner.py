"""
ner.py — 4-model NER runner used by main_build.py

Models (JSONs written next to <letter>-plain.txt):
  - flair/ner-german                -> *.flair_base.json
  - flair/ner-german-large (external .german_large venv) -> *.flair_large.json
  - Davlan/bert-base-multilingual-cased-ner-hrl -> *.hf_bert.json
  - impresso-project/ner-stacked-bert-multilingual (custom 'generic-ner') -> *.hf_hmbert.json

Why external venv for flair-large?
  hmBERT tends to prefer transformers≈4.36.
  flair/ner-german-large is most reliable with Flair 0.13.1 + transformers≈4.33.
  To avoid version conflicts we ALWAYS run flair-large in a separate venv:
    REPO_ROOT/.german_large/{Scripts|bin}/python

Create it once:
  python -m venv .german_large
  # activate, then:
  pip install "flair==0.13.1" "transformers==4.33.3" "torch<=2.5.*"

NOTE: On Windows with PATHs containing spaces, subprocess calls are already safe (we pass arg list).
"""

from __future__ import annotations
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

# Avoid TF codepaths (speeds up + avoids Windows TF issues)
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")

from transformers import pipeline, AutoTokenizer
import transformers

# Flair base is run in THIS env
from flair.models import SequenceTagger
from flair.data import Sentence, Label


# --------- constants / helpers ----------

SUFFIXES = {
    "hmbert": ".hf_hmbert.json",
    "flair_base": ".flair_base.json",
    "flair_large": ".flair_large.json",
    "hf_default": ".hf_bert.json",
}

def _out_base(txt_path: Path) -> Path:
    return txt_path.with_suffix("")

def _save_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _summarize(name: str, ents: List[Dict[str, Any]], top_k: int = 10) -> None:
    print(f"\n=== {name} ===")
    print(f"Total entities: {len(ents)}")
    for e in sorted(ents, key=lambda x: x.get("score", 0.0), reverse=True)[:top_k]:
        t = str(e.get("text","")).replace("\n"," ")
        print(f"  {e.get('label',''):6} {e.get('score',0):.3f} {t[:80]}")

def _unique_entities(ents: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen: Dict[tuple, Dict[str, Any]] = {}
    for e in ents:
        key = (int(e.get("start",-1)), int(e.get("end",-1)),
               str(e.get("label","")), str(e.get("text","")))
        if key not in seen or float(e.get("score",0)) > float(seen[key].get("score",0)):
            seen[key] = e
    return sorted(seen.values(), key=lambda x: (x.get("start",-1), x.get("end",-1)))

def _read_text(path: Path, max_chars: Optional[int]) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Text file not found: {path}")
    txt = path.read_text(encoding="utf-8", errors="ignore")
    return txt[:max_chars] if (max_chars and len(txt) > max_chars) else txt

def _repo_root() -> Path:
    # assuming this file is in REPO_ROOT/src/ner.py
    return Path(__file__).resolve().parents[1]


# --------- version sanity for hmBERT ----------

def _warn_transformers_for_hmbert() -> None:
    ver = transformers.__version__
    try:
        major, minor, *_ = [int(x) for x in ver.split(".")]
    except Exception:
        print(f"⚠️  Unknown transformers version string: {ver}")
        return
    if not ((major == 4 and 30 <= minor <= 43) or (major == 4 and minor == 36)):
        print(f"⚠️  transformers {ver} may not play nicely with hmBERT remote pipeline.")
        print('    If you hit loader errors, try:  pip install "transformers==4.36.2"')


# --------- runners (local env) ----------

def _run_flair_base(text: str, device: str = "cpu") -> List[Dict[str, Any]]:
    tagger = SequenceTagger.load("flair/ner-german")
    tagger.to("cpu" if device == "cpu" else "cuda")
    sent = Sentence(text)
    tagger.predict(sent)
    out: List[Dict[str, Any]] = []
    for span in sent.get_spans("ner"):
        lab: Label = span.labels[0]
        out.append({
            "text": span.text,
            "label": lab.value,
            "score": float(lab.score),
            "start": span.start_position,
            "end": span.end_position,
        })
    return out

def _run_hf_token_cls_chunked(text: str, model_id: str, device: str = "cpu",
                              chunk_chars: int = 1500, overlap_chars: int = 120) -> List[Dict[str, Any]]:
    dev = 0 if device == "gpu" else -1
    nlp = pipeline("token-classification", model=model_id, tokenizer=model_id,
                   aggregation_strategy="simple", device=dev)
    ents: List[Dict[str, Any]] = []
    n = len(text); step = max(1, chunk_chars - overlap_chars)
    for start in range(0, n, step):
        chunk = text[start:start+chunk_chars]
        for r in nlp(chunk):
            ents.append({
                "text": r.get("word"),
                "label": r.get("entity_group"),
                "score": float(r.get("score", 0.0)),
                "start": int(r.get("start", 0)) + start,
                "end": int(r.get("end", 0)) + start,
            })
    return _unique_entities(ents)

def _run_hmbert_generic_ner(text: str, model_id: str, device: str = "cpu",
                            chunk_chars: int = 1500, overlap_chars: int = 120,
                            revision: Optional[str] = None) -> List[Dict[str, Any]]:
    _warn_transformers_for_hmbert()
    dev = 0 if device == "gpu" else -1

    def build_pipe(name: str):
        tok = AutoTokenizer.from_pretrained(name, trust_remote_code=True, use_fast=True, revision=revision)
        return pipeline("generic-ner", model=name, tokenizer=tok, trust_remote_code=True,
                        device=dev, revision=revision)

    try:
        ner = build_pipe(model_id)
    except Exception as e:
        fallback = "impresso-project/ner-stacked-bert-multilingual-light"
        print(f"⚠️  Could not load '{model_id}' ({e}). Falling back to '{fallback}'.")
        ner = build_pipe(fallback)

    ents: List[Dict[str, Any]] = []
    n = len(text); step = max(1, chunk_chars - overlap_chars)
    for start in range(0, n, step):
        chunk = text[start:start+chunk_chars]
        results = ner(chunk)  # dicts: type, confidence_ner, surface, lOffset, rOffset
        for r in results:
            conf = r.get("confidence_ner", 0.0)
            score = float(conf)/100.0 if conf and conf > 1 else float(conf or 0.0)
            ents.append({
                "text": r.get("surface",""),
                "label": r.get("type",""),
                "score": score,
                "start": int(r.get("lOffset",0)) + start,
                "end": int(r.get("rOffset",0)) + start,
            })
    return _unique_entities(ents)


# --------- flair-large external runner ----------

def _external_python_for_flair_large() -> Path:
    root = _repo_root()
    if os.name == "nt":
        py = root / ".german_large" / "Scripts" / "python.exe"
    else:
        py = root / ".german_large" / "bin" / "python"
    if not py.exists():
        raise FileNotFoundError(
            f"Flair-large external interpreter not found at: {py}\n"
            "Create it:\n"
            "  python -m venv .german_large\n"
            "  # activate, then:\n"
            "  pip install \"flair==0.13.1\" \"transformers==4.33.3\" \"torch<=2.5.*\""
        )
    return py

def _flair_worker_path() -> Path:
    # write helper to src/ if missing
    path = _repo_root() / "src" / "flair_large_worker.py"
    if not path.exists():
        code = r'''from __future__ import annotations
import argparse, json
from pathlib import Path
from flair.models import SequenceTagger
from flair.data import Sentence, Label

def read_text(p: Path, max_chars: int | None) -> str:
    t = p.read_text(encoding="utf-8", errors="ignore")
    return t[:max_chars] if (max_chars and len(t) > max_chars) else t

def run(text: str, device: str = "cpu"):
    tagger = SequenceTagger.load("flair/ner-german-large")
    tagger.to("cpu" if device == "cpu" else "cuda")
    sent = Sentence(text)
    tagger.predict(sent)
    out = []
    for span in sent.get_spans("ner"):
        lab: Label = span.labels[0]
        out.append({
            "text": span.text,
            "label": lab.value,
            "score": float(lab.score),
            "start": span.start_position,
            "end": span.end_position,
        })
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text-file", required=True)
    ap.add_argument("--out-json", required=True)
    ap.add_argument("--device", choices=["cpu","gpu"], default="cpu")
    ap.add_argument("--max-chars", type=int, default=None)
    args = ap.parse_args()

    txt = read_text(Path(args.text_file), args.max_chars)
    ents = run(txt, device=args.device)
    Path(args.out_json).write_text(json.dumps(ents, ensure_ascii=False, indent=2), encoding="utf-8")

if __name__ == "__main__":
    main()
'''
        path.write_text(code, encoding="utf-8")
    return path

def _run_flair_large_external(text_file: Path, out_json: Path,
                              device: str = "cpu", max_chars: Optional[int] = None,
                              python_exe: Optional[Path] = None) -> List[Dict[str, Any]]:
    py = python_exe if python_exe else _external_python_for_flair_large()
    worker = _flair_worker_path()
    cmd = [str(py), str(worker),
           "--text-file", str(text_file),
           "--out-json", str(out_json),
           "--device", device]
    if max_chars is not None:
        cmd += ["--max-chars", str(max_chars)]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print("⚠️  External Flair-large worker failed.")
        print("---- stdout ----"); print(proc.stdout)
        print("---- stderr ----"); print(proc.stderr)
        raise RuntimeError("External Flair-large run failed.")
    return json.loads(out_json.read_text(encoding="utf-8"))


# --------- public API ----------

def run_ner_on_text_file(
    txt_path: Path,
    *,
    device: str = "cpu",
    hf_model: str = "Davlan/bert-base-multilingual-cased-ner-hrl",
    hmbert_model: str = "impresso-project/ner-stacked-bert-multilingual",
    hmbert_revision: Optional[str] = None,
    chunk_chars: int = 1500,
    overlap_chars: int = 120,
    max_chars: Optional[int] = None,
    flair_large_python: Optional[str] = None,
    verbose: bool = True,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Run all 4 models on the given <letter>-plain.txt and write JSONs next to it.
    Returns a dict with the in-memory results.
    """
    txt_path = Path(txt_path)
    base = _out_base(txt_path)
    text = _read_text(txt_path, max_chars=max_chars)

    # hmBERT
    hm = _run_hmbert_generic_ner(text, hmbert_model, device,
                                 chunk_chars, overlap_chars, hmbert_revision)
    _save_json(base.with_suffix(SUFFIXES["hmbert"]), hm)
    if verbose: _summarize(f"HF hmBERT ({hmbert_model})", hm)

    # Flair base
    fb = _run_flair_base(text, device=device)
    _save_json(base.with_suffix(SUFFIXES["flair_base"]), fb)
    if verbose: _summarize("Flair base (flair/ner-german)", fb)

    # Flair large (external venv; hard-coded behaviour)
    out_large = base.with_suffix(SUFFIXES["flair_large"])
    fl_py = Path(flair_large_python) if flair_large_python else None
    try:
        fl = _run_flair_large_external(txt_path, out_large, device=device,
                                       max_chars=max_chars, python_exe=fl_py)
        # already written by worker; just show
        if verbose: _summarize("Flair large (external venv)", fl)
    except Exception as e:
        print(f"\n⚠️  External Flair-large failed: {e}")
        fl = []

    # HF default (Davlan…)
    hf = _run_hf_token_cls_chunked(text, hf_model, device, chunk_chars, overlap_chars)
    _save_json(base.with_suffix(SUFFIXES["hf_default"]), hf)
    if verbose: _summarize(f"HF BERT ({hf_model})", hf)

    if verbose:
        print("\nNER outputs written:")
        for k, suf in SUFFIXES.items():
            print(f"  {base.with_suffix(suf)}")

    return {
        "hmbert": hm,
        "flair_base": fb,
        "flair_large": fl,
        "hf_default": hf,
    }
