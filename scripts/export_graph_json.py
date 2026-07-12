#!/usr/bin/env python3
"""
Phase 7b.1: exports the JSON intermediate layer as a Graphology-serialization-format graph
(`frontend/data/graph.json`) for client-side traversal (Sigma.js viz, GraphRAG expansion
functions in frontend/graph.js) - no backend required.

Same node/edge model and full entity/letter metadata as the Neo4j export (scripts/export_cypher.py)
and RDF export (scripts/export_rdf.py) - one modelling (scripts/lib_pipeline.py's property
builders + entity_relationships), three runtimes (Neo4j, RDF, browser). See
PLAN_edition_ki_infrastruktur.md Phase 7b.1 for the graph.json format itself.

Usage:
    python scripts/export_graph_json.py [--repo-root PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_pipeline import (  # noqa: E402
    ENTITY_PROPERTY_BUILDERS,
    effective_sent_place,
    entity_relationships,
    letter_properties,
    load_entities,
    load_letters,
)

LABELS = {"persons": "person", "places": "place", "works": "work", "witnesses": "witness"}


def letter_display_label(letter: dict, date: str | None) -> str:
    """Short label for graph rendering (frontend/graph.js draws this next to each node) - the
    full text/incipit are still in the node's attributes (see letter_properties()), just not used
    as the on-canvas label since they're far too long."""
    if not letter["incipit"]:
        return f"{letter['id']} ({date or '?'})"
    return f"{letter['incipit'][:40]}..."


def build_graph(entities: dict, letters: list[dict]) -> dict:
    nodes = []
    edges = []

    for bucket, kind in LABELS.items():
        build_props = ENTITY_PROPERTY_BUILDERS[bucket]
        for eid, ent in entities[bucket].items():
            attrs = {"type": kind, **build_props(ent)}
            nodes.append({"key": eid, "attributes": attrs})

    for letter in letters:
        props = letter_properties(letter)
        attrs = {"type": "letter", **props, "label": letter_display_label(letter, props.get("date"))}
        nodes.append({"key": letter["id"], "attributes": attrs})

        if letter["sent"]["person"]:
            edges.append({"source": letter["id"], "target": letter["sent"]["person"], "attributes": {"type": "SENT_BY"}})
        if letter["received"]["person"]:
            edges.append({"source": letter["id"], "target": letter["received"]["person"], "attributes": {"type": "SENT_TO"}})
        place = effective_sent_place(letter)
        if place:
            edges.append({"source": letter["id"], "target": place, "attributes": {"type": "SENT_FROM"}})
        for bucket in LABELS:
            for eid in letter["mentions"][bucket]:
                edges.append({"source": letter["id"], "target": eid, "attributes": {"type": "MENTIONS"}})

    for rel in entity_relationships(entities):
        edges.append({"source": rel["source"], "target": rel["target"], "attributes": {"type": rel["type"]}})

    return {"attributes": {}, "options": {"type": "directed", "multi": True, "allowSelfLoops": False},
            "nodes": nodes, "edges": edges}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    entities = load_entities(repo_root)
    letters = load_letters(repo_root)

    graph = build_graph(entities, letters)

    out_dir = repo_root / "frontend/data"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "graph.json"
    out_path.write_text(json.dumps(graph, ensure_ascii=False), encoding="utf-8")

    print(f"Wrote {out_path}: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges "
          f"({out_path.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
