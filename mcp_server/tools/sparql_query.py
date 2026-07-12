"""Pure-function SPARQL access against the Oxigraph endpoint. No MCP dependency in this module -
see mcp_server/tools/semantic_search.py for why.

--- Id format --- entity URIs are built from the canonical ids used everywhere else in this
system: <base_uri>letter/lassberg-letter-NNNN, .../person/lassberg-correspondent-NNNN,
.../place/lassberg-place-NNNN, .../work/lassberg-literature-NNNN, .../witness/lassberg-witness-NNNN
(NNNN = 4-digit zero-padded). Always build/report URIs and ids in this exact canonical form.

RDF predicates reference (see PLAN_edition_ki_infrastruktur.md Phase 5 / scripts/export_rdf.py,
extended 2026-07-11 with the registers' full metadata):
  PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
  PREFIX schema: <http://schema.org/>
  PREFIX dcterms: <http://purl.org/dc/terms/>
  PREFIX voc: <https://michaelscho.github.io/lassberg/vocab/>   (project-local terms, see export_rdf.py)
  <letter/ID>  a csvoc:Letter ; csvoc:hasCorrespAction <letter/ID/sent|received> ; csvoc:mentions <person|place|work|witness/ID> ;
               schema:dateCreated ; schema:abstract (incipit) ; schema:text (full text, fulltext letters only) ;
               schema:inLanguage ; voc:publicationStatus ; voc:reviewStatus ; voc:harrisNumber ;
               dcterms:identifier (signature) ; dcterms:bibliographicCitation + dcterms:source (published_in + url) .
  <letter/ID/sent>  a csvoc:correspAction, csvoc:Sent ; csvoc:hasParticipant <person/ID> ; csvoc:tookPlaceAt <place/ID> ; csvoc:hasTimespan <letter/ID/sent/date> .
  <letter/ID/sent/date>  csvoc:startsOn "YYYY-MM-DD"^^xsd:date .
  <letter/ID/received>  a csvoc:correspAction, csvoc:Received ; csvoc:hasParticipant <person/ID> .
  <person/ID>  a csvoc:Person|csvoc:Institution|csvoc:Group ; rdfs:label ; owl:sameAs <gnd-or-wikidata> ;
               schema:gender ; schema:jobTitle* ; schema:birthDate ; schema:deathDate ; voc:personType .
  <place/ID>   a csvoc:Place ; rdfs:label ; owl:sameAs <wikidata> ; schema:description ;
               schema:geo [schema:latitude; schema:longitude] .
  <work/ID>    a schema:CreativeWork ; rdfs:label ; voc:litType ; schema:dateCreated ; dcterms:identifier* ;
               schema:author <person/ID>|Literal ; schema:locationCreated <place/ID>|Literal .
  <witness/ID> a schema:CreativeWork ; rdfs:label ; schema:exampleOfWork <work/ID> .
"""
from __future__ import annotations

from pathlib import Path

import requests

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _load_endpoint() -> str:
    import yaml
    with (REPO_ROOT / "config.yaml").open() as fh:
        config = yaml.safe_load(fh)
    return config["sparql"]["endpoint"]


def sparql_query(query: str) -> dict:
    """Runs a SELECT or ASK SPARQL query against the local Oxigraph endpoint.

    Args:
        query: a SPARQL SELECT or ASK query (e.g. against csvoc:Letter/csvoc:mentions - see this
            module's docstring for the predicate reference).

    Returns:
        The endpoint's SPARQL-JSON results object. Raises RuntimeError with the endpoint's own
        error message on failure (bad query syntax, endpoint down, etc.) rather than crashing.

    Example:
        sparql_query('''
            PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
            SELECT ?letter WHERE {
              ?letter csvoc:mentions <https://michaelscho.github.io/lassberg/place/lassberg-place-0043> .
            } LIMIT 10
        ''')
    """
    endpoint = _load_endpoint()
    try:
        resp = requests.get(
            f"{endpoint}/query" if not endpoint.endswith("/query") else endpoint,
            params={"query": query},
            headers={"Accept": "application/sparql-results+json"},
            timeout=30,
        )
    except requests.exceptions.ConnectionError as exc:
        raise RuntimeError(
            f"Oxigraph is not reachable at {endpoint} ({exc}). "
            "Start it with `make sparql` or `docker compose up -d oxigraph`."
        ) from exc

    if not resp.ok:
        raise RuntimeError(f"SPARQL endpoint returned {resp.status_code}: {resp.text[:500]}")
    return resp.json()
