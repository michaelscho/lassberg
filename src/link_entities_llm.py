# link_entities_llm.py
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json
import re

# Prefer lxml; fall back to stdlib ET
try:
    from lxml import etree as ET
except Exception:
    import xml.etree.ElementTree as ET  # type: ignore

# Optional fast fuzzy
try:
    from rapidfuzz import fuzz
    _HAVE_RAPIDFUZZ = True
except Exception:
    from difflib import SequenceMatcher
    _HAVE_RAPIDFUZZ = False


# ------------------------- small utils -------------------------

def _read_text(p: Path) -> str:
    return Path(p).read_text(encoding="utf-8")

def _norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"[“”„‚’‘'`´\"\(\)\[\]\{\}<>]", "", s)
    return s

def _similarity(a: str, b: str) -> float:
    a, b = _norm(a), _norm(b)
    if not a or not b:
        return 0.0
    if _HAVE_RAPIDFUZZ:
        return float(fuzz.token_set_ratio(a, b))
    return 100.0 * SequenceMatcher(None, a, b).ratio()

def _top_k_by_similarity(query: str, candidates: List[Tuple[str, str, Dict[str, Any]]], k: int = 8) -> List[Tuple[float, Tuple[str, str, Dict[str, Any]]]]:
    scored: List[Tuple[float, Tuple[str, str, Dict[str, Any]]]] = []
    for label, xml_id, payload in candidates:
        scored.append((_similarity(query, label), (label, xml_id, payload)))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:k]


# ------------------------- Register loading -------------------------

@dataclass
class RegisterEntry:
    kind: str           # "person" | "place" | "bibl"
    xml_id: str
    label: str
    ref: Optional[str]
    extra: Dict[str, Any]

def _get_xml_id(el: ET._Element) -> Optional[str]:
    return el.get("{http://www.w3.org/XML/1998/namespace}id") or el.get("xml:id")

def _text(el: Optional[ET._Element]) -> str:
    if el is None:
        return ""
    txt = "".join(el.itertext()).strip()
    return re.sub(r"\s+", " ", txt)

def _load_persons_xml(path: Path) -> List[RegisterEntry]:
    root = ET.parse(str(path)).getroot()
    people = root.findall(".//{*}person")
    out: List[RegisterEntry] = []
    for p in people:
        xml_id = _get_xml_id(p) or ""
        persName = p.find(".//{*}persName")
        label = _text(persName) or xml_id
        ref = (persName.get("ref") if persName is not None else None) or p.get("ref")
        out.append(RegisterEntry(kind="person", xml_id=xml_id, label=label, ref=ref, extra={}))
    return out

def _load_places_xml(path: Path) -> List[RegisterEntry]:
    root = ET.parse(str(path)).getroot()
    places = root.findall(".//{*}place")
    out: List[RegisterEntry] = []
    for pl in places:
        xml_id = _get_xml_id(pl) or ""
        placeName = pl.find(".//{*}placeName")
        label = _text(placeName) or xml_id
        ref = (placeName.get("ref") if placeName is not None else None) or pl.get("ref")
        out.append(RegisterEntry(kind="place", xml_id=xml_id, label=label, ref=ref, extra={}))
    return out

def _load_bibl_xml(path: Path) -> List[RegisterEntry]:
    root = ET.parse(str(path)).getroot()
    bibls = root.findall(".//{*}bibl")
    out: List[RegisterEntry] = []
    for b in bibls:
        xml_id = _get_xml_id(b) or ""
        author = _text(b.find(".//{*}author"))
        title  = _text(b.find(".//{*}title"))
        idno   = _text(b.find(".//{*}idno"))
        label = (author + " " + title).strip() or title or xml_id
        out.append(RegisterEntry(kind="bibl", xml_id=xml_id, label=label, ref=None, extra={"idno": idno}))
    return out

