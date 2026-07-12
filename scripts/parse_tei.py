#!/usr/bin/env python3
"""
Phase 1 of the KI-Infrastruktur pipeline: parses the TEI letters (`data/letters/`) and TEI
registers (`data/register/`) into a JSON intermediate layer that every downstream stage
(embeddings, clustering, Neo4j, RDF, MCP, frontend) reads instead of TEI directly.

Output (all under `build/`):
  letters.jsonl   - one JSON object per line, one line per letter in the overall register
                    (all 3268; has_fulltext=true only for the ~170 with a TEI file in data/letters/)
  entities.json   - persons, places, literary works/editions, manuscript witnesses, keyed by id
  manifest.json   - {relative source path: sha256} of every source file read, for change
                    detection by later stages
  warnings.log    - non-fatal issues found while parsing (missing register refs, empty keys, ...)

--- TEI encoding mapping (verified against docs/TEI.md + lassberg-letter-0952.xml/-1044.xml, and
    all four register files that matter, on 2026-07-11 -- see CLAUDE.md/docs/TEI.md for the full
    prose spec; this is the condensed "what the code below actually relies on") ---

Register cross-references:
  - Inside a *letter* TEI file, `@key` on <persName>/<placeName>/<rs> points at a register entry
    as a RELATIVE PATH + FRAGMENT, e.g. "../register/lassberg-persons.xml#lassberg-correspondent-0179".
    We normalize to the bare fragment id ("lassberg-correspondent-0179"); empty/missing key/target
    stays as None (never invent an id).
  - Inside the *overall* register `lassberg-letters.xml`, the same references are already bare ids
    in `@key` (no path, no fragment), e.g. key="lassberg-correspondent-0179".
  - `@ref` (not `@key`) carries the external authority URL (GND / Wikidata / Wikipedia); may be "".
  - `<note type="mentioned">` (letter-level) uses `<ref type="cmif:mentions{Person,Place,Bibl}"
    target="...">` - target uses the same relative-path+fragment convention as `@key`.

Four <div> versions per letter body (only the transcription carries <rs> markup), identified by
content (presence of <rs>), not solely by @type - but @type/@resp are still meaningful:
  - type="original" resp="#transkribus #MiS"  -> diplomatic transcription of the MS itself
  - type="print"    resp="ocr"                -> OCR'd from a printed edition (no <lb>)
  - type="normalized" resp="GPT3.5"/"#GPT4"   -> modernized plain text, no <rs> (preferred `text`)
  - type="translation" / type="summary" resp="#GPT4" -> never used for `text`

`<rs>` @type -> target register (docs/TEI.md "Zusammenfassung"-Tabelle):
  person -> lassberg-persons.xml | place -> lassberg-places.xml | bibl -> lassberg-literature.xml
  | witness -> lassberg-manuscripts.xml | object/misc -> no register, key is always ""

Registers actually parsed (lassberg-objects.xml is intentionally ignored, per CLAUDE.md/plan):
  - lassberg-persons.xml:    <person> and <personGrp> (family/noble-house collectives);
                              @gender="CorporateBody" marks an institution, still filed as "person".
  - lassberg-places.xml:     <place><placeName ref="wikidata-url">, <geo ana="wgs84">lat,lon</geo>
  - lassberg-literature.xml: <bibl xml:id=... type="contemporaryPublication|historicalSource|unknown">
  - lassberg-manuscripts.xml:<witness xml:id=... type="manuscript|print" corresp="...literature...">

`<revisionDesc>` presence = manual-markup indicator (docs/TEI.md); its absence means a raw,
pipeline-only letter (many empty rs/@key="").

File selection: `data/letters/lassberg-letter-*.xml`, excluding anything with "_old" in the name
(3 such files exist) and non-letter files that happen to live in the same directory.

Usage:
    python scripts/parse_tei.py [--repo-root PATH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from lxml import etree

NS = {"tei": "http://www.tei-c.org/ns/1.0"}


def tei(tag: str) -> str:
    return f"{{{NS['tei']}}}{tag}"


def norm_ws(text: str | None) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def text_content(el: etree._Element | None) -> str:
    if el is None:
        return ""
    return norm_ws("".join(el.itertext()))


def bare_id(ref: str | None) -> str | None:
    """Normalize a @key/@target value to the bare register id.

    Letter-level refs look like '../register/lassberg-persons.xml#lassberg-correspondent-0179';
    the overall register (lassberg-letters.xml) already stores bare ids with no '#'. Empty/missing
    values are treated as "not linked" (never invented).
    """
    if not ref:
        return None
    ref = ref.strip()
    if not ref:
        return None
    if "#" in ref:
        return ref.rsplit("#", 1)[1] or None
    return ref


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def date_precision(when: str | None) -> str | None:
    if not when:
        return None
    when = when.strip()
    if len(when) == 10:
        return "day"
    if len(when) == 7:
        return "month"
    if len(when) == 4:
        return "year"
    return None


class Warnings:
    def __init__(self):
        self.lines: list[str] = []
        self.counts: dict[str, int] = {}

    def add(self, category: str, message: str):
        self.counts[category] = self.counts.get(category, 0) + 1
        self.lines.append(f"[{category}] {message}")

    def write(self, path: Path):
        path.write_text("\n".join(self.lines) + ("\n" if self.lines else ""), encoding="utf-8")


# --------------------------------------------------------------------------------------------
# Register parsing -> entities.json
# --------------------------------------------------------------------------------------------

def parse_ref_normdaten(ref: str | None, entity_id: str = "", warnings: Warnings | None = None) -> dict:
    """Classify an @ref authority URL into gnd/wikidata/other. A handful of place entries use a
    "-" placeholder here instead of leaving @ref empty (same convention as idno/published_in
    elsewhere in the corpus) - treated as absent rather than passed through as a fake "other" URL,
    which would otherwise break RDF export (owl:sameAs/rdfs:seeAlso need a real IRI)."""
    out = {"gnd": None, "wikidata": None, "other": None}
    if not ref:
        return out
    ref = ref.strip()
    if not ref:
        return out
    if "d-nb.info/gnd" in ref:
        out["gnd"] = ref
    elif "wikidata.org" in ref:
        out["wikidata"] = ref
    elif ref.startswith("http://") or ref.startswith("https://"):
        out["other"] = ref
    elif warnings is not None:
        warnings.add("invalid-url-ref", f"{entity_id}: @ref is not a URL, dropped: {ref!r}")
    return out


def parse_persons(path: Path, warnings: Warnings) -> dict:
    tree = etree.parse(str(path))
    root = tree.getroot()
    persons = {}
    for el in root.iter():
        if el.tag not in (tei("person"), tei("personGrp")):
            continue
        xml_id = el.get("{http://www.w3.org/XML/1998/namespace}id")
        if not xml_id:
            warnings.add("persons-missing-id", f"<{el.tag}> without xml:id in {path.name}")
            continue
        persname = el.find(tei("persName") + "[@type='main']")
        if persname is None:
            persname = el.find(tei("persName"))
        label = text_content(persname) if persname is not None else text_content(el)
        ref = el.get("ref")
        normdaten = parse_ref_normdaten(ref, xml_id, warnings)
        # extra <ref target="..."> children (e.g. Wikipedia) not already captured as @ref
        for ref_el in el.findall(tei("ref")):
            target = ref_el.get("target") or text_content(ref_el)
            target = target.strip() if target else None
            if target and normdaten["other"] is None and target != ref:
                if target.startswith("http://") or target.startswith("https://"):
                    normdaten["other"] = target
                else:
                    warnings.add("invalid-url-ref", f"{xml_id}: <ref> target/text is not a URL, dropped: {target!r}")
        gender = el.get("gender")
        birth_el = el.find(tei("birth"))
        death_el = el.find(tei("death"))
        persons[xml_id] = {
            "id": xml_id,
            "type": "person",
            "kind": "personGrp" if el.tag == tei("personGrp") else "person",
            "label": label,
            "person_type": el.get("type"),  # contemporary|historical
            "gender": gender,
            "corporate_body": gender == "CorporateBody",
            "normdaten": normdaten,
            "occupation": [norm_ws(o.text) for o in el.findall(tei("occupation")) if norm_ws(o.text)],
            "education": [norm_ws(e.text) for e in el.findall(tei("education")) if norm_ws(e.text)],
            "birth": (birth_el.get("when") or None) if birth_el is not None else None,
            "death": (death_el.get("when") or None) if death_el is not None else None,
        }
    return persons


def parse_places(path: Path, warnings: Warnings) -> dict:
    tree = etree.parse(str(path))
    root = tree.getroot()
    places = {}
    for el in root.iter(tei("place")):
        xml_id = el.get("{http://www.w3.org/XML/1998/namespace}id")
        if not xml_id:
            warnings.add("places-missing-id", f"<place> without xml:id in {path.name}")
            continue
        placename = el.find(tei("placeName"))
        label = text_content(placename) if placename is not None else ""
        ref = placename.get("ref") if placename is not None else None
        normdaten = parse_ref_normdaten(ref, xml_id, warnings)
        geo = el.find(f"{tei('location')}/{tei('geo')}")
        coords = None
        if geo is not None and geo.text and "," in geo.text:
            try:
                lat_s, lon_s = geo.text.strip().split(",", 1)
                coords = {"lat": float(lat_s), "lon": float(lon_s)}
            except ValueError:
                warnings.add("places-bad-geo", f"{xml_id}: unparseable geo '{geo.text}'")
        desc = el.find(tei("desc"))
        places[xml_id] = {
            "id": xml_id,
            "type": "place",
            "label": label,
            "normdaten": normdaten,
            "coords": coords,
            "desc": text_content(desc) or None,
        }
    return places


def parse_literature(path: Path, warnings: Warnings) -> dict:
    tree = etree.parse(str(path))
    root = tree.getroot()
    works = {}
    for el in root.iter():
        if el.tag not in (tei("bibl"), tei("biblStruct")):
            continue
        xml_id = el.get("{http://www.w3.org/XML/1998/namespace}id")
        if not xml_id:
            continue  # template/comment fragments etc. without an id are not real entries
        title = el.find(tei("title"))
        author = el.find(tei("author"))
        pub_place = el.find(tei("pubPlace"))
        date_el = el.find(tei("date"))
        idno = [
            {"type": i.get("type"), "value": norm_ws(i.text)}
            for i in el.findall(tei("idno"))
        ]
        works[xml_id] = {
            "id": xml_id,
            "type": "work",
            "label": text_content(title) or text_content(el),
            "lit_type": el.get("type"),  # contemporaryPublication|historicalSource|unknown
            "ana": el.get("ana"),  # e.g. needs-review, projected
            "author": {
                "key": bare_id(author.get("key")),
                "label": text_content(author),
            } if author is not None else None,
            "pub_place": {
                "key": bare_id(pub_place.get("key")),
                "label": text_content(pub_place),
            } if pub_place is not None else None,
            "date": text_content(date_el) or None,
            "idno": idno,
        }
    return works


def parse_manuscripts(path: Path, warnings: Warnings) -> dict:
    tree = etree.parse(str(path))
    root = tree.getroot()
    witnesses = {}
    for el in root.iter(tei("witness")):
        xml_id = el.get("{http://www.w3.org/XML/1998/namespace}id")
        if not xml_id:
            continue
        bibl = el.find(tei("bibl"))
        settlement = bibl.find(tei("settlement")) if bibl is not None else None
        repository = bibl.find(tei("repository")) if bibl is not None else None
        signature = bibl.find(tei("idno") + "[@type='signature']") if bibl is not None else None
        note = bibl.find(tei("note")) if bibl is not None else None
        witnesses[xml_id] = {
            "id": xml_id,
            "type": "witness",
            "witness_type": el.get("type"),  # manuscript|print
            "corresp": bare_id(el.get("corresp")),
            "settlement": text_content(settlement) or None,
            "repository": text_content(repository) or None,
            "signature": text_content(signature) or None,
            "note": text_content(note) or None,
        }
    return witnesses


def parse_registers(register_dir: Path, warnings: Warnings) -> dict:
    entities = {
        "persons": parse_persons(register_dir / "lassberg-persons.xml", warnings),
        "places": parse_places(register_dir / "lassberg-places.xml", warnings),
        "works": parse_literature(register_dir / "lassberg-literature.xml", warnings),
        "witnesses": parse_manuscripts(register_dir / "lassberg-manuscripts.xml", warnings),
    }
    return entities


# --------------------------------------------------------------------------------------------
# Letters parsing -> letters.jsonl
# --------------------------------------------------------------------------------------------

def _valid_url_or_none(value: str | None, field: str, letter_id: str, warnings: Warnings) -> str | None:
    """Several `url_facsimile`/`published_in`/IIIF notes contain placeholder text ("-", "done")
    instead of a real URL or being left empty - real data-entry noise in the source TEI (167
    letters for published_in's @target alone). Downstream consumers (export_rdf.py in particular)
    would otherwise choke trying to serialize e.g. "<->" as an RDF IRI. Treat anything not
    starting with http(s):// as absent rather than guessing/fixing it, and log it once."""
    if not value:
        return None
    if value.startswith("http://") or value.startswith("https://"):
        return value
    warnings.add("invalid-url-note", f"{letter_id}: {field} is not a URL, dropped: {value!r}")
    return None


def parse_register_notes(cd: etree._Element, letter_id: str, warnings: Warnings) -> dict:
    """Flattens correspDesc's flat `<note type="...">` list (archival/citation metadata, only
    present in the overall register lassberg-letters.xml, not the individual letter files) into
    named fields. Empty notes (the common case for optional ones like journalnummer/
    url_facsimile/published_in) are omitted rather than stored as empty strings."""
    notes = {n.get("type"): n for n in cd.findall(tei("note")) if n.get("type")}

    def note_text(note_type: str) -> str | None:
        note = notes.get(note_type)
        return (text_content(note) or None) if note is not None else None

    def note_url(note_type: str) -> str | None:
        return _valid_url_or_none(note_text(note_type), note_type, letter_id, warnings)

    published_in = notes.get("published_in")
    published_in_target = published_in.get("target") if published_in is not None else None
    return {
        "harris_number": note_text("nummer_harris"),
        "journal_number": note_text("journalnummer"),
        "repository_place": note_text("aufbewahrungsort"),
        "repository_institution": note_text("aufbewahrungsinstitution"),
        "signature": note_text("signatur"),
        "facsimile_url": note_url("url_facsimile"),
        "published_in": note_text("published_in"),
        "published_in_url": _valid_url_or_none(published_in_target, "published_in_url", letter_id, warnings),
        "comment": note_text("comment"),
        "iiif_manifest": note_url("iiif_manifest"),
        "iiif_canvas": note_url("iiif_canvas"),
    }


def parse_overall_register(path: Path, warnings: Warnings) -> dict:
    """Parse lassberg-letters.xml: metadata for all 3268 letters."""
    tree = etree.parse(str(path))
    root = tree.getroot()
    letters = {}
    for cd in root.iter(tei("correspDesc")):
        letter_id = cd.get("key")
        if not letter_id:
            warnings.add("register-missing-key", "correspDesc without @key in lassberg-letters.xml")
            continue
        sent_action = cd.find(tei("correspAction") + "[@type='sent']")
        recv_action = cd.find(tei("correspAction") + "[@type='received']")
        letters[letter_id] = {
            "id": letter_id,
            "sent": parse_corresp_action(sent_action),
            "received": parse_corresp_action(recv_action),
            "publication_status": cd.get("change"),  # in_register|in_oxygen_done|online
            "register_meta": parse_register_notes(cd, letter_id, warnings),
        }
    return letters


def parse_corresp_action(action: etree._Element | None) -> dict:
    if action is None:
        return {"person": None, "place": None, "date": None, "date_precision": None}
    persname = action.find(tei("persName"))
    placename = action.find(tei("placeName"))
    date_el = action.find(tei("date"))
    when = date_el.get("when") if date_el is not None else None
    return {
        "person": bare_id(persname.get("key")) if persname is not None else None,
        "place": bare_id(placename.get("key")) if placename is not None else None,
        "date": when,
        "date_precision": date_precision(when),
    }


TRANSCRIPTION_TYPES = {"original", "print"}
EXCLUDE_INLINE_TAGS = {tei("fw"), tei("add")}


def extract_div_text(div: etree._Element) -> str:
    """Text content of a <div>, excluding <fw>/<add> (archival apparatus, not letter content)."""
    parts = []

    def walk(el):
        if el.tag in EXCLUDE_INLINE_TAGS:
            return
        if el.text:
            parts.append(el.text)
        for child in el:
            walk(child)
            if child.tail:
                parts.append(child.tail)

    walk(div)
    return norm_ws("".join(parts))


def parse_mentions(corresp_desc: etree._Element | None) -> dict:
    mentions = {"persons": [], "places": [], "works": [], "witnesses": []}
    if corresp_desc is None:
        return mentions
    note = corresp_desc.find(tei("note") + "[@type='mentioned']")
    if note is None:
        return mentions
    type_to_bucket = {
        "cmif:mentionsPerson": "persons",
        "cmif:mentionsPlace": "places",
    }
    for ref_el in note.findall(tei("ref")):
        ref_type = ref_el.get("type")
        target = bare_id(ref_el.get("target"))
        if not target:
            continue
        if ref_type == "cmif:mentionsBibl":
            # Disambiguate work vs. witness by id prefix (both use cmif:mentionsBibl per CMIF).
            bucket = "witnesses" if target.startswith("lassberg-witness-") else "works"
        else:
            bucket = type_to_bucket.get(ref_type)
        if bucket:
            mentions[bucket].append(target)
    return mentions


def letter_status(tree_root: etree._Element) -> str:
    revision = tree_root.find(f".//{tei('revisionDesc')}")
    return "reviewed" if revision is not None else "raw"


def parse_letter_file(path: Path, warnings: Warnings) -> dict:
    tree = etree.parse(str(path))
    root = tree.getroot()

    corresp_desc = root.find(f".//{tei('correspDesc')}")
    sent_action = corresp_desc.find(tei("correspAction") + "[@type='sent']") if corresp_desc is not None else None
    recv_action = corresp_desc.find(tei("correspAction") + "[@type='received']") if corresp_desc is not None else None

    sent = parse_corresp_action(sent_action)
    received = parse_corresp_action(recv_action)
    mentions = parse_mentions(corresp_desc)

    # rs-key sanity check against note[type=mentioned]: warn on divergence (docs/TEI.md, Phase 1
    # step 4) - only for the transcription div, which is the one carrying <rs>.
    rs_keys = set()
    text = None
    incipit = None
    for div in root.iter(tei("div")):
        div_type = div.get("type")
        has_rs = div.find(f".//{tei('rs')}") is not None
        if has_rs:
            for rs in div.iter(tei("rs")):
                k = bare_id(rs.get("key"))
                if k:
                    rs_keys.add(k)
                elif rs.get("key") == "":
                    pass  # expected placeholder for raw/unreviewed letters
        if div_type == "normalized" and text is None:
            text = extract_div_text(div)
        elif div_type in TRANSCRIPTION_TYPES and text is None:
            # fallback only used if no normalized div is present anywhere in the file
            pass

    if text is None:
        for div in root.iter(tei("div")):
            if div.get("type") in TRANSCRIPTION_TYPES:
                text = extract_div_text(div)
                break

    if text:
        incipit = text[:200]
    else:
        warnings.add("empty-fulltext", f"{path.name}: no usable <div> text found despite TEI file existing")

    status = letter_status(root)

    # rs-key sanity check against note[type=mentioned] (docs/TEI.md, Phase 1 step 4). Only
    # meaningful for "reviewed" letters: "raw" letters have <note type="mentioned"> still as a
    # commented-out placeholder template by design, so a mismatch there is expected noise, not a
    # data issue - checking anyway would flood warnings.log with ~85 non-actionable entries.
    if status == "reviewed":
        all_mentioned_ids = set(mentions["persons"]) | set(mentions["places"]) | set(mentions["works"]) | set(mentions["witnesses"])
        stray_rs = rs_keys - all_mentioned_ids
        if stray_rs:
            warnings.add(
                "rs-mentioned-mismatch",
                f"{path.name}: <rs> keys not present in <note type='mentioned'>: {sorted(stray_rs)}",
            )

    return {
        "sent": sent,
        "received": received,
        "mentions": mentions,
        "text": text,
        "incipit": incipit,
        "status": status,
    }


def collect_letter_files(letters_dir: Path) -> list[Path]:
    files = sorted(letters_dir.glob("lassberg-letter-*.xml"))
    return [f for f in files if "_old" not in f.name]


def build_letters_jsonl(repo_root: Path, entities: dict, warnings: Warnings) -> list[dict]:
    register_path = repo_root / "data/register/lassberg-letters.xml"
    letters_dir = repo_root / "data/letters"

    overall = parse_overall_register(register_path, warnings)
    letter_files = {f.stem: f for f in collect_letter_files(letters_dir)}

    all_entity_ids = set()
    for bucket in entities.values():
        all_entity_ids |= set(bucket.keys())

    records = []
    for letter_id in sorted(overall.keys()):
        reg_entry = overall[letter_id]
        file_path = letters_dir / f"{letter_id}.xml"
        has_fulltext = letter_id in letter_files

        record = {
            "id": letter_id,
            "file": f"data/letters/{letter_id}.xml" if has_fulltext else None,
            "has_fulltext": has_fulltext,
            "status": "register-only",
            "sha256": None,
            "sent": reg_entry["sent"],
            "received": reg_entry["received"],
            "mentions": {"persons": [], "places": [], "works": [], "witnesses": []},
            "text": None,
            "incipit": None,
            "lang": "de",
            "publication_status": reg_entry["publication_status"],
            "register_meta": reg_entry["register_meta"],
        }

        if has_fulltext:
            parsed = parse_letter_file(file_path, warnings)
            record["status"] = parsed["status"]
            record["sha256"] = sha256_file(file_path)
            # TEI file wins over the overall register for sent/received, per plan step 3.
            record["sent"] = parsed["sent"] if parsed["sent"]["person"] or parsed["sent"]["date"] else reg_entry["sent"]
            record["received"] = parsed["received"] if parsed["received"]["person"] else reg_entry["received"]
            record["mentions"] = parsed["mentions"]
            record["text"] = parsed["text"]
            record["incipit"] = parsed["incipit"]

        # Validation: refs without a matching register entry.
        for role in ("sent", "received"):
            person_id = record[role]["person"]
            if person_id and person_id not in entities["persons"]:
                warnings.add("dangling-person-ref", f"{letter_id}: {role} person '{person_id}' not in persons register")
            place_id = record[role]["place"]
            if place_id and place_id not in entities["places"]:
                warnings.add("dangling-place-ref", f"{letter_id}: {role} place '{place_id}' not in places register")
        for bucket, reg_key in (("persons", "persons"), ("places", "places"), ("works", "works"), ("witnesses", "witnesses")):
            for eid in record["mentions"][bucket]:
                if eid not in entities[reg_key]:
                    warnings.add("dangling-mention-ref", f"{letter_id}: mentions {bucket[:-1]} '{eid}' not in register")

        if not record["sent"]["date"] and not record["received"]["date"]:
            warnings.add("missing-date", f"{letter_id}: no date on sent or received action")

        # Known corpus quirk: in ~82/170 fulltext letters (mostly the Pupikofer side of the
        # Pupikofer-Laßberg correspondence), <placeName> ends up nested under
        # <correspAction type="received"> instead of type="sent", even though docs/TEI.md defines
        # placeName as "Absendeort des Briefes" (departure place) regardless of which
        # correspAction wraps it. We keep the raw sent/received split faithful to the source here
        # (no silent fixing) and only warn; downstream consumers that need "the place a letter was
        # sent from" should use sent.place, falling back to received.place - see
        # scripts/lib_pipeline.py:effective_sent_place().
        if not record["sent"]["place"] and record["received"]["place"]:
            warnings.add(
                "place-under-received",
                f"{letter_id}: placeName found under correspAction[received] instead of [sent] "
                f"('{record['received']['place']}') - likely encoding quirk, not a real destination place",
            )

        records.append(record)

    return records


# --------------------------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------------------------

def build_manifest(repo_root: Path) -> dict:
    manifest = {}
    letters_dir = repo_root / "data/letters"
    register_dir = repo_root / "data/register"

    for f in collect_letter_files(letters_dir):
        manifest[str(f.relative_to(repo_root))] = sha256_file(f)

    for name in (
        "lassberg-letters.xml",
        "lassberg-persons.xml",
        "lassberg-places.xml",
        "lassberg-literature.xml",
        "lassberg-manuscripts.xml",
    ):
        f = register_dir / name
        if f.exists():
            manifest[str(f.relative_to(repo_root))] = sha256_file(f)

    return manifest


# --------------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    build_dir = repo_root / "build"
    build_dir.mkdir(exist_ok=True)

    warnings = Warnings()

    print("Parsing registers...", file=sys.stderr)
    entities = parse_registers(repo_root / "data/register", warnings)
    for k, v in entities.items():
        print(f"  {k}: {len(v)} entries", file=sys.stderr)

    print("Parsing letters...", file=sys.stderr)
    letters = build_letters_jsonl(repo_root, entities, warnings)
    n_fulltext = sum(1 for l in letters if l["has_fulltext"])
    print(f"  {len(letters)} letters total, {n_fulltext} with full text", file=sys.stderr)

    print("Writing build/entities.json...", file=sys.stderr)
    (build_dir / "entities.json").write_text(
        json.dumps(entities, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print("Writing build/letters.jsonl...", file=sys.stderr)
    with (build_dir / "letters.jsonl").open("w", encoding="utf-8") as fh:
        for rec in letters:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print("Writing build/manifest.json...", file=sys.stderr)
    manifest = build_manifest(repo_root)
    (build_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    warnings.write(build_dir / "warnings.log")
    print(f"Wrote {len(warnings.lines)} warnings to build/warnings.log:", file=sys.stderr)
    for cat, count in sorted(warnings.counts.items(), key=lambda kv: -kv[1]):
        print(f"  {cat}: {count}", file=sys.stderr)


if __name__ == "__main__":
    main()
