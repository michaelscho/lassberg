"""Smoke tests for the KI-Infrastruktur pipeline (Phase 8 acceptance criterion: one smoke test per
stage, run against small fixture letters, not the full corpus).

Phase 1 (parse_tei.py) is tested thoroughly against tests/fixtures/mini_repo/ (2 full-text
letters - one published with clean rs<->mentions links, one draft (no revisionDesc) with empty rs keys and a
commented-out mentions template - plus one register-only letter, mirroring the three real letter
states found in the actual corpus). Phases 4/5's small pure-function helpers (Cypher literal
escaping, RDF date-precision typing, the sent-place corpus-quirk fallback) are unit-tested
directly since they have no external-service dependency. Phases 2/3/6/7 were validated manually
against the real corpus (see PLAN_edition_ki_infrastruktur.md's acceptance-criteria walkthrough
and tests/test_onnx_consistency.md) rather than in this fixture-based suite, since they require a
GPU-friendly model download, Docker services, or a browser - not suitable for a fast fixture test.

Run: python -m pytest tests/test_pipeline.py -v
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = Path(__file__).resolve().parent / "fixtures/mini_repo"

sys.path.insert(0, str(REPO_ROOT / "scripts"))

from parse_tei import (  # noqa: E402
    Warnings,
    bare_id,
    build_letters_jsonl,
    build_manifest,
    date_precision,
    parse_registers,
)
from lib_pipeline import (  # noqa: E402
    ENTITY_PROPERTY_BUILDERS,
    effective_sent_place,
    entity_relationships,
    label_for_id,
    letter_properties,
)


@pytest.fixture
def entities():
    return parse_registers(FIXTURE_ROOT / "data/register", Warnings())


@pytest.fixture
def letters(entities):
    return build_letters_jsonl(FIXTURE_ROOT, entities, Warnings())


def test_registers_parse_all_entity_types(entities):
    assert set(entities["persons"].keys()) == {
        "lassberg-correspondent-0001", "lassberg-correspondent-0002", "lassberg-correspondent-0003",
    }
    assert entities["persons"]["lassberg-correspondent-0003"]["kind"] == "personGrp"
    assert entities["places"]["lassberg-place-0001"]["coords"] == {"lat": 47.5, "lon": 9.2}
    assert entities["works"]["lassberg-literature-0001"]["label"] == "Testwerk"
    assert entities["witnesses"]["lassberg-witness-0001"]["corresp"] == "lassberg-literature-0002"

    sender = entities["persons"]["lassberg-correspondent-0001"]
    assert sender["birth"] == "1780"
    assert sender["death"] == "1850"
    assert entities["persons"]["lassberg-correspondent-0002"]["birth"] is None  # <birth when=""/>


def test_full_metadata_flows_through_to_property_builders(entities):
    """The full-representation fields (person_type, birth/death, occupation, register_meta, ...)
    must survive scripts/lib_pipeline.py's property builders unchanged - these are what actually
    ends up in Neo4j/RDF/graph.json, so a regression here would silently impoverish all three."""
    props = ENTITY_PROPERTY_BUILDERS["persons"](entities["persons"]["lassberg-correspondent-0001"])
    assert props["person_type"] == "contemporary"
    assert props["gender"] == "male"
    assert props["birth"] == "1780"
    assert props["death"] == "1850"
    assert props["occupation"] == ["Gelehrter"]

    work_props = ENTITY_PROPERTY_BUILDERS["works"](entities["works"]["lassberg-literature-0001"])
    assert work_props["lit_type"] == "historicalSource"
    assert work_props["idno"] == ["varia:-"]  # fixture work's placeholder idno, still flattened as-is


def test_letters_jsonl_has_all_three_states(letters):
    by_id = {l["id"]: l for l in letters}
    assert set(by_id.keys()) == {"lassberg-letter-0001", "lassberg-letter-0002", "lassberg-letter-0003"}

    reviewed = by_id["lassberg-letter-0001"]
    assert reviewed["has_fulltext"] is True
    assert reviewed["status"] == "published"  # latest revisionDesc change entry
    assert reviewed["sent"] == {
        "person": "lassberg-correspondent-0001", "place": "lassberg-place-0001",
        "date": "1825-01-01", "date_precision": "day",
    }
    assert reviewed["mentions"]["works"] == ["lassberg-literature-0001"]
    assert "normalisiert" in reviewed["text"]  # prefers the normalized div over the transcription
    assert reviewed["publication_status"] == "online_transcription"
    assert reviewed["register_meta"]["harris_number"] == "42"
    assert reviewed["register_meta"]["repository_place"] == "Testarchivstadt"
    assert reviewed["register_meta"]["published_in_url"] == "https://example.com/pub"
    assert reviewed["register_meta"]["journal_number"] is None  # empty <note> -> None, not ""

    raw = by_id["lassberg-letter-0002"]
    assert raw["status"] == "draft"  # no <revisionDesc> in the fixture -> defaults to draft
    assert raw["mentions"] == {"persons": [], "places": [], "works": [], "witnesses": []}
    assert "unbekannte Buch" in raw["text"]  # falls back to the transcription div (no normalized one)

    register_only = by_id["lassberg-letter-0003"]
    assert register_only["has_fulltext"] is False
    assert register_only["status"] == "register-only"
    assert register_only["text"] is None
    assert register_only["sent"]["person"] == "lassberg-correspondent-0001"


def test_raw_letter_rs_mismatch_is_not_flagged_as_a_warning(entities):
    """The raw letter's <rs> tags are empty-keyed and its mentions-note is a commented-out
    template - both expected for unreviewed letters (docs/TEI.md) and must not trigger
    rs-mentioned-mismatch, which is reserved for reviewed letters."""
    warnings = Warnings()
    build_letters_jsonl(FIXTURE_ROOT, entities, warnings)
    assert "rs-mentioned-mismatch" not in warnings.counts


def test_manifest_covers_every_source_file():
    manifest = build_manifest(FIXTURE_ROOT)
    assert len(manifest) == 2 + 5  # 2 letters + 5 register files
    assert all(len(sha) == 64 for sha in manifest.values())  # sha256 hex digest length


def test_bare_id_normalizes_relative_and_bare_forms():
    assert bare_id("../register/lassberg-persons.xml#lassberg-correspondent-0179") == "lassberg-correspondent-0179"
    assert bare_id("lassberg-correspondent-0179") == "lassberg-correspondent-0179"
    assert bare_id("") is None
    assert bare_id(None) is None


def test_date_precision():
    assert date_precision("1825-01-01") == "day"
    assert date_precision("1825-01") == "month"
    assert date_precision("1825") == "year"
    assert date_precision(None) is None


def test_effective_sent_place_fallback():
    with_sent_place = {"sent": {"place": "place-A"}, "received": {"place": "place-B"}}
    assert effective_sent_place(with_sent_place) == "place-A"

    quirk_case = {"sent": {"place": None}, "received": {"place": "place-B"}}
    assert effective_sent_place(quirk_case) == "place-B"

    neither = {"sent": {"place": None}, "received": {"place": None}}
    assert effective_sent_place(neither) is None


def test_export_cypher_literal_escaping():
    from export_cypher import cypher_literal

    assert cypher_literal("O'Brien") == "'O\\'Brien'"
    assert cypher_literal(True) == "true"
    assert cypher_literal(42) == "42"


def test_export_rdf_date_literal_typing():
    from rdflib import XSD
    from export_rdf import date_literal

    assert date_literal("1825-01-01", "day").datatype == XSD.date
    assert date_literal("1825-01", "month").datatype == XSD.gYearMonth
    assert date_literal("1825", "year").datatype == XSD.gYear


def test_entity_relationships_only_emitted_for_linked_ids(entities):
    """lassberg-literature-0001's author/pubPlace both have key="" (unlinked, per docs/TEI.md's
    "leave empty rather than guess" convention) and must NOT produce a relationship; only the
    fixture's -0002 work (linked author/pubPlace) and its witness should."""
    rels = entity_relationships(entities)
    rel_tuples = {(r["type"], r["source"], r["target"]) for r in rels}
    assert rel_tuples == {
        ("AUTHORED_BY", "lassberg-literature-0002", "lassberg-correspondent-0001"),
        ("PUBLISHED_AT", "lassberg-literature-0002", "lassberg-place-0001"),
        ("WITNESS_OF", "lassberg-witness-0001", "lassberg-literature-0002"),
    }


def test_label_for_id():
    assert label_for_id("lassberg-correspondent-0001") == "Person"
    assert label_for_id("lassberg-place-0001") == "Place"
    assert label_for_id("lassberg-literature-0002") == "Work"
    assert label_for_id("lassberg-witness-0001") == "Witness"
    with pytest.raises(ValueError):
        label_for_id("not-a-real-id")


def test_letter_properties_includes_register_meta_and_fulltext(letters):
    by_id = {l["id"]: l for l in letters}
    props = letter_properties(by_id["lassberg-letter-0001"])
    assert props["harris_number"] == "42"
    assert props["publication_status"] == "online_transcription"
    assert "normalisiert" in props["text"]  # full text present for the has_fulltext letter

    register_only_props = letter_properties(by_id["lassberg-letter-0003"])
    assert "text" not in register_only_props  # no fulltext -> dropped, not text: None


def test_letters_jsonl_round_trips_as_json(letters):
    # every record must be JSON-serializable as-is (this is what actually gets written to
    # build/letters.jsonl, one json.dumps() per line)
    for letter in letters:
        json.loads(json.dumps(letter, ensure_ascii=False))
