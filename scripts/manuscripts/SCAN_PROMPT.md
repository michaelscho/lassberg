# Handschriften-Scan: Anleitung für Sonnet-Subagenten

Du liest Briefe aus der Laßberg-Korrespondenz (19. Jh., deutsch, oft mit historischer Orthografie)
und schlägst vor, welche Erwähnungen **bestimmter Handschriften** im Text als
`rs type="witness"` ausgezeichnet werden sollen. **Du schreibst kein TEI**, du lieferst nur
JSON-Vorschläge; ein Skript setzt sie um.

## Eingabe

Für jeden Brief: `.venv-infra/bin/python scripts/manuscripts/extract_letter.py <Brief-ID>`
(Text der Transkription; bestehendes Markup als `[[typ|register-id: Text]]`, z. B.
`[[object|: Colmarer codex]]`). Register-Kontext: `build/manuscripts/register_digest.tsv`
(id, msName, Ort, Signatur, frühere Signaturen). Zum Prüfen einer vermuteten Handschrift:
`.venv-infra/bin/python scripts/manuscripts/hsp_lookup.py "<Anfrage>" [--live]` (lokaler HSP-Index
über Beschreibungsinhalt, Autor, frühere Signatur, Provenienz; `--live` fragt das
Handschriftenportal, Achtung Rechtschreibkorrektur: Signatur/Titel selbst prüfen).

## Regeln

1. **`witness` = eine bestimmte, identifizierbare Handschrift** (Codex, Fragment,
   Sammelhandschrift), egal ob über Namen („Weingartner Codex“), Signatur („Cod. pal. 357“), Besitzer
   („Neukirchs Hs.“) oder Aufbewahrungsort genannt. Pronomen/Anaphern nicht auszeichnen.
2. **Werk vs. Handschrift:** „das Nibelungenlied“ ist ein Werk (nicht melden). „meine Handschrift der
   Nibelungen“ ist eine Handschrift. Nicht verschachteln.
3. **Unspezifische Nennungen** („eine alte Handschrift“, „einige Pergamentblätter“, „meine
   handschriften und bücher“) nicht melden. Spezifisch, aber nicht identifizierbar: melden mit
   `witness_id: null` und `proposed` nur mit dem, was der Text hergibt (nicht raten).
4. **Nicht melden:** Urkunden, Druckexemplare, gedruckte Sammlungen („Myllers Sammlung“), Editionen
   („Codex diplomaticus …“), Gemälde/Siegel/Reliquien.
5. Ist an der Stelle schon ein `[[object|…]]`, `[[misc|…]]` oder `[[bibl|…]]` markiert, das eine
   Handschrift meint: `action: "retype"`. Steht die Handschrift ohne Markup: `action: "wrap"`.
   Ist sie schon als `[[witness|…]]` mit einer `lassberg-witness-…`-ID markiert: nicht melden.
6. `quote` ist der Text **exakt** so, wie er in der Extraktion steht (ohne die `[[…]]`-Klammern), mit
   nur einem Leerzeichen zwischen Wörtern und **ohne Silbentrennung** (die Extraktion hat sie schon
   entfernt). Nimm die kürzeste Wortfolge, die die Handschrift bezeichnet („Colmarer liedercodex“,
   nicht den ganzen Satz). `occurrence` = wievielte Fundstelle dieses Textes im Brief (1 = erste).
7. Einträge im Register schon vorhanden (digest) → `witness_id` setzen. Sonst `witness_id: null` und
   `proposed` ausfüllen (`name` = moderne Bezeichnung, `hsp_query` = Suchbegriff fürs HSP).
   Hast du per `hsp_lookup` einen sicheren Treffer gefunden, trage `hsp_candidates` ein (Liste mit
   `hsp_id`, `shelfmark`, `msname`); das ersetzt aber nicht die Prüfung durch `resolve.py`.
8. **Nicht raten.** Im Zweifel `confidence` < 0.7 und `witness_id: null`.

## Ausgabe

Pro Brief **eine** Datei `build/manuscripts/proposals/<Brief-ID>.json` (auch leer):

```json
{"letter_id": "lassberg-letter-1743", "model": "claude-sonnet-5", "mentions": [
  {"quote": "Colmarer liedercodex", "occurrence": 1,
   "existing_rs": {"type": "object", "key": ""},
   "action": "retype",
   "manuscript": {"witness_id": null,
                  "proposed": {"name": "Kolmarer Liederhandschrift", "settlement": null,
                               "repository": null, "shelfmark": null,
                               "hsp_query": "Kolmarer Liederhandschrift"}},
   "confidence": 0.95,
   "rationale": "Kurze Begründung, keine längeren Zitate aus HSP-Beschreibungen."}]}
```

`existing_rs` ist bei `wrap` `null`. Kein Mention → `"mentions": []`. Gib am Ende nur eine kurze
Zusammenfassung (Anzahl Briefe, Anzahl Vorschläge, unsichere Fälle) zurück.

## Beispiele aus dem Korpus

1. Brief 1743: „der [[object|: Colmarer liedercodex]] wieder aufgefunden ist“ → `retype`, bestimmte
   Handschrift, identifizierbar (Name, Colmar).
2. Brief 1741: „[[object|: Handschriften]]“ (Plural, unspezifisch) → **nicht melden**.
3. Brief 1015: „[[bibl|: Codex trad. S. Gallensium]]“ (Urkundenbuch/Edition) → **nicht melden**.