def load_registers(registers: Dict[str, str | Path], verbose: bool = True) -> Dict[str, List[RegisterEntry]]:
    persons = _load_persons_xml(Path(registers["persons_xml"]))
    places  = _load_places_xml(Path(registers["places_xml"]))
    bibls   = _load_bibl_xml(Path(registers["literature_xml"]))
    if verbose:
        print(f"  Registers loaded: persons={len(persons)}  places={len(places)}  bibl={len(bibls)}")
    return {"person": persons, "place": places, "bibl": bibls}


# ------------------------- LLM pick (optional) -------------------------

def _context_window(text: str, start: int, end: int, window: int = 60) -> str:
    s = max(0, start - window)
    e = min(len(text), end + window)
    left = text[s:start]
    mid  = text[start:end]
    right= text[end:e]
    return f"...{left}[{mid}]{right}..."

def _build_llm_choice_prompt(entity: Dict[str, Any],
                             context: str,
                             top_candidates: List[RegisterEntry]) -> List[Dict[str, str]]:
    sys_msg = {
        "role": "system",
        "content": (
            "You are a careful historical linker. "
            "Given an entity mention with short context and candidate list from a curated register, "
            "choose the best matching register xml:id or 'none'. Return only JSON: "
            '{"pick":"<xml_id or none>","confidence":0..1}. '
            "Prefer exact/normalized matches (e.g., 'v.'→'von'), favor specific candidates."
        )
    }
    ent_txt = entity.get("text", "")
    label = entity.get("target_label") or entity.get("label") or ""
    choices = "\n".join([f"- {e.xml_id}: {e.label}" + (f" (ref: {e.ref})" if e.ref else "") for e in top_candidates]) or "(no candidates)"
    user_msg = {
        "role": "user",
        "content": (
            f"ENTITY: {ent_txt}\n"
            f"LABEL: {label}\n"
            f"CONTEXT: {context}\n\n"
            f"CANDIDATES (xml_id: label):\n{choices}\n\n"
            "Pick one xml_id from the list or 'none'."
        )
    }
    return [sys_msg, user_msg]

def _ask_llm_pick(saia_client: Any,
                  entity: Dict[str, Any],
                  context: str,
                  candidates: List[RegisterEntry]) -> Tuple[str, float]:
    msgs = _build_llm_choice_prompt(entity, context, candidates)
    data = saia_client.chat_json(msgs, temperature=0.0, max_tokens=256)
    pick = str(data.get("pick", "none")).strip() or "none"
    conf = float(data.get("confidence", 0.0))
    return pick, conf


# ------------------------- Public API -------------------------

LABEL_MAP = {
    # your adjudicated labels
    "PER": "person",
    "ORG": "person",     # historically might live in persons register
    "LOC": "place",
    "LIT_WORK": "bibl",
    "LIT_OBJECT": "bibl",
    "BIBL": "bibl",
    "MANUSCRIPT": "bibl",
}

def _extract_label(ent: Dict[str, Any]) -> str:
    # Be generous: adjudicator may use "target_label" (your case) or "label"
    raw = ent.get("target_label") or ent.get("label") or ""
    return raw

def _extract_span(ent: Dict[str, Any]) -> Tuple[int, int]:
    if "char_span" in ent and isinstance(ent["char_span"], dict):
        return int(ent["char_span"].get("start", -1)), int(ent["char_span"].get("end", -1))
    return int(ent.get("start", -1)), int(ent.get("end", -1))

