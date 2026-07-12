#!/usr/bin/env python3
"""
Phase 3 of the KI-Infrastruktur pipeline: precomputes a 2D projection and cluster assignment of
the BGE-M3 letter embeddings, plus per-cluster labels (TF-IDF top terms + most-mentioned entities),
so the frontend can render a static scatterplot without running UMAP/HDBSCAN in the browser.

Output:
  clustering/umap_2d.json  - {letter_id: [x, y]}
  clustering/clusters.json - {"clusters": {"<label>": {"size", "top_terms", "top_entities"}},
                               "assignments": {letter_id: label}}
                              label -1 is HDBSCAN noise, kept (frontend renders it grey).

Default strategy (config.yaml: clustering.umap/hdbscan): UMAP reduces the 1024D embeddings to 50D
for clustering (HDBSCAN on cosine-ish euclidean space after UMAP), and *separately* to 2D for
visualization only - clustering never runs directly on the 2D projection, since collapsing to 2D
first discards structure HDBSCAN could otherwise use. `random_state` is fixed for both runs, so
reruns are deterministic and diffable.

Usage:
    python scripts/cluster.py [--repo-root PATH]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import numpy as np
import yaml
from safetensors.numpy import load_file
from sklearn.feature_extraction.text import TfidfVectorizer

import hdbscan
import umap

# Minimal German stopword list (function words only) - sklearn ships no German list; this is
# enough to keep TF-IDF top-terms from being dominated by "und", "die", "der", etc.
GERMAN_STOPWORDS = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines", "einem", "einen",
    "und", "oder", "aber", "auch", "als", "am", "an", "auf", "aus", "bei", "bis", "durch", "für",
    "gegen", "hinter", "in", "im", "ins", "mit", "nach", "neben", "ohne", "seit", "über", "um",
    "unter", "von", "vor", "während", "wegen", "zu", "zum", "zur", "zwischen", "ist", "sind",
    "war", "waren", "sein", "seine", "seiner", "seinen", "ihr", "ihre", "ihrer", "ihren", "ich",
    "sie", "wir", "er", "es", "man", "sich", "mich", "mir", "dich", "dir", "uns", "euch", "nicht",
    "kein", "keine", "so", "wie", "was", "wenn", "dass", "daß", "weil", "da", "doch", "noch",
    "nur", "schon", "sehr", "mehr", "hier", "dort", "diese", "dieser", "dieses", "diesem",
    "diesen", "welche", "welcher", "welches", "habe", "hat", "haben", "hatte", "hatten", "wird",
    "werden", "wurde", "wurden", "kann", "können", "könnte", "muss", "müssen", "soll", "sollen",
    "will", "wollen", "würde", "würden", "bin", "bist", "sind", "of", "the", "to", "and", "einem",
    "einer", "jener", "jene", "jenes", "immer", "wol", "wohl", "denn", "jedoch", "allein", "ganz",
    "sehr", "recht", "beym", "beim", "bey", "bei", "her", "hin", "wieder", "einmal", "etwas",
}


def load_config(repo_root: Path) -> dict:
    with (repo_root / "config.yaml").open() as fh:
        return yaml.safe_load(fh)


def load_embeddings(repo_root: Path) -> tuple[list[str], np.ndarray]:
    emb_dir = repo_root / "embeddings/bge-m3"
    ids = json.loads((emb_dir / "ids.json").read_text())
    matrix = load_file(str(emb_dir / "letters.safetensors"))["embeddings"].astype(np.float32)
    return ids, matrix


def load_letters(repo_root: Path) -> dict[str, dict]:
    letters = {}
    with (repo_root / "build/letters.jsonl").open(encoding="utf-8") as fh:
        for line in fh:
            rec = json.loads(line)
            letters[rec["id"]] = rec
    return letters


def load_entities(repo_root: Path) -> dict[str, dict]:
    entities = json.loads((repo_root / "build/entities.json").read_text())
    by_id = {}
    for bucket in entities.values():
        by_id.update(bucket)
    return by_id


def top_terms_per_cluster(texts_by_label: dict[int, list[str]], top_n: int = 10) -> dict[int, list[str]]:
    labels = sorted(texts_by_label.keys())
    docs = [" ".join(texts_by_label[l]) for l in labels]
    vectorizer = TfidfVectorizer(
        lowercase=True,
        token_pattern=r"(?u)\b[^\W\d_]{3,}\b",
        stop_words=list(GERMAN_STOPWORDS),
        max_df=0.9,
    )
    tfidf = vectorizer.fit_transform(docs)
    terms = np.array(vectorizer.get_feature_names_out())
    result = {}
    for i, label in enumerate(labels):
        row = tfidf[i].toarray().ravel()
        top_idx = row.argsort()[::-1][:top_n]
        result[label] = [terms[j] for j in top_idx if row[j] > 0]
    return result


def top_entities_per_cluster(letters: dict[str, dict], entities: dict[str, dict],
                              assignments: dict[str, int], top_n: int = 5) -> dict[int, list[dict]]:
    counts_by_label: dict[int, Counter] = {}
    for letter_id, label in assignments.items():
        rec = letters[letter_id]
        counter = counts_by_label.setdefault(label, Counter())
        for bucket in ("persons", "places", "works", "witnesses"):
            for eid in rec["mentions"][bucket]:
                counter[eid] += 1
    result = {}
    for label, counter in counts_by_label.items():
        top = []
        for eid, count in counter.most_common(top_n):
            ent = entities.get(eid)
            top.append({"id": eid, "label": ent["label"] if ent else eid, "count": count})
        result[label] = top
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()

    repo_root: Path = args.repo_root
    config = load_config(repo_root)
    umap_cfg = config["clustering"]["umap"]
    hdbscan_cfg = config["clustering"]["hdbscan"]

    ids, matrix = load_embeddings(repo_root)
    letters = load_letters(repo_root)
    entities = load_entities(repo_root)
    print(f"Loaded {len(ids)} letter embeddings ({matrix.shape[1]}d)")

    n_neighbors = min(umap_cfg["n_neighbors"], len(ids) - 1)

    # Clustering reduction: 50D (or fewer components than points allow)
    n_components_cluster = min(50, len(ids) - 2, matrix.shape[1])
    reducer_cluster = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=umap_cfg["min_dist"],
        metric=umap_cfg["metric"],
        n_components=n_components_cluster,
        random_state=umap_cfg["random_state"],
    )
    reduced_cluster = reducer_cluster.fit_transform(matrix)

    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=hdbscan_cfg["min_cluster_size"],
        min_samples=hdbscan_cfg["min_samples"],
        cluster_selection_method=hdbscan_cfg.get("cluster_selection_method", "eom"),
    )
    labels = clusterer.fit_predict(reduced_cluster)

    # Visualization reduction: separate 2D projection (not derived from the 50D clustering space)
    reducer_2d = umap.UMAP(
        n_neighbors=n_neighbors,
        min_dist=umap_cfg["min_dist"],
        metric=umap_cfg["metric"],
        n_components=2,
        random_state=umap_cfg["random_state"],
    )
    coords_2d = reducer_2d.fit_transform(matrix)

    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = int((labels == -1).sum())
    print(f"{n_clusters} clusters found, {n_noise} noise points (of {len(ids)})")

    assignments = {lid: int(label) for lid, label in zip(ids, labels)}
    umap_2d = {lid: [float(x), float(y)] for lid, (x, y) in zip(ids, coords_2d)}

    texts_by_label: dict[int, list[str]] = {}
    for lid, label in assignments.items():
        texts_by_label.setdefault(label, []).append(letters[lid]["text"] or "")

    top_terms = top_terms_per_cluster(texts_by_label)
    top_entities = top_entities_per_cluster(letters, entities, assignments)

    clusters_out = {}
    for label in sorted(texts_by_label.keys()):
        clusters_out[str(label)] = {
            "size": len(texts_by_label[label]),
            "top_terms": top_terms.get(label, []),
            "top_entities": top_entities.get(label, []),
        }

    clustering_dir = repo_root / "clustering"
    clustering_dir.mkdir(exist_ok=True)
    (clustering_dir / "umap_2d.json").write_text(json.dumps(umap_2d, ensure_ascii=False, indent=2), encoding="utf-8")
    (clustering_dir / "clusters.json").write_text(
        json.dumps({"clusters": clusters_out, "assignments": assignments}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote clustering/umap_2d.json and clustering/clusters.json ({n_clusters} clusters, {n_noise} noise)")


if __name__ == "__main__":
    main()
