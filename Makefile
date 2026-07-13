# KI-Infrastruktur pipeline orchestration (PLAN_edition_ki_infrastruktur.md). Uses its own
# .venv-infra - never touches src/'s .venv (see CLAUDE.md: separate, fragile dependency set).
#
# Setup: python3 -m venv .venv-infra && .venv-infra/bin/pip install -r requirements-infra.txt
# `graph`/`sparql` need NEO4J_PASSWORD set (see .env, gitignored, docker-compose.yml reads it too).

PYTHON := .venv-infra/bin/python

.PHONY: all parse embed cluster graph rdf sparql explore frontend cmif graph-json status status-write test clean

all: parse embed cluster graph rdf explore

# --- Phase 1 ---
build/letters.jsonl: $(wildcard data/letters/lassberg-letter-*.xml) $(wildcard data/register/lassberg-*.xml) scripts/parse_tei.py
	$(PYTHON) scripts/parse_tei.py

parse: build/letters.jsonl

# --- Phase 2 ---
embeddings/bge-m3/letters.safetensors: build/letters.jsonl scripts/embed.py
	$(PYTHON) scripts/embed.py

embed: embeddings/bge-m3/letters.safetensors

# --- Phase 3 ---
clustering/clusters.json: embeddings/bge-m3/letters.safetensors scripts/cluster.py
	$(PYTHON) scripts/cluster.py

cluster: clustering/clusters.json

# --- Phase 4 ---
graph/import.cypher: build/letters.jsonl scripts/export_cypher.py
	$(PYTHON) scripts/export_cypher.py

graph: graph/import.cypher
	docker compose up -d neo4j
	$(PYTHON) scripts/import_neo4j.py

# --- Phase 5 ---
rdf/edition.ttl: build/letters.jsonl scripts/export_rdf.py
	$(PYTHON) scripts/export_rdf.py

rdf: rdf/edition.ttl

cmif: build/letters.jsonl
	$(PYTHON) scripts/export_rdf.py --cmif

sparql: rdf/edition.ttl
	docker compose up -d oxigraph
	$(PYTHON) scripts/load_oxigraph.py

# --- Phase 7 / 7b ---
# Explore-page data artifacts (html/explore.html + js/explore/), served from json/explore/.
# clustering/ is no longer shipped to the website (internal corpus-triage artifact only).
json/explore/graph.json: build/letters.jsonl scripts/export_graph_json.py
	$(PYTHON) scripts/export_graph_json.py

graph-json: json/explore/graph.json

json/explore/overview.json: build/letters.jsonl scripts/export_overview.py
	$(PYTHON) scripts/export_overview.py

json/explore/related.json: embeddings/bge-m3/letters.safetensors build/letters.jsonl scripts/export_related.py
	$(PYTHON) scripts/export_related.py

explore: rdf/edition.ttl json/explore/graph.json json/explore/overview.json json/explore/related.json scripts/export_frontend.py
	$(PYTHON) scripts/export_frontend.py

# Backwards-compatible alias (the explore page was a separate frontend/ site until 2026-07).
frontend: explore

# --- Status model (docs/TEI.md "Letter status model") ---
status:
	$(PYTHON) scripts/sync_letter_status.py

status-write:
	$(PYTHON) scripts/sync_letter_status.py --write

# --- Phase 8 ---
test:
	$(PYTHON) -m pytest tests/test_pipeline.py -v
	node --test tests/test_graph_core.mjs

clean:
	rm -f build/letters.jsonl build/entities.json build/manifest.json build/warnings.log
