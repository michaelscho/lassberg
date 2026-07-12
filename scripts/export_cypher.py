#!/usr/bin/env python3
"""
Phase 4 of the KI-Infrastruktur pipeline: generates `graph/import.cypher`, a portable, idempotent
Cypher script (pure MERGE, safe to run any number of times) that recreates the correspondence
network in Neo4j from the JSON intermediate layer.

Data model (docs in PLAN_edition_ki_infrastruktur.md, Phase 4, extended 2026-07-11 to carry the
entity registers' full metadata instead of only id/label - see scripts/lib_pipeline.py's
person_properties/place_properties/work_properties/witness_properties for the exact per-type
field list, shared with export_rdf.py and export_graph_json.py so all three runtimes match):

  (:Letter {id, date, incipit?, text?, file?, has_fulltext, status, lang?, publication_status?,
             harris_number?, journal_number?, repository_place?, repository_institution?,
             signature?, facsimile_url?, published_in?, published_in_url?, comment?,
             iiif_manifest?, iiif_canvas?})
  (:Person {id, label, kind, person_type?, gender?, corporate_body, gnd?, wikidata?, url?,
             occupation?, education?})
  (:Place  {id, label, wikidata?, gnd?, url?, desc?, lat?, lon?})
  (:Work   {id, label, lit_type?, ana?, date?, idno?, author_label?, pub_place_label?})
  (:Witness{id, label, witness_type?, settlement?, repository?, signature?, note?})

  (l:Letter)-[:SENT_BY]->(p:Person)     - from all 3268 register letters
  (l:Letter)-[:SENT_TO]->(p:Person)     - from all 3268 register letters
  (l:Letter)-[:SENT_FROM]->(pl:Place)   - from all 3268 register letters (see
                                           lib_pipeline.effective_sent_place for a corpus quirk
                                           fallback)
  (l:Letter)-[:MENTIONS]->(p|pl|w|wit)  - only for the ~170 full-text letters
  (w:Work)-[:AUTHORED_BY]->(p:Person)   - only when the work's <author> links a register id
  (w:Work)-[:PUBLISHED_AT]->(pl:Place)  - only when the work's <pubPlace> links a register id
  (wit:Witness)-[:WITNESS_OF]->(w:Work) - only when the witness's @corresp links a register id

For a faster bulk import, use `scripts/import_neo4j.py` (UNWIND-batched via the Python driver)
instead of piping this file through cypher-shell - this file exists as a portable, tool-agnostic
artifact (and for documentation/inspection), not as the primary import path.

Usage:
    python scripts/export_cypher.py [--repo-root PATH] [--batch-size 500]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_pipeline import (  # noqa: E402
    ENTITY_PROPERTY_BUILDERS,
    effective_sent_place,
    entity_relationships,
    label_for_id,
    letter_properties,
    load_entities,
    load_letters,
)

LABELS = {"persons": "Person", "places": "Place", "works": "Work", "witnesses": "Witness"}


def cypher_literal(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(cypher_literal(v) for v in value) + "]"
    text = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{text}'"


def set_clause(var: str, props: dict) -> str:
    parts = [f"{var}.{k} = {cypher_literal(v)}" for k, v in props.items() if v is not None]
    return "SET " + ", ".join(parts) if parts else ""


class BatchWriter:
    """Wraps statements in cypher-shell :begin/:commit blocks of `batch_size` statements each."""

    def __init__(self, fh, batch_size: int):
        self.fh = fh
        self.batch_size = batch_size
        self.count = 0

    def write(self, statement: str):
        if self.count % self.batch_size == 0:
            if self.count > 0:
                self.fh.write(":commit\n\n")
            self.fh.write(":begin\n")
        self.fh.write(statement + ";\n")
        self.count += 1

    def close(self):
        if self.count > 0:
            self.fh.write(":commit\n")


def write_constraints(fh):
    fh.write("// Constraints - run once, idempotent via IF NOT EXISTS\n")
    for label in ("Letter", "Person", "Place", "Work", "Witness"):
        fh.write(
            f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
            f"FOR (n:{label}) REQUIRE n.id IS UNIQUE;\n"
        )
    fh.write("\n")


def write_entities(writer: BatchWriter, entities: dict):
    for bucket, label in LABELS.items():
        build_props = ENTITY_PROPERTY_BUILDERS[bucket]
        for eid, ent in entities[bucket].items():
            props = build_props(ent)
            writer.write(f"MERGE (n:{label} {{id: {cypher_literal(eid)}}}) {set_clause('n', props)}")


def write_letters(writer: BatchWriter, letters: list[dict]):
    for letter in letters:
        props = letter_properties(letter)
        writer.write(f"MERGE (l:Letter {{id: {cypher_literal(letter['id'])}}}) {set_clause('l', props)}")


def write_relationships(writer: BatchWriter, letters: list[dict]):
    for letter in letters:
        lid = cypher_literal(letter["id"])
        sent_person = letter["sent"]["person"]
        recv_person = letter["received"]["person"]
        place = effective_sent_place(letter)

        if sent_person:
            writer.write(
                f"MATCH (l:Letter {{id: {lid}}}), (p:Person {{id: {cypher_literal(sent_person)}}}) "
                f"MERGE (l)-[:SENT_BY]->(p)"
            )
        if recv_person:
            writer.write(
                f"MATCH (l:Letter {{id: {lid}}}), (p:Person {{id: {cypher_literal(recv_person)}}}) "
                f"MERGE (l)-[:SENT_TO]->(p)"
            )
        if place:
            writer.write(
                f"MATCH (l:Letter {{id: {lid}}}), (pl:Place {{id: {cypher_literal(place)}}}) "
                f"MERGE (l)-[:SENT_FROM]->(pl)"
            )
        for bucket, label in LABELS.items():
            for eid in letter["mentions"][bucket]:
                writer.write(
                    f"MATCH (l:Letter {{id: {lid}}}), (n:{label} {{id: {cypher_literal(eid)}}}) "
                    f"MERGE (l)-[:MENTIONS]->(n)"
                )


def write_entity_relationships(writer: BatchWriter, entities: dict):
    for rel in entity_relationships(entities):
        source_label = label_for_id(rel["source"])
        target_label = label_for_id(rel["target"])
        writer.write(
            f"MATCH (a:{source_label} {{id: {cypher_literal(rel['source'])}}}), "
            f"(b:{target_label} {{id: {cypher_literal(rel['target'])}}}) "
            f"MERGE (a)-[:{rel['type']}]->(b)"
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    entities = load_entities(repo_root)
    letters = load_letters(repo_root)
    extra_rels = entity_relationships(entities)

    graph_dir = repo_root / "graph"
    graph_dir.mkdir(exist_ok=True)
    out_path = graph_dir / "import.cypher"

    n_entities = sum(len(v) for v in entities.values())
    n_rels = len(extra_rels)
    for letter in letters:
        n_rels += sum(1 for p in (letter["sent"]["person"], letter["received"]["person"], effective_sent_place(letter)) if p)
        n_rels += sum(len(letter["mentions"][b]) for b in LABELS)

    with out_path.open("w", encoding="utf-8") as fh:
        write_constraints(fh)
        writer = BatchWriter(fh, args.batch_size)
        fh.write("// Entity nodes\n")
        write_entities(writer, entities)
        write_letters(writer, letters)
        write_relationships(writer, letters)
        write_entity_relationships(writer, entities)
        writer.close()

    print(f"Wrote graph/import.cypher: {len(letters)} letters, {n_entities} entities, {n_rels} relationships "
          f"({len(extra_rels)} of which are AUTHORED_BY/PUBLISHED_AT/WITNESS_OF)")


if __name__ == "__main__":
    main()
