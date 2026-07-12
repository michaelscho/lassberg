#!/usr/bin/env python3
"""
Phase 4 convenience import: loads the JSON intermediate layer directly into Neo4j via the Python
driver, batched with UNWIND (much faster than executing graph/import.cypher statement-by-statement
through cypher-shell). Idempotent - safe to rerun any number of times, converges to the same graph.

Requires a running Neo4j instance (see docker-compose.yml, `make graph` starts one).

Data model: see scripts/export_cypher.py's module docstring (this script produces the identical
graph, just via a faster bulk-import path).

Usage:
    python scripts/import_neo4j.py [--repo-root PATH] [--uri bolt://localhost:7687]
                                    [--user neo4j] [--password ...] [--batch-size 500]
Password: read from NEO4J_PASSWORD env var if --password is not given.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_pipeline import (  # noqa: E402
    ENTITY_PROPERTY_BUILDERS,
    effective_sent_place,
    entity_relationships,
    label_for_id,
    letter_properties,
    load_config,
    load_entities,
    load_letters,
)

LABELS = {"persons": "Person", "places": "Place", "works": "Work", "witnesses": "Witness"}


def chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def import_entities(session, entities: dict, batch_size: int):
    for bucket, label in LABELS.items():
        build_props = ENTITY_PROPERTY_BUILDERS[bucket]
        rows = [{"id": eid, "props": build_props(ent)} for eid, ent in entities[bucket].items()]
        for batch in chunked(rows, batch_size):
            session.run(
                f"UNWIND $rows AS row MERGE (n:{label} {{id: row.id}}) SET n += row.props",
                rows=batch,
            )
        print(f"  {label}: {len(rows)} nodes")


def import_letters(session, letters: list[dict], batch_size: int):
    rows = [{"id": letter["id"], "props": letter_properties(letter)} for letter in letters]
    for batch in chunked(rows, batch_size):
        session.run(
            "UNWIND $rows AS row MERGE (l:Letter {id: row.id}) SET l += row.props",
            rows=batch,
        )
    print(f"  Letter: {len(rows)} nodes")


def import_relationships(session, letters: list[dict], batch_size: int):
    rel_rows = {"SENT_BY": [], "SENT_TO": [], "SENT_FROM": [], "MENTIONS": []}
    for letter in letters:
        lid = letter["id"]
        if letter["sent"]["person"]:
            rel_rows["SENT_BY"].append({"letter": lid, "target": letter["sent"]["person"]})
        if letter["received"]["person"]:
            rel_rows["SENT_TO"].append({"letter": lid, "target": letter["received"]["person"]})
        place = effective_sent_place(letter)
        if place:
            rel_rows["SENT_FROM"].append({"letter": lid, "target": place})
        for bucket in LABELS:
            for eid in letter["mentions"][bucket]:
                rel_rows["MENTIONS"].append({"letter": lid, "target": eid})

    target_label = {
        "SENT_BY": "Person", "SENT_TO": "Person", "SENT_FROM": "Place", "MENTIONS": None,
    }
    for rel_type, rows in rel_rows.items():
        if not rows:
            continue
        if target_label[rel_type]:
            match_clause = f"MATCH (t:{target_label[rel_type]} {{id: row.target}})"
        else:
            # MENTIONS can point at any of the four entity labels; match by id across all of them.
            match_clause = "MATCH (t {id: row.target}) WHERE t:Person OR t:Place OR t:Work OR t:Witness"
        for batch in chunked(rows, batch_size):
            session.run(
                f"UNWIND $rows AS row "
                f"MATCH (l:Letter {{id: row.letter}}) {match_clause} "
                f"MERGE (l)-[:{rel_type}]->(t)",
                rows=batch,
            )
        print(f"  {rel_type}: {len(rows)} relationships")


def import_entity_relationships(session, entities: dict, batch_size: int):
    rels_by_type: dict[str, list[dict]] = {}
    for rel in entity_relationships(entities):
        rels_by_type.setdefault(rel["type"], []).append(
            {"source": rel["source"], "target": rel["target"]}
        )
    for rel_type, rows in rels_by_type.items():
        source_label = label_for_id(rows[0]["source"])
        target_label = label_for_id(rows[0]["target"])
        for batch in chunked(rows, batch_size):
            session.run(
                f"UNWIND $rows AS row "
                f"MATCH (a:{source_label} {{id: row.source}}), (b:{target_label} {{id: row.target}}) "
                f"MERGE (a)-[:{rel_type}]->(b)",
                rows=batch,
            )
        print(f"  {rel_type}: {len(rows)} relationships")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--uri", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--batch-size", type=int, default=500)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    config = load_config(repo_root)
    uri = args.uri or config["neo4j"]["uri"]
    user = args.user or config["neo4j"]["user"]
    password = args.password or os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("No Neo4j password given (--password or NEO4J_PASSWORD env var required).", file=sys.stderr)
        sys.exit(1)

    from neo4j import GraphDatabase

    entities = load_entities(repo_root)
    letters = load_letters(repo_root)

    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    with driver.session() as session:
        print("Creating constraints...")
        for label in ("Letter", "Person", "Place", "Work", "Witness"):
            session.run(
                f"CREATE CONSTRAINT {label.lower()}_id IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.id IS UNIQUE"
            )
        print("Importing entities...")
        import_entities(session, entities, args.batch_size)
        print("Importing letters...")
        import_letters(session, letters, args.batch_size)
        print("Importing relationships...")
        import_relationships(session, letters, args.batch_size)
        print("Importing entity-to-entity relationships (AUTHORED_BY/PUBLISHED_AT/WITNESS_OF)...")
        import_entity_relationships(session, entities, args.batch_size)

        counts = session.run(
            "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS n ORDER BY label"
        ).data()
        print("Node counts:", counts)
        rel_counts = session.run(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(*) AS n ORDER BY type"
        ).data()
        print("Relationship counts:", rel_counts)
    driver.close()


if __name__ == "__main__":
    main()
