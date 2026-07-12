"""Pure-function Neo4j access: a guarded read-only Cypher runner plus a convenience
`get_letter(id)` that reads directly from the JSON intermediate layer (no Neo4j needed for that
one). No MCP dependency in this module - see mcp_server/tools/semantic_search.py for why.

--- Letter/entity id format (read this before writing a Cypher query or calling get_letter) ---
Every id in this corpus is a canonical string, never a bare number: letters are
"lassberg-letter-NNNN" (4-digit zero-padded, e.g. "lassberg-letter-0952"), persons
"lassberg-correspondent-NNNN", places "lassberg-place-NNNN", works "lassberg-literature-NNNN",
witnesses "lassberg-witness-NNNN". Always reference and report letters/entities by this full id,
not by the bare number - "letter 952" is not a valid id anywhere in this system. get_letter()
tolerates loose input (a bare number, "letter-952", etc.) and normalizes it, but graph_query's
raw Cypher does not - write `{id: 'lassberg-letter-0952'}`, not `{id: '952'}`.

Data model reference (see PLAN_edition_ki_infrastruktur.md Phase 4 / scripts/export_cypher.py,
extended 2026-07-11 with the registers' full metadata - see scripts/lib_pipeline.py for the exact
per-type property list):
  (:Letter {id, date, incipit?, text?, file?, has_fulltext, status, lang?, publication_status?,
             harris_number?, journal_number?, repository_place?, repository_institution?,
             signature?, facsimile_url?, published_in?, published_in_url?, comment?,
             iiif_manifest?, iiif_canvas?})
  (:Person {id, label, kind, person_type?, gender?, corporate_body, gnd?, wikidata?, url?,
             occupation?, education?, birth?, death?})
  (:Place  {id, label, wikidata?, gnd?, url?, desc?, lat?, lon?})
  (:Work   {id, label, lit_type?, ana?, date?, idno?, author_label?, pub_place_label?})
  (:Witness{id, label, witness_type?, settlement?, repository?, signature?, note?})
  (l:Letter)-[:SENT_BY]->(p:Person)
  (l:Letter)-[:SENT_TO]->(p:Person)
  (l:Letter)-[:SENT_FROM]->(pl:Place)
  (l:Letter)-[:MENTIONS]->(p:Person|pl:Place|w:Work|wit:Witness)
  (w:Work)-[:AUTHORED_BY]->(p:Person)    - only when the work's author links a register id
  (w:Work)-[:PUBLISHED_AT]->(pl:Place)   - only when the work's pubPlace links a register id
  (wit:Witness)-[:WITNESS_OF]->(w:Work)  - only when the witness's corresp links a register id
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Cypher write keywords rejected outright, in addition to using a read-only driver session -
# belt and suspenders, since a session's access mode is advisory in some driver/server versions.
_WRITE_KEYWORDS = re.compile(
    r"\b(CREATE|MERGE|DELETE|SET|REMOVE|DROP|CALL\s+db\.\w*create|LOAD\s+CSV)\b",
    re.IGNORECASE,
)

_driver = None
_letters_by_id: dict | None = None


def _load_config() -> dict:
    import yaml
    with (REPO_ROOT / "config.yaml").open() as fh:
        return yaml.safe_load(fh)


def _get_driver():
    global _driver
    if _driver is None:
        from neo4j import GraphDatabase
        config = _load_config()
        password = os.environ.get("NEO4J_PASSWORD")
        if not password:
            raise RuntimeError("NEO4J_PASSWORD environment variable is not set.")
        _driver = GraphDatabase.driver(
            config["neo4j"]["uri"], auth=(config["neo4j"]["user"], password)
        )
    return _driver


QUERY_TIMEOUT_SECONDS = 20


def graph_query(cypher: str, limit: int = 100) -> list[dict]:
    """Runs a read-only Cypher query against the Neo4j correspondence graph.

    Args:
        cypher: a Cypher query. Write operations (CREATE/MERGE/DELETE/SET/REMOVE/DROP/LOAD CSV)
            are rejected before execution. Write your own `LIMIT` into the query when possible -
            this tool also caps rows server-side (see `limit`), but a query with no LIMIT and a
            join across large label sets (e.g. `MATCH (l:Letter), (p:Person) RETURN l, p` with no
            relationship pattern - a cartesian product of 3268 x 673 rows) can still be slow to
            even start streaming, since Neo4j must plan/execute the full match before this tool
            can stop early.
        limit: max rows returned. Enforced by stopping iteration early (not by fetching
            everything and truncating after), so a `LIMIT`-less query is still bounded in how
            much this tool pulls into memory - but see the cartesian-product caveat above.

    Returns:
        List of row dicts. Raises RuntimeError if Neo4j is unreachable, or if the query doesn't
        finish within QUERY_TIMEOUT_SECONDS (a runaway query is killed rather than left to
        hang/OOM the server process). Raises ValueError if the query contains a write keyword.

    Example:
        graph_query("MATCH (l:Letter)-[:MENTIONS]->(p:Person {id: 'lassberg-correspondent-0382'}) "
                    "RETURN l.id, l.date ORDER BY l.date")
    """
    if _WRITE_KEYWORDS.search(cypher):
        raise ValueError("Write operations are not permitted via graph_query (read-only tool).")

    try:
        driver = _get_driver()
        driver.verify_connectivity()
    except Exception as exc:
        raise RuntimeError(
            f"Neo4j is not reachable ({exc}). Start it with `make graph` or `docker compose up -d neo4j`."
        ) from exc

    try:
        with driver.session(default_access_mode="READ") as session:
            result = session.run(cypher, timeout=QUERY_TIMEOUT_SECONDS)
            rows = []
            for record in result:
                rows.append(dict(record))
                if len(rows) >= limit:
                    result.consume()  # stop the server-side stream instead of draining the rest
                    break
    except Exception as exc:
        raise RuntimeError(
            f"Query failed or exceeded the {QUERY_TIMEOUT_SECONDS}s timeout ({exc}). If this was "
            f"a broad query (e.g. matching multiple large label sets with no relationship "
            f"pattern), add an explicit LIMIT or a relationship pattern to narrow it."
        ) from exc
    return rows


def normalize_letter_id(raw_id: str) -> str:
    """Best-effort normalization of loose references ("952", "letter 952", "letter-0952") to the
    canonical "lassberg-letter-NNNN" (4-digit zero-padded) id every other tool/query expects. Only
    used by get_letter()'s convenience lookup - graph_query's raw Cypher is not rewritten, since
    that would mean silently editing a query the model wrote itself."""
    raw_id = raw_id.strip()
    match = re.search(r"(\d+)", raw_id)
    if not match:
        return raw_id  # unrecognizable; let the caller's KeyError report the original input
    return f"lassberg-letter-{int(match.group(1)):04d}"


def get_letter(letter_id: str) -> dict:
    """Returns all metadata, mentions, and full text for one letter, straight from the JSON
    intermediate layer (build/letters.jsonl) - no Neo4j connection required.

    Args:
        letter_id: the canonical id, e.g. "lassberg-letter-0952". Loose forms ("952", "letter
            952", "letter-0952") are tolerated and normalized, but always prefer and report the
            canonical id in full - it is the only id that also works in graph_query/sparql_query.

    Returns:
        The letter's record (id, file, has_fulltext, status, sent, received, mentions, text,
        incipit, lang, publication_status, register_meta). Raises KeyError with a corrective
        message (not a bare lookup failure) if the id doesn't exist in the register.
    """
    global _letters_by_id
    if _letters_by_id is None:
        _letters_by_id = {}
        with (REPO_ROOT / "build/letters.jsonl").open(encoding="utf-8") as fh:
            for line in fh:
                rec = json.loads(line)
                _letters_by_id[rec["id"]] = rec

    canonical_id = normalize_letter_id(letter_id)
    if canonical_id not in _letters_by_id:
        raise KeyError(
            f"Unknown letter id: {letter_id!r} (normalized to {canonical_id!r}, which also "
            f"doesn't exist). Letter ids are 'lassberg-letter-NNNN', a zero-padded 4-digit "
            f"number, e.g. 'lassberg-letter-0952'. Use semantic_search or graph_query to find "
            f"the correct id first."
        )
    return _letters_by_id[canonical_id]
