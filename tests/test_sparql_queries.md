# SPARQL smoke tests for rdf/edition.ttl

Three test queries required by PLAN_edition_ki_infrastruktur.md Phase 5's acceptance criteria.
Run against a local Oxigraph loaded via `scripts/load_oxigraph.py` (`make sparql`). Results below
were captured against the full corpus (2026-07-11) and should stay in the same ballpark after
re-parsing/re-linking letters; a large deviation signals a regression in export_rdf.py or the
underlying data.

These three queries must also produce identical results when run in the browser against Oxigraph-
WASM with the same `edition.ttl` (Phase 7b.2 smoke test) - same file, same store engine, no second
modelling.

## 1. All letters sent to/from a given person (Johann Adam Pupikofer, lassberg-correspondent-0179)

```sparql
PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
SELECT (COUNT(?letter) AS ?n) WHERE {
  ?letter csvoc:hasCorrespAction ?action .
  ?action csvoc:hasParticipant <https://michaelscho.github.io/lassberg/person/lassberg-correspondent-0179> .
}
```

Result: **143** letters (sent or received).

## 2. All letters mentioning a given place (Eppishausen, lassberg-place-0043)

```sparql
PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
SELECT (COUNT(?letter) AS ?n) WHERE {
  ?letter csvoc:mentions <https://michaelscho.github.io/lassberg/place/lassberg-place-0043> .
}
```

Result: **37** letters.

## 3. Letters per year

```sparql
PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
SELECT ?year (COUNT(?letter) AS ?n) WHERE {
  ?letter csvoc:hasCorrespAction ?action .
  ?action csvoc:hasTimespan ?ts .
  ?ts csvoc:startsOn ?date .
  BIND(SUBSTR(STR(?date), 1, 4) AS ?year)
} GROUP BY ?year ORDER BY ?year
```

Result (excerpt, full corpus spans 1788-1855-ish): 1788: 3, 1789: 2, 1792: 4, 1793: 1, 1795: 4,
1796: 2, 1798: 2, 1799: 3, 1800: 3, 1801: 2, 1802: 18, 1803: 8, 1804: 9, 1805: 26, 1806: 20, ...
plausible - no single year dominates implausibly, no all-zero years in the active correspondence
period.
