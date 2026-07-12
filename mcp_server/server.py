#!/usr/bin/env python3
"""
Phase 6 of the KI-Infrastruktur pipeline: FastMCP (stdio) server exposing the Laßberg
correspondence edition to Claude Desktop and other MCP clients.

Tools (thin registrations only - the actual logic lives in mcp_server/tools/*.py as plain,
MCP-independent functions, importable from other agent frameworks or scripts too):
  semantic_search(query, top_k=10, date_from?, date_to?) - BGE-M3 cosine search, files only,
      no services required.
  graph_query(cypher, limit=100)   - read-only Cypher against Neo4j (needs `make graph` running).
  get_letter(letter_id)            - full metadata+text for one letter, from JSON files only.
  sparql_query(query)              - SPARQL against Oxigraph (needs `make sparql` running).

Id format (repeated in each tool's docstring since that's what the model actually reads before
calling a tool): every letter/person/place/work/witness id in this corpus is a canonical string
like "lassberg-letter-0952" (4-digit zero-padded number) - never a bare number. Always use and
report ids in this full form; "letter 952" is not a valid id anywhere in this system.

Run:
    python mcp_server/server.py
See mcp_server/README.md for Claude Desktop configuration.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastmcp import FastMCP

from tools.graph_query import get_letter as _get_letter
from tools.graph_query import graph_query as _graph_query
from tools.semantic_search import semantic_search as _semantic_search
from tools.sparql_query import sparql_query as _sparql_query

mcp = FastMCP("lassberg-edition")


@mcp.tool
def semantic_search(query: str, top_k: int = 10, date_from: str | None = None, date_to: str | None = None) -> list[dict]:
    """Semantic search over the ~170 full-text Laßberg letters using BGE-M3 embeddings.

    Args:
        query: natural-language question or topic (German or English).
        top_k: number of results.
        date_from: optional ISO date lower bound (YYYY-MM-DD).
        date_to: optional ISO date upper bound (YYYY-MM-DD).

    Returns list of {id, score, date, sender, recipient, incipit}. `id` is the canonical
    "lassberg-letter-NNNN" form (4-digit zero-padded) - always use/report this exact string (e.g.
    "lassberg-letter-0952", never just "952") since get_letter()/graph_query() require it. Runs
    entirely from static files (embeddings/, build/) - no Neo4j/Oxigraph required.
    """
    return _semantic_search(query, top_k=top_k, date_from=date_from, date_to=date_to)


@mcp.tool
def graph_query(cypher: str, limit: int = 100) -> list[dict]:
    """Read-only Cypher query against the Neo4j correspondence graph.

    Ids: every node's `id` property is a canonical string ("lassberg-letter-0952",
    "lassberg-correspondent-0179", "lassberg-place-0025", "lassberg-literature-0011",
    "lassberg-witness-0001") - write `{id: 'lassberg-letter-0952'}` in your MATCH clauses, never
    a bare number.

    Data model (full per-type property list; extended 2026-07-11 with the registers' full
    metadata, not just id/label):
      (:Letter {id, date, incipit?, text?, file?, has_fulltext, status, lang?, publication_status?,
                 harris_number?, journal_number?, repository_place?, repository_institution?,
                 signature?, facsimile_url?, published_in?, published_in_url?, comment?,
                 iiif_manifest?, iiif_canvas?})
      (:Person {id, label, kind, person_type?, gender?, corporate_body, gnd?, wikidata?, url?,
                 occupation?, education?, birth?, death?})
      (:Place  {id, label, wikidata?, gnd?, url?, desc?, lat?, lon?})
      (:Work   {id, label, lit_type?, ana?, date?, idno?, author_label?, pub_place_label?})
      (:Witness{id, label, witness_type?, settlement?, repository?, signature?, note?})
      (l:Letter)-[:SENT_BY]->(p:Person), (l)-[:SENT_TO]->(p:Person), (l)-[:SENT_FROM]->(pl:Place)
      (l:Letter)-[:MENTIONS]->(p:Person|pl:Place|w:Work|wit:Witness)
      (w:Work)-[:AUTHORED_BY]->(p:Person), (w:Work)-[:PUBLISHED_AT]->(pl:Place)
      (wit:Witness)-[:WITNESS_OF]->(w:Work)

    Write keywords (CREATE/MERGE/DELETE/SET/REMOVE/DROP/LOAD CSV) are rejected. Requires Neo4j
    running (`make graph`) and NEO4J_PASSWORD set in the environment.
    """
    return _graph_query(cypher, limit=limit)


@mcp.tool
def get_letter(letter_id: str) -> dict:
    """Full metadata, mentions, and text for one letter, read directly from the JSON
    intermediate layer - no services required.

    Args:
        letter_id: the canonical id, e.g. "lassberg-letter-0952". Loose forms ("952",
            "letter-952") are tolerated and normalized, but always report results using the
            canonical id in full - it's the only form graph_query/sparql_query also accept.
    """
    return _get_letter(letter_id)


@mcp.tool
def sparql_query(query: str) -> dict:
    """SELECT/ASK SPARQL query against the Oxigraph endpoint (CMIF/correspSearch-style RDF).

    Ids: entity URIs are built from the same canonical ids as everywhere else -
    <base_uri>letter/lassberg-letter-0952, .../person/lassberg-correspondent-0179, etc. (4-digit
    zero-padded numbers).

    Key predicates (prefix csvoc: <https://lod.academy/correspsearch/vocab/terms#>, schema:
    <http://schema.org/>, dcterms: <http://purl.org/dc/terms/>, voc:
    <https://michaelscho.github.io/lassberg/vocab/>):
      <letter/ID> a csvoc:Letter ; csvoc:hasCorrespAction <.../sent|received> ; csvoc:mentions <person|place|work|witness/ID> ;
                  schema:dateCreated ; schema:text (full text) ; voc:harrisNumber ; dcterms:bibliographicCitation (published_in) .
      <.../sent>  csvoc:hasParticipant <person/ID> ; csvoc:tookPlaceAt <place/ID> ; csvoc:hasTimespan <.../date> .
      <.../date>  csvoc:startsOn "YYYY-MM-DD"^^xsd:date .
      <person/ID> a csvoc:Person|csvoc:Institution|csvoc:Group ; rdfs:label ; owl:sameAs <gnd-or-wikidata> ;
                  schema:gender ; schema:birthDate ; schema:deathDate ; voc:personType .
      <place/ID>  a csvoc:Place ; rdfs:label ; owl:sameAs <wikidata> .
      <work/ID>   a schema:CreativeWork ; rdfs:label ; schema:author <person/ID>|Literal .

    Requires Oxigraph running (`make sparql`).
    """
    return _sparql_query(query)


if __name__ == "__main__":
    mcp.run()
