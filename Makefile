# KI-Infrastruktur pipeline orchestration (PLAN_edition_ki_infrastruktur.md). Uses its own
# .venv-infra - never touches src/'s .venv (see CLAUDE.md: separate, fragile dependency set).
#
# Setup: python3 -m venv .venv-infra && .venv-infra/bin/pip install -r requirements-infra.txt
# `graph`/`sparql` need NEO4J_PASSWORD set (see .env, gitignored, docker-compose.yml reads it too).

PYTHON := .venv-infra/bin/python

.PHONY: all parse embed cluster graph rdf sparql frontend cmif graph-json test clean

all: parse embed cluster graph rdf frontend

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
frontend/data/graph.json: build/letters.jsonl scripts/export_graph_json.py
	$(PYTHON) scripts/export_graph_json.py

graph-json: frontend/data/graph.json

frontend: clustering/clusters.json rdf/edition.ttl frontend/data/graph.json scripts/export_frontend.py
	$(PYTHON) scripts/export_frontend.py

# --- Phase 8 ---
test:
	$(PYTHON) -m pytest tests/test_pipeline.py -v
	node --test tests/test_graph_core.mjs

clean:
	rm -f build/letters.jsonl build/entities.json build/manifest.json build/warnings.log
