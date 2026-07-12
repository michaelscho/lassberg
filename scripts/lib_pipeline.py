"""Shared helpers for the export stages (Neo4j, RDF, graph.json, MCP tools) that all read the
same `build/` JSON intermediate layer produced by parse_tei.py. Kept dependency-free (stdlib +
yaml only) so every export script can import it without pulling in torch/umap/etc.
"""
from __future__ import annotations

import json
from pathlib import Path


def load_config(repo_root: Path) -> dict:
    import yaml
    with (repo_root / "config.yaml").open() as fh:
        return yaml.safe_load(fh)


def load_letters(repo_root: Path) -> list[dict]:
    """Returns all letters (register-only and full-text), sorted by id."""
    letters = []
    with (repo_root / "build/letters.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            letters.append(json.loads(line))
    letters.sort(key=lambda r: r["id"])
    return letters


def load_entities(repo_root: Path) -> dict:
    """Returns {"persons": {...}, "places": {...}, "works": {...}, "witnesses": {...}}."""
    return json.loads((repo_root / "build/entities.json").read_text(encoding="utf-8"))


def flatten_entities(entities: dict) -> dict:
    """Returns a single {id: entity} dict across all four registers, for O(1) lookups by id."""
    flat = {}
    for bucket in entities.values():
        flat.update(bucket)
    return flat


def flatten_idno(idno_list: list[dict]) -> list[str]:
    """Flattens a work/witness's `idno` list (`[{"type": "vd18", "value": "VD18-..."}]`) into
    `["vd18:VD18-..."]` strings, since Neo4j/RDF properties can't hold nested objects. Entries
    with no value (or type) are dropped rather than emitted as "None:None".
    """
    return [f"{i['type']}:{i['value']}" for i in idno_list if i.get("type") and i.get("value")]


def letter_properties(letter: dict) -> dict:
    """Full Letter node/resource property set, including the register_meta fields (Harris number,
    archival signature, published-in citation, IIIF links) that only exist in the overall register
    (lassberg-letters.xml) - not per-file for individual TEI letters, see
    parse_tei.py:parse_register_notes. `text` is included so the full-text letters' text is
    directly queryable in Neo4j/RDF without a separate JSON-file lookup, not just the `incipit`."""
    meta = letter.get("register_meta") or {}
    return _drop_empty({
        "date": letter["sent"]["date"] or letter["received"]["date"],
        "incipit": letter["incipit"],
        "text": letter["text"],
        "file": letter["file"],
        "has_fulltext": letter["has_fulltext"],
        "status": letter["status"],
        "lang": letter["lang"],
        "publication_status": letter.get("publication_status"),
        "harris_number": meta.get("harris_number"),
        "journal_number": meta.get("journal_number"),
        "repository_place": meta.get("repository_place"),
        "repository_institution": meta.get("repository_institution"),
        "signature": meta.get("signature"),
        "facsimile_url": meta.get("facsimile_url"),
        "published_in": meta.get("published_in"),
        "published_in_url": meta.get("published_in_url"),
        "comment": meta.get("comment"),
        "iiif_manifest": meta.get("iiif_manifest"),
        "iiif_canvas": meta.get("iiif_canvas"),
    })


def effective_sent_place(letter: dict) -> str | None:
    """The place a letter was sent from.

    Normally `letter["sent"]["place"]`. Falls back to `letter["received"]["place"]` because of a
    known corpus quirk (see parse_tei.py:build_letters_jsonl, warning category
    "place-under-received"): in ~82/170 fulltext letters, <placeName> ended up nested under
    <correspAction type="received"> instead of type="sent", even though docs/TEI.md defines
    placeName as the departure place regardless of which correspAction wraps it. Without this
    fallback, ~48% of fulltext letters would be missing a SENT_FROM place entirely.
    """
    return letter["sent"]["place"] or letter["received"]["place"]


# --------------------------------------------------------------------------------------------
# Entity property/relationship mapping, shared by scripts/export_cypher.py, import_neo4j.py,
# export_rdf.py, and export_graph_json.py so the three parallel runtimes (Neo4j/RDF/browser
# graph.json) stay in sync - "one modelling, three runtimes", never four independent field lists.
# --------------------------------------------------------------------------------------------

def _drop_empty(props: dict) -> dict:
    return {k: v for k, v in props.items() if v not in (None, [], "")}


def person_properties(ent: dict) -> dict:
    """Full property set for a person/personGrp entity (Neo4j/RDF property values must be
    primitives or arrays of primitives, so nothing here is a nested object)."""
    return _drop_empty({
        "label": ent["label"],
        "kind": ent["kind"],  # "person" | "personGrp"
        "person_type": ent.get("person_type"),  # "contemporary" | "historical"
        "gender": ent.get("gender"),
        "corporate_body": ent["corporate_body"],
        "gnd": ent["normdaten"].get("gnd"),
        "wikidata": ent["normdaten"].get("wikidata"),
        "url": ent["normdaten"].get("other"),
        "occupation": ent.get("occupation") or None,
        "education": ent.get("education") or None,
        "birth": ent.get("birth"),
        "death": ent.get("death"),
    })


def place_properties(ent: dict) -> dict:
    props = _drop_empty({
        "label": ent["label"],
        "wikidata": ent["normdaten"].get("wikidata"),
        "gnd": ent["normdaten"].get("gnd"),
        "url": ent["normdaten"].get("other"),
        "desc": ent.get("desc"),
    })
    if ent.get("coords"):
        props["lat"] = ent["coords"]["lat"]
        props["lon"] = ent["coords"]["lon"]
    return props


def work_properties(ent: dict) -> dict:
    """Author/pub_place become AUTHORED_BY/PUBLISHED_AT relationships (see entity_relationships())
    when linked to a register id; the free-text label is kept as a property only when there's no
    linked id to relate to (unlinked author/pubPlace, key="")."""
    author = ent.get("author")
    pub_place = ent.get("pub_place")
    return _drop_empty({
        "label": ent["label"],
        "lit_type": ent.get("lit_type"),
        "ana": ent.get("ana"),
        "date": ent.get("date"),
        "idno": flatten_idno(ent.get("idno") or []),
        "author_label": author["label"] if author and not author.get("key") else None,
        "pub_place_label": pub_place["label"] if pub_place and not pub_place.get("key") else None,
    })


def witness_properties(ent: dict) -> dict:
    """`corresp` becomes a WITNESS_OF relationship (see entity_relationships()), not a property."""
    return _drop_empty({
        "label": ent["label"],
        "witness_type": ent.get("witness_type"),
        "settlement": ent.get("settlement"),
        "repository": ent.get("repository"),
        "signature": ent.get("signature"),
        "note": ent.get("note"),
    })


ENTITY_PROPERTY_BUILDERS = {
    "persons": person_properties,
    "places": place_properties,
    "works": work_properties,
    "witnesses": witness_properties,
}


LABEL_BY_ID_PREFIX = {  # entity id prefix -> Neo4j node label / RDF entity "kind" path segment
    "lassberg-correspondent-": "Person",
    "lassberg-place-": "Place",
    "lassberg-literature-": "Work",
    "lassberg-witness-": "Witness",
}


def label_for_id(entity_id: str) -> str:
    for prefix, label in LABEL_BY_ID_PREFIX.items():
        if entity_id.startswith(prefix):
            return label
    raise ValueError(f"Cannot infer entity label for id: {entity_id}")


def entity_relationships(entities: dict) -> list[dict]:
    """Entity-to-entity relationships beyond the letter-centric ones (SENT_BY/SENT_TO/SENT_FROM/
    MENTIONS, which are per-letter and built separately by each exporter). Currently:
    Work-AUTHORED_BY->Person, Work-PUBLISHED_AT->Place, Witness-WITNESS_OF->Work. Only emitted
    when the source register actually links to a real register id - never invented, per
    docs/TEI.md's "leave key/corresp empty rather than guess" convention.

    Returns [{"type": ..., "source": <id>, "target": <id>}, ...].
    """
    rels = []
    for work_id, work in entities["works"].items():
        author = work.get("author")
        if author and author.get("key"):
            rels.append({"type": "AUTHORED_BY", "source": work_id, "target": author["key"]})
        pub_place = work.get("pub_place")
        if pub_place and pub_place.get("key"):
            rels.append({"type": "PUBLISHED_AT", "source": work_id, "target": pub_place["key"]})
    for witness_id, witness in entities["witnesses"].items():
        if witness.get("corresp"):
            rels.append({"type": "WITNESS_OF", "source": witness_id, "target": witness["corresp"]})
    return rels
