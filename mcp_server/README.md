# Laßberg Edition MCP Server

FastMCP (stdio) server exposing the digitized Laßberg correspondence to Claude Desktop and other
MCP clients: semantic search over letter full texts, read-only Cypher queries against the
correspondence graph, and SPARQL queries against the CMIF/correspSearch-style RDF export.

## Tools

| Tool | Needs running services? | What it does |
|---|---|---|
| `semantic_search(query, top_k=10, date_from?, date_to?)` | No (static files only) | BGE-M3 cosine search over the ~170 full-text letters |
| `get_letter(letter_id)` | No (static files only) | Full metadata + mentions + text for one letter |
| `graph_query(cypher, limit=100)` | Neo4j (`make graph`) | Read-only Cypher over the correspondence graph (all 3268 letters) |
| `sparql_query(query)` | Oxigraph (`make sparql`) | SELECT/ASK SPARQL over `rdf/edition.ttl` |

`semantic_search` and `get_letter` work with no Docker services running at all - they read
straight from `build/` and `embeddings/`. `graph_query`/`sparql_query` return a clear
`RuntimeError` (not a crash) if their backing service isn't up.

## Id format

Every letter/person/place/work/witness id is a canonical string - `lassberg-letter-0952`,
`lassberg-correspondent-0179`, `lassberg-place-0025`, `lassberg-literature-0011`,
`lassberg-witness-0001` (always a 4-digit zero-padded number) - never a bare number. Report and
query using this exact form; `get_letter()` tolerates loose input ("952", "letter-952") and
normalizes it, but `graph_query`/`sparql_query` expect the canonical form written directly into
the query.

## Data model quick reference

Extended 2026-07-11 to carry each register's full metadata (not just id/label) - see
`scripts/lib_pipeline.py`'s property builders, shared by the Neo4j/RDF/browser-graph.json exports
so all three stay in sync.

**Neo4j** (see `scripts/export_cypher.py`):
```
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
(w:Work)-[:AUTHORED_BY]->(p:Person)     - only when the work's <author> links a register id
(w:Work)-[:PUBLISHED_AT]->(pl:Place)    - only when the work's <pubPlace> links a register id
(wit:Witness)-[:WITNESS_OF]->(w:Work)   - only when the witness's @corresp links a register id
```

**RDF** (see `scripts/export_rdf.py`; prefixes `csvoc: <https://lod.academy/correspsearch/vocab/terms#>`,
`schema: <http://schema.org/>`, `dcterms: <http://purl.org/dc/terms/>`,
`voc: <https://michaelscho.github.io/lassberg/vocab/>` for the handful of fields with no fitting
standard term):
```
<letter/ID>  a csvoc:Letter ; csvoc:hasCorrespAction <.../sent|received> ; csvoc:mentions <person|place|work|witness/ID> ;
             schema:dateCreated ; schema:abstract (incipit) ; schema:text (full text) ; schema:inLanguage ;
             voc:publicationStatus ; voc:reviewStatus ; voc:harrisNumber ; dcterms:identifier (signature) ;
             dcterms:bibliographicCitation + dcterms:source (published_in text + url) .
<.../sent>   a csvoc:correspAction, csvoc:Sent ; csvoc:hasParticipant <person/ID> ; csvoc:tookPlaceAt <place/ID> ; csvoc:hasTimespan <.../date> .
<.../date>   csvoc:startsOn "YYYY-MM-DD"^^xsd:date .
<.../received> a csvoc:correspAction, csvoc:Received ; csvoc:hasParticipant <person/ID> .
<person/ID>  a csvoc:Person|csvoc:Institution|csvoc:Group ; rdfs:label ; owl:sameAs <gnd-or-wikidata-uri> ;
             schema:gender ; schema:jobTitle* (occupation) ; schema:birthDate ; schema:deathDate ; voc:personType .
<place/ID>   a csvoc:Place ; rdfs:label ; owl:sameAs <wikidata-uri> ; schema:description ;
             schema:geo [ schema:latitude; schema:longitude ] .
<work/ID>    a schema:CreativeWork ; rdfs:label ; voc:litType ; schema:dateCreated ; dcterms:identifier* (idno) ;
             schema:author <person/ID>|Literal ; schema:locationCreated <place/ID>|Literal .
<witness/ID> a schema:CreativeWork ; rdfs:label ; schema:exampleOfWork <work/ID> .
```

## Setup

```bash
cd /path/to/lassberg
python3 -m venv .venv-infra   # if not already created
source .venv-infra/bin/activate
pip install -r requirements-infra.txt
```

For `graph_query`, set `NEO4J_PASSWORD` in the environment (same value used to start the
container, see `.env` / `docker-compose.yml`).

## Claude Desktop configuration

Add to `claude_desktop_config.json` (adjust the absolute paths and password).

**macOS/Linux**, Claude Desktop running on the same machine as the repo:
```json
{
  "mcpServers": {
    "lassberg-edition": {
      "command": "/absolute/path/to/lassberg/.venv-infra/bin/python",
      "args": ["/absolute/path/to/lassberg/mcp_server/server.py"],
      "env": {
        "NEO4J_PASSWORD": "your-neo4j-password"
      }
    }
  }
}
```

**Windows + WSL**, Claude Desktop running on Windows while the repo lives in a WSL distro: the
`"env"` block above is **not** reliably forwarded across the `wsl.exe` boundary (Windows-side
process env vars don't automatically become WSL shell env vars) - bake the variable into the
command string itself instead, and drop `"env"` entirely:
```json
{
  "mcpServers": {
    "lassberg-edition": {
      "command": "wsl.exe",
      "args": [
        "-d", "Ubuntu", "--cd", "/home/USER/github/lassberg/",
        "-e", "bash", "-lc",
        "NEO4J_PASSWORD=your-neo4j-password .venv-infra/bin/python ./mcp_server/server.py"
      ]
    }
  }
}
```

## Running standalone

```bash
python mcp_server/server.py
```

This starts the stdio server directly - useful for testing with any MCP client, or for importing
`mcp_server/tools/*.py` functions directly into other agent frameworks (LangChain, custom scripts,
etc.) since none of them import `fastmcp` themselves.
