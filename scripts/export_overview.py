#!/usr/bin/env python3
"""Exports the corpus-overview data for the Explore page (html/explore.html, Overview tab) to
json/explore/overview.json.

Unlike the embedding-based artifacts, this covers ALL letters in the register (register-only
included), because it is built purely from correspondence metadata: dates, correspondents, and
sending places. Every letter in the corpus involves Joseph von Laßberg himself
(lassberg-correspondent-0373), so "correspondent" here always means the other party.

Output shape:
  totals:             letters / fulltext / published / dated counts
  years:              {year: n} over all dated letters
  correspondents:     [{id, label, letters, from, to, years: {year: n}}], sorted by letter count
  places:             [{id, label, lat, lon, letters}] - effective sending place, coords required
  historical_persons: [{id, label, letters}] - persons register @type historical, counted by
                      distinct mentioning letters (mentions only exist for full-text letters)
  contemporary_persons, works, mentioned_places: same shape, from the other mention buckets
                      ("Unbekannt" register placeholders are skipped; mentioned_places carries
                      lat/lon like places and feeds the map's second layer)

Usage: python scripts/export_overview.py [--repo-root PATH]
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_pipeline import effective_sent_place, load_entities, load_letters  # noqa: E402

LASSBERG = "lassberg-correspondent-0373"


def year_of(letter: dict) -> int | None:
    date = letter["sent"]["date"] or letter["received"]["date"]
    if date and len(date) >= 4 and date[:4].isdigit():
        return int(date[:4])
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args()
    repo_root: Path = args.repo_root

    letters = load_letters(repo_root)
    entities = load_entities(repo_root)
    persons = entities["persons"]
    places = entities["places"]

    years = collections.Counter()
    corr_letters = collections.Counter()
    corr_years = collections.defaultdict(collections.Counter)
    corr_span = {}
    place_letters = collections.Counter()
    historical_mentions = collections.Counter()
    contemporary_mentions = collections.Counter()
    work_mentions = collections.Counter()
    mentioned_place_letters = collections.Counter()
    dated = fulltext = published = 0

    for letter in letters:
        if letter["has_fulltext"]:
            fulltext += 1
        if (letter.get("publication_status") or "").startswith("online"):
            published += 1

        partner = letter["sent"]["person"] if letter["received"]["person"] == LASSBERG else letter["received"]["person"]
        year = year_of(letter)
        if year:
            dated += 1
            years[year] += 1
            if partner:
                corr_years[partner][year] += 1
                lo, hi = corr_span.get(partner, (year, year))
                corr_span[partner] = (min(lo, year), max(hi, year))
        if partner:
            corr_letters[partner] += 1

        place = effective_sent_place(letter)
        if place:
            place_letters[place] += 1

        for pid in set(letter["mentions"]["persons"]):
            if persons.get(pid, {}).get("label") == "Unbekannt":
                continue  # register placeholder for unidentified persons
            ptype = persons.get(pid, {}).get("person_type")
            if ptype == "historical":
                historical_mentions[pid] += 1
            elif ptype == "contemporary":
                contemporary_mentions[pid] += 1
        for wid in set(letter["mentions"]["works"]):
            work_mentions[wid] += 1
        for plid in set(letter["mentions"]["places"]):
            mentioned_place_letters[plid] += 1

    correspondents = []
    for pid, n in corr_letters.most_common():
        span = corr_span.get(pid)
        correspondents.append({
            "id": pid,
            "label": persons.get(pid, {}).get("label") or pid,
            "letters": n,
            "from": span[0] if span else None,
            "to": span[1] if span else None,
            "years": dict(sorted(corr_years[pid].items())) if pid in corr_years else {},
        })

    place_rows = []
    for pid, n in place_letters.most_common():
        coords = places.get(pid, {}).get("coords")
        if not coords:
            continue
        place_rows.append({
            "id": pid,
            "label": places.get(pid, {}).get("label") or pid,
            "lat": coords["lat"],
            "lon": coords["lon"],
            "letters": n,
        })

    def person_rows(counter):
        return [{"id": pid, "label": persons.get(pid, {}).get("label") or pid, "letters": n}
                for pid, n in counter.most_common()]

    works = load_entities(repo_root)["works"]
    work_rows = [{"id": wid, "label": works.get(wid, {}).get("label") or wid, "letters": n}
                 for wid, n in work_mentions.most_common()]

    mentioned_place_rows = []
    for plid, n in mentioned_place_letters.most_common():
        coords = places.get(plid, {}).get("coords")
        if not coords:
            continue
        mentioned_place_rows.append({
            "id": plid,
            "label": places.get(plid, {}).get("label") or plid,
            "lat": coords["lat"],
            "lon": coords["lon"],
            "letters": n,
        })

    out = {
        "totals": {
            "letters": len(letters),
            "dated": dated,
            "fulltext": fulltext,
            "published": published,
            "correspondents": len(corr_letters),
            "places_mapped": len(place_rows),
        },
        "years": {str(y): n for y, n in sorted(years.items())},
        "correspondents": correspondents,
        "places": place_rows,
        "mentioned_places": mentioned_place_rows,
        "historical_persons": person_rows(historical_mentions),
        "contemporary_persons": person_rows(contemporary_mentions),
        "works": work_rows,
    }
    out_path = repo_root / "json/explore/overview.json"
    out_path.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {out_path} ({out_path.stat().st_size / 1024:.1f} KiB): "
          f"{len(letters)} letters, {dated} dated, {len(corr_letters)} correspondents, "
          f"{len(place_rows)} sending places, {len(mentioned_place_rows)} mentioned places, "
          f"{len(historical_mentions)} historical + {len(contemporary_mentions)} contemporary "
          f"persons, {len(work_rows)} works")


if __name__ == "__main__":
    main()
