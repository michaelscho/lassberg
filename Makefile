# KI-Infrastruktur pipeline orchestration (PLAN_edition_ki_infrastruktur.md). Uses its own
# .venv-infra - never touches src/'s .venv (see CLAUDE.md: separate, fragile dependency set).
#
# Setup: python3 -m venv .venv-infra && .venv-infra/bin/pip install -r requirements-infra.txt
# `graph`/`sparql` need NEO4J_PASSWORD set (see .env, gitignored, docker-compose.yml reads it too).

PYTHON := .venv-infra/bin/python

.PHONY: blb-harvest blb-alto blb-match blb-download blb-apply transkribus-gt hsp hsp-mirror hsp-index hsp-export test-network all parse embed cluster graph rdf sparql explore frontend cmif graph-json status status-write test clean

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

# --- Manuscripts / Handschriftenportal (network; NOT part of `make all`; data/hsp/ is gitignored) ---
hsp-mirror:
	$(PYTHON) scripts/manuscripts/mirror_hsp.py

hsp-index:
	$(PYTHON) scripts/manuscripts/build_hsp_index.py

hsp-export:
	$(PYTHON) scripts/export_manuscripts.py
	$(PYTHON) scripts/export_manuscripts.py --local

hsp: hsp-mirror hsp-index hsp-export

# --- BLB Karlsruhe letters: images + ALTO/PAGE (network; NOT part of `make all`; data/blb/ is gitignored, ~12 GB) ---
# harvest -> alto -> match (review build/blb/matches.tsv: accept=y) -> download -> apply (writes the register)
blb-harvest:
	$(PYTHON) scripts/blb/harvest.py

blb-alto:
	$(PYTHON) scripts/blb/fetch_alto.py

blb-match:
	$(PYTHON) scripts/blb/match.py

blb-download:
	$(PYTHON) scripts/blb/download.py

blb-apply:
	$(PYTHON) scripts/blb/apply_register.py --write

# Ground Truth = Transkribus documents titled done_* (needs src/config.py credentials; main .venv)
transkribus-gt:
	.venv/bin/python scripts/transkribus/sync_gt.py --write

# --- Status model (docs/TEI.md "Letter status model") ---
status:
	$(PYTHON) scripts/sync_letter_status.py

status-write:
	$(PYTHON) scripts/sync_letter_status.py --write

# --- Phase 8 ---
test:
	$(PYTHON) -m pytest tests/test_pipeline.py tests/test_hsp.py -v
	node --test tests/test_graph_core.mjs

test-network:
	$(PYTHON) -m pytest tests/test_hsp.py -v --run-network

clean:
	rm -f build/letters.jsonl build/entities.json build/manifest.json build/warnings.log