def link_entities_with_llm(
    adjudicated: Dict[str, Any],
    *,
    letter_text: str,
    registers: Dict[str, str | Path],
    saia_client: Optional[Any] = None,
    prefer_register: bool = True,
    fuzzy_threshold: int = 92,
    context_window: int = 60,
    topk_for_llm: int = 6,
    suggestions_path: Optional[str | Path] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Enrich adjudicated entities with register links; keeps start/end.

    Input expects:
      {
        "entities": [ { "text":..., "target_label":..., "char_span":{"start":..,"end":..}, ... }, ... ],
        "added_by_llm": [ ... ]   # optional
      }
    """
    # normalize input
    entities: List[Dict[str, Any]] = []
    added: List[Dict[str, Any]] = []
    if isinstance(adjudicated, dict):
        entities = list(adjudicated.get("entities") or [])
        added    = list(adjudicated.get("added_by_llm") or [])
    elif isinstance(adjudicated, list):
        entities = adjudicated
    else:
        raise ValueError("adjudicated must be dict with 'entities' or a list of entities")

    # load registers
    regs = load_registers(registers, verbose=verbose)

    # prebuild candidate banks
    banks: Dict[str, List[Tuple[str, str, Dict[str, Any]]]] = {
        "person": [(e.label, e.xml_id, {"ref": e.ref, **e.extra, "kind": "person"}) for e in regs.get("person", [])],
        "place":  [(e.label, e.xml_id, {"ref": e.ref, **e.extra, "kind": "place"})  for e in regs.get("place", [])],
        "bibl":   [(e.label, e.xml_id, {"ref": e.ref, **e.extra, "kind": "bibl"})   for e in regs.get("bibl", [])],
    }

    def link_one(ent: Dict[str, Any]) -> Dict[str, Any]:
        text = ent.get("text", "")
        raw_label = _extract_label(ent)
        target_kind = LABEL_MAP.get(raw_label, "")
        start, end = _extract_span(ent)

        if not target_kind or not banks.get(target_kind):
            ent["links"] = {
                "register": None,
                "decision": {"method": "none", "score": 0.0, "candidates_considered": []},
            }
            return ent

        # fuzzy prefilter
        top_scored = _top_k_by_similarity(text, banks[target_kind], k=max(8, topk_for_llm))
        considered = [
            {"xml_id": xml_id, "label": lab, "score": float(score), **payload}
            for score, (lab, xml_id, payload) in top_scored
        ]

        # confident fuzzy match?
        if prefer_register and top_scored and top_scored[0][0] >= float(fuzzy_threshold):
            best_score, (lab, xml_id, payload) = top_scored[0]
            ent["links"] = {
                "register": {"kind": target_kind, "xml_id": xml_id, "ref": payload.get("ref")},
                "decision": {"method": "fuzzy", "score": float(best_score), "candidates_considered": considered},
            }
            return ent

        # otherwise ask LLM if available
        if saia_client is not None and considered:
            ctx = _context_window(letter_text, start, end, context_window) if start >= 0 and end >= 0 else ""
            # Build RegisterEntry-like objects for the prompt
            prompt_cands = []
            for score, (lab, xml_id, payload) in top_scored[:topk_for_llm]:
                prompt_cands.append(RegisterEntry(kind=target_kind, xml_id=xml_id, label=lab, ref=payload.get("ref"), extra={}))

            try:
                pick, conf = _ask_llm_pick(saia_client, ent, ctx, prompt_cands)
            except Exception as e:
                ent["links"] = {
                    "register": None,
                    "decision": {"method": "none", "score": 0.0, "candidates_considered": considered, "error": str(e)},
                }
                return ent

            if pick and pick.lower() != "none":
                payload_ref = None
                for c in considered:
                    if c.get("xml_id") == pick:
                        payload_ref = c.get("ref")
                        break
                ent["links"] = {
                    "register": {"kind": target_kind, "xml_id": pick, "ref": payload_ref},
                    "decision": {"method": "llm", "score": float(conf), "candidates_considered": considered},
                }
                return ent

        # no link
        ent["links"] = {
            "register": None,
            "decision": {"method": "none", "score": 0.0, "candidates_considered": considered},
        }
        return ent

    enriched_entities = [link_one(dict(e)) for e in entities]
    enriched_added    = [link_one(dict(e)) for e in added]

    result: Dict[str, Any] = dict(adjudicated) if isinstance(adjudicated, dict) else {"entities": enriched_entities}
    result["entities"] = enriched_entities
    if added:
        result["added_by_llm"] = enriched_added

    if suggestions_path:
        Path(suggestions_path).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    return result
