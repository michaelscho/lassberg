#!/usr/bin/env python3
"""
Phase 5 helper: loads `rdf/edition.ttl` into a running Oxigraph instance (see docker-compose.yml,
`make sparql` starts one). Clears the default graph first so reruns are idempotent.

Usage:
    python scripts/load_oxigraph.py [--repo-root PATH] [--endpoint http://localhost:7878]
"""
from __future__ import annotations

import argparse
from pathlib import Path

import requests


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--endpoint", default="http://localhost:7878")
    args = parser.parse_args()

    ttl_path = args.repo_root / "rdf/edition.ttl"

    # Clear default graph for idempotency, then upload the dump.
    clear = requests.post(
        f"{args.endpoint}/query",
        data="CLEAR DEFAULT",
        headers={"Content-Type": "application/sparql-update"},
    )
    clear_update = requests.post(
        f"{args.endpoint}/update",
        data="CLEAR DEFAULT",
        headers={"Content-Type": "application/sparql-update"},
    )
    print(f"CLEAR DEFAULT: query={clear.status_code} update={clear_update.status_code}")

    with ttl_path.open("rb") as fh:
        resp = requests.post(
            f"{args.endpoint}/store?default",
            data=fh,
            headers={"Content-Type": "text/turtle"},
        )
    resp.raise_for_status()
    print(f"Loaded {ttl_path} into {args.endpoint} (status {resp.status_code})")

    count = requests.get(
        f"{args.endpoint}/query",
        params={"query": "SELECT (COUNT(*) AS ?n) WHERE { ?s ?p ?o }"},
        headers={"Accept": "application/sparql-results+json"},
    ).json()
    print("Triple count in store:", count["results"]["bindings"][0]["n"]["value"])


if __name__ == "__main__":
    main()
