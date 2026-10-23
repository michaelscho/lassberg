# Plan: Handschriften erschließen, registrieren und mit dem Handschriftenportal (HSP) verknüpfen

Umsetzung durch Sonnet 5 in Claude Code. Erstellt 2026-09-30 (Opus 5.5) auf Basis von
`task_opus5.md` und einer Bestandsaufnahme des Repos. Entscheidungen des Projektleiters sind in
Abschnitt 1 festgehalten und **nicht erneut zur Diskussion zu stellen**.

**Tagesziel (Definition of Done, s. Abschnitt 9):** Eine Abfrage „Welche Briefe erwähnen die
Kolmarer Liederhandschrift, und was verzeichnet das HSP zu ihr?“ liefert über MCP (und äquivalent
per SPARQL) die tatsächlich annotierten Briefe des Laßberg–Wackernagel-Briefwechsels plus die
live aus dem HSP geholten Daten zu HSP-666242f4-0675-3121-b0d6-be697c7a9b20 (München, BSB,
Cgm 4997). Kein Mockup: Im Code darf weder „Kolmar“ noch die HSP-ID hart kodiert sein; beides steht
ausschließlich in `data/` (und in Test-Erwartungen).

Reihenfolge für heute: **Phase 0 → 1 (kurz) → 2 → 3 → 4 → 6a/6b**. Der Vollspiegel aller
Beschreibungen (3b) läuft ca. 10–15 Minuten bei 1 Anfrage/s und kann im Hintergrund laufen.
Die Phasen 5, 6c/6d, 7 und 8
folgen danach.

---

## 1. Getroffene Entscheidungen

| Frage | Entscheidung |
|---|---|
| Registerort | **Eigenes Handschriftenregister** `data/register/lassberg-manuscripts.xml`, schlanke `<msDesc>` in `<listBibl>`. Die Handschriften unter den `bibl type="charter"`-Einträgen im Literaturregister werden dorthin migriert; **Urkunden und Druckexemplare bleiben** als `type="charter"` im Literaturregister. Das revidiert die Festlegung vom 2026-07-14 in `docs/TEI.md`. |
| LLM für den Nachscan | **Sonnet 5 in Claude Code** (Subagenten in Batches), kein SAIA-Skript. |
| Freigabe | **Automatisch anwenden**, auch in `reviewed`/`published`-Briefen. Nachvollziehbarkeit über `@resp`, Log-Datei und Git-Commits pro Batch (s. Phase 4/5). |
| HSP-Daten | **Lokaler Spiegel** aller HSP-Kulturobjekte und -Beschreibungen der registrierten Handschriften in `data/hsp/`, **gitignored** (Lizenzen, s. u.). Er dient der Identifizierung im Workflow, MCP und dem Website-Export. Grund: Das HSP sendet keine CORS-Header (geprüft 2026-09-30), und eine offizielle API ist erst mittelfristig angekündigt. Deshalb kein Proxy; der Client wird später auf die offizielle API umgestellt. |
| Website | Statisch, **pro Handschrift nachgeladen**. Öffentlich (`json/hsp/`, GitHub Pages) nur **frei lizenzierte** Inhalte (Lizenz-Gate). **Lokal ohne Einschränkung** über die gitignorte Vollversion `json/hsp-local/`, die das Frontend automatisch bevorzugt (Phase 6c). |

## 2. Bestandsaufnahme (Stand 2026-09-30, verifiziert)

- `lassberg-manuscripts.xml` existiert, ist aber leer (nur eine auskommentierte `<listWit>/<witness>`-Vorlage).
- Die Pipeline kennt Handschriften bereits halb: `scripts/parse_tei.py::parse_manuscripts()`
  liest `<witness>`, `scripts/lib_pipeline.py` bildet das ID-Präfix `lassberg-witness-` auf
  `Witness` ab, `export_cypher/export_rdf/export_graph_json` exportieren Witness-Knoten, und
  `js/explore/graph.js` hat eine Witness-Farbe. `parse_mentions()` ordnet
  `cmif:mentionsBibl`-Ziele mit Präfix `lassberg-witness-` dem Bucket `witnesses` zu.
  → **ID-Präfix `lassberg-witness-NNNN` und `rs type="witness"` beibehalten**, damit diese Kette
  ohne Umbenennung weiter funktioniert.
- Im Korpus (281 Briefdateien): 6× `rs type="witness"` (alle mit Key ins Literaturregister),
  101× `object`, 249× `misc`, 374× `bibl`. Handschriften stecken vor allem in `object`/`misc`,
  zum Teil sind sie gar nicht ausgezeichnet.
- Kolmar-Stellen: Briefe **1730, 1737, 1741, 1743** (Laßberg ↔ Wackernagel, 1833, alle
  `published`, `div type="original"`) mit `<rs type="object" key="">Colmarer … codex</rs>`;
  **1064** (Uhland an Laßberg, 1826, `div type="print"`, `draft`): „der Kolmarer Handschrift nachspüren“,
  nicht ausgezeichnet. Nur die Transkriptions-`div` trägt `<rs>`; normalisierte Fassung, Übersetzung und
  Zusammenfassung bleiben unausgezeichnet und unangetastet.
- 44 Briefdateien gehören zum Wackernagel-Briefwechsel (`lassberg-correspondent-0367`) → Pilotkorpus.
- Die 8 `type="charter"`-Einträge im Literaturregister umfassen Handschriften (u. a. 0230 Weingartner
  Liederhs., 0231 Cpg 350, 0232 Cpg 357, 0234 Nibelungen C) und Urkunden (u. a. 0227, 0228).
- Excel `data/temp/Handschriften BLB Laßberg.xlsx`:
  - `Tabellenblatt1` (82 Zeilen): Teilliste mit Laßberg-Nummern. Spalten `Signatur`
    (**Formel** `="Cod. Donaueschingen "&C`), `[Nummer Signatur]`, `[Nummer Laßberg]`, dazu HSP-IDs
    und Permalinks (ebenfalls Formeln, VLOOKUP auf `HSP-Abzug`).
  - `HSP-Abzug` (287 Zeilen): `Signatur`, `Besitzende Einrichtung`, `Ort`, `HSP-ID-Kulturobjekt`,
    `GND-ID`, `HSP-ID-Beschreibung`, `PURL`, …
  - `HSP-Abzug 2` (289 Zeilen): Beschreibungen mit Autor:in, Status, IDs.
  - Alle Handschriften der Tabelle stammen aus Laßbergs Besitz und kommen vollständig ins Register.
  - **Die Kolmarer Hs. steht nicht in der Tabelle** (sie liegt in München). Das Register muss also auch
    Handschriften außerhalb der BLB aufnehmen, und für sie braucht es einen HSP-Lookup.
  - Lesen mit `.venv/bin/python` (hat `openpyxl`) und `load_workbook(..., data_only=True)`. Fehlen
    die gecachten Formelwerte (`None`), den Join selbst nachbauen: Signatur =
    `"Cod. Donaueschingen " + str(int(Nummer Signatur))`, Nachschlagen in `HSP-Abzug` über `Signatur`.
- HSP-API: undokumentiert, aber funktionsfähig (alle Endpunkte am 2026-09-30 live geprüft):

  | Endpunkt | Liefert |
  |---|---|
  | `GET https://handschriftenportal.de/api/kods/search?q=<text>` | JSON `{payload:[KOD…], metadata:{numFound,rows,start}}`; findet „Kolmarer“ → Cgm 4997 |
  | `GET https://handschriftenportal.de/api/kods/<HSP-ID>` | JSON-Kerndaten: `settlement-display`, `repository-display`, `idno-display`, `title-display`, `orig-date-lang-display`, `orig-place-display`, `leaves-count-display`, `material-display`, … |
  | `GET https://handschriftenportal.de/api/tei/<HSP-ID des Kulturobjekts>` | TEI (~11 KB) des Kulturobjekts; `<ptr type="purl">` und `<index copyOf="#HSP-…">` verweisen auf die IDs der Beschreibungen |
  | `GET https://handschriftenportal.de/api/tei/<HSP-ID der Beschreibung>` | Volle Katalogbeschreibung als TEI; bei Kolmar HSP-1963f105-df95-39ea-b821-2e294e9e53b1, 424 KB, Schneider 1996, S. 425–446 |
  | Menschenlesbare Seite | `https://handschriftenportal.de/search?hspobjectid=<HSP-ID>` |

  **Lizenzen (geprüft):** Das TEI des Kulturobjekts trägt CC0 (`availability status="free"`). Die
  Beschreibung der Kolmarer Hs. (Retrokonversion des gedruckten Katalogs Schneider 1996) trägt
  dagegen `availability status="restricted"` und `rightsstatements.org/vocab/InC/1.0/` (In
  Copyright). Die Lizenz wird **pro Beschreibung** aus `teiHeader//availability` gelesen, nie
  angenommen.
  Größe: 8 zufällige Donaueschinger Beschreibungen haben 17–76 KB TEI (Schnitt ca. 40 KB), alle
  ca. 290 zusammen also grob 12 MB.
  Kein CORS, erlaubte Methoden GET/HEAD. Die Suche macht Rechtschreibkorrektur
  (`spellCorrectedTerm`), deshalb Treffer immer auf exakte ID bzw. Signatur prüfen.

## 3. Annotationsschema (Ziel)

Einfach halten und an Bestehendes anlehnen: `<rs>` wie bei Personen, Orten und Werken, CMIF
`mentionsBibl` in `<note type="mentioned">`, `msIdentifier` nach TEI-msDesc (wie das HSP selbst).

### 3.1 Im Brief (nur in der Transkriptions-`div`, `type="original"` oder `type="print"`)

```xml
Nun bin ich doch frohe, daß der <rs type="witness"
    key="../register/lassberg-manuscripts.xml#lassberg-witness-0001"
    resp="#manuscript-scan">Colmarer liedercodex</rs> wieder aufgefunden ist.
```

In `<correspDesc><note type="mentioned">` (einmal pro Handschrift und Brief):

```xml
<ref type="cmif:mentionsBibl" target="../register/lassberg-manuscripts.xml#lassberg-witness-0001"
    ><rs>Kolmarer Liederhandschrift</rs></ref>
```

Regeln (Phase 1 prüft sie an der Stichprobe und darf sie präzisieren, nicht verkomplizieren):

1. **`witness` = eine bestimmte, identifizierbare Handschrift** (Codex, Fragment,
   Sammelhandschrift), egal ob über den Namen („Weingartner Codex“), die Signatur („Cod. pal. 357“),
   den Besitzer („Neukirchs Hs.“) oder den Aufbewahrungsort genannt. Pronomen und Anaphern werden
   nicht ausgezeichnet.
2. **Werk vs. Handschrift:** „das Nibelungenlied“ → `rs type="bibl"` (Literaturregister). „meine
   Handschrift der Nibelungen“ → `rs type="witness"`. Nicht verschachteln; der Werkbezug steht im
   Register (`msItem/title/@key`).
3. **Unspezifische Nennungen** („eine alte Handschrift“, „einige Pergamentblätter“) werden **nicht**
   ausgezeichnet. Ist eine Handschrift **spezifisch, aber nicht identifizierbar**, gilt
   `rs type="witness" key=""` (bestehende Konvention: nicht raten).
4. **Urkunden und Druckexemplare** bleiben `rs type="witness"` mit Key auf einen
   `bibl type="charter"` im **Literaturregister** (unverändert). Das Zielregister ergibt sich
   aus dem Key.
5. Bestehendes `rs type="object"|"misc"|"bibl"`, das eigentlich eine Handschrift meint, wird
   **umtypisiert** (`@type` → `witness`, `@key` setzen), nicht neu verschachtelt.
6. Maschinell gesetzte oder geänderte `<rs>` bekommen `resp="#manuscript-scan"`
   (`att.global.responsibility`). **Kein** neuer `<change>` in `revisionDesc`: Ein `<change>` ohne
   bzw. mit wiederholtem `@status` würde das Statusmodell brechen (`parse_tei.letter_status()`
   liest den letzten `change/@status`, `published` darf nur `sync_letter_status.py` setzen).

### 3.2 Im Register `lassberg-manuscripts.xml`

`<listWit>` wird durch `<listBibl>` ersetzt (`msDesc` ist in `listBibl` erlaubt). Pflicht ist nur
`msIdentifier`, alles andere ist optional:

```xml
<listBibl>
    <msDesc xml:id="lassberg-witness-0001">
        <msIdentifier>
            <settlement>München</settlement>
            <repository>Bayerische Staatsbibliothek</repository>
            <idno type="shelfmark">Cgm 4997</idno>
            <altIdentifier type="hsp"><idno>HSP-666242f4-0675-3121-b0d6-be697c7a9b20</idno></altIdentifier>
            <msName>Kolmarer Liederhandschrift</msName>
        </msIdentifier>
        <!-- optional: -->
        <msContents><msItem><title key="../register/lassberg-literature.xml#lassberg-literature-NNNN">…</title></msItem></msContents>
        <history><provenance>…</provenance></history>
        <note>Identifizierung/Quelle, z. B. „Im Brief als ‚Neukirchs Hs.‘ bzw. ‚Colmarer codex‘ (Briefe 1730–1743)“</note>
    </msDesc>
</listBibl>
```

- `altIdentifier/@type`: `hsp` (HSP-ID des **Kulturobjekts**), optional `handschriftencensus`,
  `gnd`, `former` (frühere Signatur, z. B. Laßberg-Nummer als `<idno type="lassberg">`).
- HSP-IDs der **Beschreibungen** kommen **nicht** ins Register. Sie werden zur Laufzeit bzw. zur
  Build-Zeit aus `/api/tei/<KOD-ID>` gelesen, weil sie sich im HSP ändern können.
- Laßbergs Besitz: `<history><provenance>Sammlung Laßberg (Laßberg-Nr. 174)</provenance></history>`.
- `@ana="needs-review"` wie in den übrigen Registern, wenn die Identifizierung unsicher ist.
- Kein `@type` nötig, das Register enthält nur Handschriften.

## 4. Phasen

### Phase 0: Entscheidungen dokumentieren (klein, zuerst)

- `docs/TEI.md`, Abschnitt „Handschriften- und Druckexemplare, Urkunden (Textzeugen)“: Die Regelung
  vom 2026-07-14 für Handschriften ersetzen durch Abschnitt 3 dieses Plans. Für Urkunden und
  Druckexemplare bleibt sie bestehen. Zusammenfassungstabelle (`witness` → Zielregister) und die
  Tabelle „Drei Ebenen“ anpassen.
- `CLAUDE.md`: `lassberg-manuscripts.xml` in der Registerliste unter `data/` ergänzen.
- `scripts/parse_tei.py`, Modul-Docstring Zeilen ~37–46: Beschreibung auf `msDesc` aktualisieren.

### Phase 1: Stichprobenanalyse der Annotation (Aufgabe 1)

Ziel: das Schema aus Abschnitt 3 am Material prüfen, nicht neu erfinden.

1. Stichprobe von ca. 25 Briefen, geschichtet: 10 aus dem Wackernagel-Briefwechsel, der Rest verteilt
   auf die großen Korrespondenzen (Uhland, Grimm, Pupikofer, Meyer von Knonau u. a., per
   `build/letters.jsonl` ermitteln), gemischt `original`/`print` und `draft`/`published`.
2. Zusätzlich alle 101 `rs type="object"`, die 6 `witness` sowie `misc`/`bibl`-Treffer mit
   Handschriften-Stichwörtern (Regex, case-insensitive: `handschrift|hs\.|hss\.|codex|cod\.|
   manuscript|msc?\.|pergament|membran|fragment|abschrift|liederbuch|sammlung`) als Tabelle erfassen.
3. Ergebnis: `docs/analysis/handschriften-stichprobe.md` mit
   - Häufigkeiten: wie Handschriften heute ausgezeichnet sind (object/misc/bibl/witness/gar nicht),
   - 10–15 typischen Belegen, jeweils mit Entscheidung nach Abschnitt 3,
   - einer Liste der Grenzfälle mit Regelvorschlag (nur Präzisierungen, keine neuen Elemente).
4. Wenn Regeln präzisiert werden, Abschnitt 3.1 dieses Plans **und** `docs/TEI.md` nachziehen.

Zeitbudget: kurz. Für das Tagesziel reicht es, die Wackernagel-Briefe und die `object`-Liste
auszuwerten.

### Phase 2: Register und Parser

1. **Schema**: `lassberg-manuscripts.xml` auf `<listBibl>` mit `<msDesc>` umstellen (Header bleibt).
   Die Vorlage als Kommentar nach Abschnitt 3.2 aktualisieren.
2. **Parser** `scripts/parse_tei.py::parse_manuscripts()`: `tei:msDesc` statt `tei:witness` lesen.
   Das Rückgabeformat bleibt kompatibel und wird erweitert:
   `{id, type:"witness", label (msName, sonst "settlement, repository, shelfmark"), settlement,
   repository, signature (idno[@type='shelfmark']), hsp_id, alt_ids:{…}, corresp (erster
   msItem/title/@key), provenance, note}`. Die Felder `witness_type` und `note` weiter befüllen
   (`witness_type="manuscript"`), damit `lib_pipeline.witness_properties()` nicht bricht.
   `witness_properties()` um `hsp_id` erweitern.
3. **Hilfsskript** `scripts/manuscripts/next_id.py` (oder den bestehenden
   `.claude/skills/add-register-entry/scripts/next_id.py` um `manuscripts` erweitern) und
   `scripts/manuscripts/register.py` mit `add_msdesc(entry: dict) -> id`, das Einträge
   formatierungsschonend anhängt (lxml, gleiche Einrückung wie die anderen Register).
4. **Excel-Import** `scripts/manuscripts/import_blb_excel.py`: **alle** Handschriften der Tabelle
   kommen ins Register, alle stammen aus Laßbergs Besitz (Vorgabe des Projektleiters vom 2026-09-30).
   - Grundmenge ist die Vereinigung von `HSP-Abzug` (287) und `HSP-Abzug 2` (289) über `Signatur`,
     entdoppelt. Die Abweichung der Zeilenzahlen wird im Importbericht aufgeschlüsselt: Welche
     Signaturen stehen nur in einem der beiden Blätter?
   - `Tabellenblatt1` (82) liefert nur die Zusatzinfo `[Nummer Laßberg]`. Signaturen, die dort
     stehen, aber in keinem HSP-Abzug vorkommen, werden trotzdem angelegt (ohne HSP-ID, mit
     `ana="needs-review"`).
   - Pro Handschrift ein `msDesc`: settlement und repository aus `Ort`/`Besitzende Einrichtung`,
     shelfmark aus `Signatur`, `altIdentifier type="hsp"` = `HSP-ID-Kulturobjekt`, `gnd` falls
     vorhanden, Laßberg-Nummer (falls bekannt) als `altIdentifier type="former"`.
   - `<provenance>`: „Sammlung Laßberg“, gegebenenfalls mit Laßberg-Nummer.
   - `msName` bleibt leer, er wird in Phase 3 aus `title-display` des HSP ergänzt.
   - Die Beschreibungs-IDs (`HSP-ID-Beschreibung`) kommen nicht ins Register (s. 3.2). Sie werden
     aber mit der ganzen Tabelle als `data/indices/hsp_blb_donaueschingen.json` abgelegt
     (`data/indices/` ist gitignored, die Datei lässt sich aus der Excel-Tabelle neu erzeugen) und
     dienen dem Abgleich in Phase 3.
   - Idempotent: Existiert ein Eintrag mit gleicher HSP-ID oder Signatur, wird er übersprungen.
5. **Migration** der Handschriften unter den 8 `bibl type="charter"`-Einträgen (0230, 0231, 0232,
   0234; alle 8 prüfen). Jeweils `msDesc` anlegen bzw. auf den Excel-Import mappen (Nibelungen C =
   Cod. Donaueschingen 63, Laßberg-Nr. 174, steht in `Tabellenblatt1`), dann **alle** Verweise in
   `data/letters/*.xml` (`rs/@key` und `ref/@target`) umhängen (`grep -rn "lassberg-literature-0230"`
   usw.). Den alten `bibl` erst löschen, wenn der grep leer ist. IDs werden nicht neu vergeben.
6. **Tests** in `tests/test_pipeline.py`: Fixture mit zwei `msDesc` (einer mit HSP-ID) →
   `parse_manuscripts` liefert die erwarteten Felder. `make test` muss grün sein.

### Phase 3: HSP-Client, lokaler Spiegel und Suchindex

**3a: Client** `scripts/lib_hsp.py`, geteilt von Skripten, MCP und Website-Export. Nur
Standardbibliothek plus `requests` und `lxml`, beides in `.venv-infra` prüfen und sonst in
`requirements-infra.txt` ergänzen. **Einzige Stelle mit HSP-URLs**, damit die angekündigte
offizielle API später nur hier eingebaut werden muss.

- `search(q, rows=10) -> list[dict]` über `/api/kods/search?q=`. Prüfen, ob `rows`/`start` als
  Parameter wirken; sonst clientseitig kürzen.
- `get_kod(hsp_id) -> dict` über `/api/kods/<id>`; `get_tei(id) -> bytes` über `/api/tei/<id>`.
- `description_ids(kod_tei) -> list[str]` aus `//tei:index/@copyOf`, entdoppelt, ohne `#`.
- `portal_url(hsp_id)` → `https://handschriftenportal.de/search?hspobjectid=<id>`.
- Eigener User-Agent (`lassberg-edition (+https://michaelscho.github.io/lassberg/)`), höchstens
  1 Anfrage/s, Timeout 30 s, klare Fehlermeldung bei Nicht-200.

**3b: Lokaler Spiegel** `data/hsp/`, **in `.gitignore` aufnehmen, bevor die erste Datei
geschrieben wird** (Lizenzen). Struktur:

```
data/hsp/kod/<KOD-ID>.json     # /api/kods/<id>, unverändert
data/hsp/kod/<KOD-ID>.xml      # /api/tei/<KOD-ID>, unverändert
data/hsp/desc/<DESC-ID>.xml    # /api/tei/<DESC-ID>, volle Beschreibung, unverändert
data/hsp/manifest.json         # pro ID: witness_id, kind (kod|desc), fetched_at, sha256,
                               # source_url, licence_url, licence_status (free|restricted|unknown)
```

- `scripts/manuscripts/mirror_hsp.py` (Make-Target `hsp-mirror`, Netzwerk, **nicht** in `make all`):
  holt für jeden `msDesc` mit HSP-ID Kulturobjekt, Kulturobjekt-TEI und **alle** Beschreibungen.
  Inkrementell (vorhandene Dateien überspringen), `--refresh` erzwingt ein Neuladen,
  `--add <HSP-ID>` spiegelt eine einzelne Handschrift (wird von `resolve.py` aufgerufen, wenn eine
  neue Handschrift außerhalb der BLB-Liste ins Register kommt, z. B. Kolmar).
  Am Ende Bericht: Anzahl, fehlgeschlagene IDs, Verteilung der Lizenzen.
- Lizenz aus `teiHeader//availability/@status` und `licence/@target` jeder Datei ins Manifest.

**3c: Aufbereitung** `lib_hsp.parse_description(xml) -> dict` (arbeitet nur auf lokalen Dateien):
Katalogzitat (`titleStmt/title`), `msIdentifier` (inklusive `altIdentifier`, also **frühere
Signaturen**, wichtig für alte Donaueschinger oder Laßberg-Nummern in den Briefen), `head`,
`msContents/summary`, alle `msItem` (locus, author, title, incipit), `physDesc` kurz, `history`
(origin, provenance, acquisition), Personen/Orte/Werke aus den Norm-Indizes (`index`/`term`,
`persName`/`placeName` mit GND-Refs), `additional/listBibl`, bereinigter Volltext sowie
`licence_url`/`licence_status`.

**3d: Lokaler Suchindex für die Identifizierung** `scripts/manuscripts/build_hsp_index.py` →
`data/hsp/index.sqlite` (ebenfalls gitignored), SQLite **FTS5** (in `.venv-infra` verfügbar,
geprüft). Eine Zeile pro Handschrift mit den Spalten shelfmark, former_shelfmarks, msname, title,
date, orig_place, authors_works (msItem), persons, provenance, fulltext.
`lib_hsp.local_search(query, limit=10) -> [{hsp_id, witness_id, shelfmark, msname, score,
snippet}]`: Ist die Anfrage signaturartig (Regex auf `Cod.`, `Cgm`, `Nr.`, Zahlen), zuerst exakter
bzw. Fuzzy-Treffer auf shelfmark/former_shelfmarks (`rapidfuzz`), sonst FTS5-BM25 mit
`snippet()`. Kommandozeile für Sonnet und Menschen: `scripts/manuscripts/hsp_lookup.py "<anfrage>"
[--live]`. `--live` ergänzt Treffer aus `lib_hsp.search` für Handschriften, die noch nicht im Spiegel
sind.

**3e: Abgleich** `scripts/manuscripts/enrich_from_hsp.py` (nur lokal): leeren `msName` aus
`title-display` füllen (typografische Anführungszeichen ‘…’ entfernen), settlement, repository und
Signatur gegen das HSP abgleichen und Abweichungen nur protokollieren. Für `msDesc` ohne HSP-ID
`hsp_lookup --live "<settlement> <shelfmark>"` und nur bei genau einem Treffer mit identischer
Signatur und identischem Ort die ID eintragen. Alles andere geht in
`build/manuscripts/hsp_unresolved.md`.

**Tests**: `tests/test_hsp.py`. Offline-Teil mit einer **selbst gebauten Minimal-TEI** als
Fixture (keine echten HSP-Beschreibungen einchecken: Lizenz!) für `parse_description` und
`local_search`. Netzwerk-Teil mit `@pytest.mark.network` gegen die Kolmar-ID (erwartet:
`idno-display == "Cgm 4997"`, mindestens eine Beschreibungs-ID).

### Phase 4: Pilot-Nachscan Wackernagel-Briefwechsel (Aufgabe 2, Teil 1; Tagesziel)

Werkzeugkette mit strikter Arbeitsteilung: **Das LLM schlägt vor, der Code schreibt.** Sonnet
editiert das TEI nicht frei.

1. **Vorschlagsformat** `build/manuscripts/proposals/<letter-id>.json`:
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
      "rationale": "Laßberg spricht von einem bestimmten, wiedergefundenen Meisterliedercodex aus Colmar."}]}
   ```
   `quote` ist der exakte Textinhalt der Transkriptions-`div` mit normalisiertem Leerraum und ohne
   Silbentrennung an `<lb break="no"/>`. `action` ist entweder `retype` (bestehendes `<rs>`) oder
   `wrap` (bisher nicht ausgezeichnet).
2. **Scan-Anleitung** als Datei `scripts/manuscripts/SCAN_PROMPT.md`: Abschnitt 3.1 dieses Plans,
   das JSON-Schema, drei Beispiele aus Phase 1 und der Hinweis „nicht raten, lieber `witness_id:
   null` mit `proposed`-Angaben“. Liste der vorhandenen Register-Handschriften als Kontext
   mitgeben: `build/manuscripts/register_digest.tsv` (id, msName, settlement, shelfmark), erzeugt
   aus dem Register. Die Subagenten dürfen `scripts/manuscripts/hsp_lookup.py` selbst aufrufen, um
   eine vermutete Handschrift schon beim Lesen zu prüfen, und schreiben das Ergebnis dann als
   `witness_id` bzw. `hsp_candidates` in den Vorschlag.
3. **Scan**: Sonnet-Subagenten mit je ca. 8–10 Briefen. Eingabe ist der Text der Transkriptions-`div`
   inklusive vorhandenem `<rs>`-Markup (vom Skript `scripts/manuscripts/extract_letter.py <id>`
   erzeugt, damit bestehende `rs` sichtbar sind). Ausgabe: eine Vorschlagsdatei pro Brief, auch
   wenn sie leer ist (`"mentions": []`), damit Vollständigkeit prüfbar bleibt.
4. **Auflösung** `scripts/manuscripts/resolve.py`: Vorschläge ohne `witness_id` durchlaufen drei
   Stufen: (a) Fuzzy-Match gegen das Register (`rapidfuzz`, msName und Signatur, Schwelle 92 wie in
   `link_entities_llm.py`), (b) `lib_hsp.local_search` über den **lokalen Beschreibungsindex**
   (findet Laßberg-Handschriften auch über Inhalt, Autor, frühere Signatur oder Provenienz, wenn der
   Brief keinen Namen nennt, z. B. „meine Hs. mit dem Schwabenspiegel“), (c) erst dann
   `lib_hsp.search(hsp_query)` live für Handschriften außerhalb des Bestands. Bei eindeutigem
   Treffer in (c) neuen `msDesc` mit HSP-ID anlegen und `mirror_hsp.py --add` aufrufen. Bei mehreren Kandidaten **Sonnet** entscheiden lassen (Kontext +
   Kandidatenliste inklusive der `snippet`s aus dem lokalen Index; die Entscheidung mit kurzer
   Begründung ins Vorschlags-JSON schreiben, **ohne** längere Zitate aus HSP-Beschreibungen, weil
   `build/manuscripts/` versioniert wird). Ohne Treffer
   `msDesc` mit `ana="needs-review"` und nur den bekannten Angaben anlegen, oder `key=""`, wenn
   nicht einmal die Identität sicher ist. Gleiche Handschrift in mehreren Briefen → **ein**
   Registereintrag (vor dem Anlegen immer erneut gegen das Register matchen).
5. **Anwenden** `scripts/manuscripts/apply_proposals.py [--dry-run] <ids…|--all>`:
   - lxml, Textsuche nur in `div[@type='original' or @type='print']`,
   - `retype`: vorhandenes `<rs>` finden (Text + occurrence), `@type`/`@key`/`@resp` setzen,
   - `wrap`: Treffer darf leere Inline-Elemente (`<lb/>`, `<pb/>`) überspannen, sie wandern mit ins
     `<rs>`. Treffer, die nicht-leere Elemente nur teilweise überlappen → **überspringen und
     protokollieren**, nicht reparieren,
   - `<note type="mentioned">` um den `ref`-Eintrag ergänzen (ohne Duplikate); fehlt die Note,
     wird sie wie in `data/letter_template.xml` angelegt,
   - Serialisierung formatierungsschonend (Muster: bestehende Skripte, die Briefe schreiben, z. B. im
     Skill `check-letter-annotations`). Danach Diff-Stichprobe ansehen: keine Umformatierung ganzer
     Dateien.
   - Log `build/manuscripts/applied.jsonl` (Brief, Aktion, Quote, Ziel-ID, Konfidenz) und Bericht
     `build/manuscripts/report.md` (Zähler, übersprungene Treffer, alle mit `confidence < 0.7`).
6. **Validierung** nach dem Anwenden: alle geänderten Briefe gegen TEI parsen (wohlgeformt),
   `make status` (keine neuen Konflikte), `make parse` (keine neuen `register-missing`-Warnungen
   in `build/warnings.log`).
7. **Commit** mit Log-Auszug in der Nachricht, getrennt pro Batch (Git ist das Sicherheitsnetz für
   „automatisch anwenden“).

Erwartung für Kolmar: Die Briefe 1730, 1737, 1741 und 1743 haben ihre `rs type="object"` umtypisiert,
1064 ist neu ausgezeichnet („der Kolmarer Handschrift“), alle zeigen auf **denselben**
`lassberg-witness-NNNN`. Dessen HSP-ID stammt aus `resolve.py` → `lib_hsp.search()` (Stufe c, denn
Kolmar liegt nicht im BLB-Bestand), nicht aus einer Handeingabe. Danach ist sie über
`mirror_hsp.py --add` lokal gespiegelt. Brief 1064 (Uhland) gehört nicht zum Wackernagel-Briefwechsel und kommt deshalb
**explizit** mit in den Pilotbatch. Weitere Kolmar-Stellen findet `grep -il "kolmar\|colmar"`.

### Phase 5: Vollscan aller übrigen Briefe (Aufgabe 2, Teil 2)

Gleiche Kette wie Phase 4 für alle übrigen ~237 Briefdateien, in Batches von ca. 25 Briefen, mit
einem Commit pro Batch. Reihenfolge: zuerst Briefe mit Treffern der Stichwort-Regex oder mit
`rs type="object"`, dann der Rest (auch Briefe ohne Treffer werden gelesen, weil Handschriften oft
nur mit Namen genannt werden, z. B. „der Weingartner“). Danach `enrich_from_hsp.py` erneut laufen
lassen und `build/manuscripts/hsp_unresolved.md` dem Projektleiter vorlegen (das ist der einzige
manuelle Schritt).

Neue Briefe aus der `src/`-Pipeline: ist laut Memory bewusst **nicht** Teil dieses Plans (die
Encoding-Pipeline wird später überarbeitet). In `docs/TEI.md` vermerken, dass neue Briefe über den
Scan-Workflow nachgezogen werden.

### Phase 6: Analytischer Zugriff (Aufgabe 5)

**6a: RDF/Graph** (heute)
- `scripts/export_rdf.py`, Witness-Block (~Zeile 172): zusätzlich `voc:hspId "HSP-…"`,
  `rdfs:seeAlso <portal_url>`, `dcterms:identifier` (Signatur), `voc:settlement`/`voc:repository`
  (sind schon da), `schema:exampleOfWork` aus `corresp`. RDF-Typ: `schema:CreativeWork`
  beibehalten und zusätzlich `schema:ArchiveComponent`.
- `export_cypher.py`/`export_graph_json.py`: `hsp_id` wird über `witness_properties()`
  mitgenommen, das prüfen. Witness-Knoten in `graph.json` tragen `label` = msName, damit
  `lookup_entity` im Browser-Agenten „Kolmarer“ findet.
- Vokabular-Doku in `mcp_server/README.md` und `mcp_server/server.py` (Docstrings von
  `graph_query`/`sparql_query`) aktualisieren.

**6b: MCP-Tools** (heute), Logik in `mcp_server/tools/manuscripts.py`, Registrierung in `server.py`:
- `find_manuscript(query)`: sucht im lokalen Register (msName, Signatur, Ort, HSP-ID; Fuzzy) und
  liefert `[{witness_id, label, settlement, repository, shelfmark, hsp_id, n_letters}]`. Braucht
  nur `build/entities.json`, keine Dienste.
- `manuscript_mentions(witness_id)`: Briefe, die die Handschrift erwähnen, aus
  `build/letters.jsonl` (`mentions.witnesses`), mit Datum, Absender/Empfänger und einem Textauszug
  um das `<rs>` (aus `text`, sofern Volltext vorhanden).
- `hsp_search(query, limit=10, live=False)`: `lib_hsp.local_search` über den Spiegel, mit
  `live=True` zusätzlich `lib_hsp.search`.
- `hsp_manuscript(id, description="summary"|"full"|"none")`: `id` ist `lassberg-witness-NNNN`
  (wird über das Register zur HSP-ID aufgelöst) oder eine HSP-ID. Liest aus `data/hsp/`; fehlt die
  Handschrift dort, wird sie live geholt und gespiegelt. Liefert Kerndaten, Portal-URL,
  Beschreibungs-IDs mit Katalogzitat und Lizenz sowie `summary` bzw. `full` (bereinigter Text,
  gekürzt auf maximal 30.000 Zeichen) nach 3c. Die MCP-Nutzung ist lokal und privat, dort gibt es
  deshalb kein Lizenz-Gate. Die Lizenz wird aber immer mitgeliefert.
- Tool-Docstrings nach dem Muster der bestehenden Tools (ID-Format wiederholen) und
  Beispielablauf im README: `find_manuscript("Kolmar")` → `manuscript_mentions` → `hsp_manuscript`.

**6c: Website-Export, pro Handschrift nachgeladen** (danach)
- `scripts/export_manuscripts.py` (Make-Target `hsp-export`, offline, liest nur `data/hsp/` und
  `build/`) schreibt:
  - `json/explore/manuscripts.json`: kleiner Index für alle Witnesses (id, label, shelfmark,
    settlement, repository, hsp_id, portal_url, n_letters, letter_ids, suchbare Kurzfelder wie
    msItem-Titel und Autoren aus CC0-Kerndaten).
  - `json/hsp/<witness-id>.json`: pro Handschrift die Registerfelder, HSP-Kerndaten, Liste der
    Beschreibungen (Katalogzitat, ID, Portal-Link, Lizenz) und die erwähnenden Briefe. Den
    **Inhalt** einer Beschreibung (summary, msItems, Provenienz, Volltext) nur dann, wenn ihr
    `licence_status == "free"` ist.
- **Lizenz-Gate**: Die Positivliste freier Lizenzen (CC0, CC BY, CC BY-SA, …) steht als Konstante
  in `lib_hsp.py`. Alles andere, auch `unknown`, bekommt nur Zitat und Link. Test in
  `tests/test_hsp.py`: Eine Fixture mit `status="restricted"` darf keinen Beschreibungsinhalt im
  Export erzeugen. `fetched_at` und die Lizenz stehen in jeder Datei; Attribution
  „Daten: Handschriftenportal“ mit Lizenz-Link.
- **Lokale Vollversion für Präsentationen** (Vorgabe des Projektleiters: lokal ohne Einschränkung):
  `export_manuscripts.py --local` (in `make hsp-export` immer mit ausführen) schreibt zusätzlich
  `json/hsp-local/<witness-id>.json` **ohne Lizenz-Gate**, also mit vollem Beschreibungsinhalt
  aller Handschriften, dazu `json/hsp-local/index.json` als Marker. `json/hsp-local/` steht in
  `.gitignore`.
  Das Frontend prüft beim ersten Handschriftenzugriff einmal `json/hsp-local/index.json`. Gibt es
  die Datei (lokal mit `python3 -m http.server`), lädt es aus `json/hsp-local/`, sonst (GitHub
  Pages) aus `json/hsp/`. Das Ergebnis wird für die Sitzung gemerkt, damit es bei höchstens einer
  404-Anfrage bleibt. Im Vollmodus zeigt die Seite einen dezenten Hinweis „Lokale Vollversion,
  enthält nicht frei lizenzierte HSP-Beschreibungen, nicht veröffentlichen“. Der GraphRAG-Agent
  nutzt automatisch dieselbe Quelle, bekommt also lokal die vollen Beschreibungen.
  Schutz gegen versehentliches Veröffentlichen: `.gitignore`-Eintrag, zusätzlich ein Test in
  `tests/test_hsp.py`, der fehlschlägt, wenn `git ls-files json/hsp-local data/hsp` nicht leer ist.
  **Nie** `git add -f` auf diese Pfade.
- `json/hsp/` wird committet (enthält per Gate nur freie Inhalte). Vor dem ersten Commit
  stichprobenartig prüfen, dass keine Datei Inhalte einer `restricted`-Beschreibung enthält.
- `js/explore/agent.js`: neue Tools `find_manuscript {"query"}` (über `manuscripts.json`) und
  `get_manuscript {"id"}` (lädt `json/hsp/<id>.json` bei Bedarf); `lookup_entity` um
  Witness-Knoten ergänzen (falls nicht schon über graph.json abgedeckt). `SYSTEM_PROMPT`: ID-Schema
  `lassberg-witness-NNNN`, `voc:hspId`, Hinweise „HSP-Daten sind ein Snapshot vom `fetched_at`“ und
  „Beschreibungen ohne freie Lizenz nur verlinkt“. Laut CLAUDE.md mit `scripts/export_rdf.py`
  synchron halten.

**6d: Offizielle HSP-API**: Sobald sie verfügbar ist, nur `lib_hsp.py` umstellen. Spiegel und Index
bleiben als Cache bzw. für die Identifizierung bestehen. In `mcp_server/README.md` notieren.

### Phase 7: Darstellung auf der Website

- `oxygen-framework/lassberg/xslt/letter-to-html.xsl` (~Zeilen 503–570): Bei `rs type="witness"`
  mit Key in `lassberg-manuscripts.xml` Tooltip/Popover „Ort, Bibliothek, Signatur (msName)“
  und HSP-Link anzeigen. Keys ins Literaturregister (Urkunden) behandeln wie bisher.
- Neue Registerseite `html/manuscripts.html` über `xslt/manuscripts.xsl` (Vorlage:
  `persons.xsl`): Tabelle mit Signatur, Name, Ort, Anzahl Briefe, HSP-Link; Navigation in allen
  Seiten ergänzen; Einbindung in die MiniSearch-Suche (`js/search.js`).
- Skill `build-website` um die neue Seite erweitern und danach ausführen.

### Phase 8: Skills und Doku nachziehen

- `.claude/skills/add-register-entry/references/manuscript-research.md`: auf `msDesc` umstellen,
  HSP als **erste** Quelle (`scripts/manuscripts/hsp_lookup.py`, lokal und `--live`), danach
  Handschriftencensus und GND.
- `.claude/skills/check-letter-annotations` (inkl. `references/tei-annotation-reference.md`):
  Regeln aus Abschnitt 3.1 aufnehmen.
- Skill `edition-pipeline`: Target `make hsp` erwähnen.
- `CLAUDE.md`: kurzer Absatz zum HSP-Zugriff (undokumentierte API, kein CORS, lokaler Spiegel
  `data/hsp/` gitignored wegen Lizenzen, Lizenz-Gate im Export, `scripts/lib_hsp.py`
  als einzige Stelle mit HSP-URLs).

## 5. Wichtige Fallstricke

- **Formatierung der Briefdateien** nicht zerstören (große Diffs machen Reviews unmöglich).
  Nach dem ersten Batch den `git diff --stat` prüfen: Pro Brief sollten wenige Zeilen geändert sein.
- **Statusmodell**: keine `<change>`-Einträge schreiben (s. 3.1, Regel 6). Nach jedem Batch
  `make status`.
- **Transkriptions-`div` only**: normalisierte Fassung, Übersetzung und Summary nicht anfassen.
- **`<lb break="no"/>` mitten im Wort** (z. B. „auf<lb break="no"/>gefunden“): `quote` wird ohne
  Trennung verglichen, das `<rs>` umfasst das `<lb/>`.
- **HSP-Suche mit Rechtschreibkorrektur**: nie den ersten Treffer blind übernehmen.
- **Undokumentierte API**: Fällt sie aus, laufen MCP und Website aus dem Spiegel bzw. den
  exportierten Dateien weiter (Fehler melden, nicht abstürzen).
- **Keine Hartkodierung** von Kolmar-Daten außerhalb von `data/` und Tests.
- **Lizenzen**: `data/hsp/` und `json/hsp-local/` sind gitignored und werden nie committet, auch
  nicht als Test-Fixture.
  Auf die Website kommen nur Inhalte, die das Lizenz-Gate passieren (6c). In versionierten
  Dateien (`build/manuscripts/`, Commit-Messages, Doku) keine längeren Zitate aus
  HSP-Beschreibungen.
- `.venv` (openpyxl, für den Excel-Import) und `.venv-infra` (Pipeline, MCP) nicht vermischen.
  Nichts in `src/` ändern.

## 6. Dateiübersicht (neu/geändert)

Neu: `scripts/lib_hsp.py`, `scripts/manuscripts/{import_blb_excel,register,mirror_hsp,
build_hsp_index,hsp_lookup,enrich_from_hsp,extract_letter,resolve,apply_proposals}.py`, `scripts/manuscripts/SCAN_PROMPT.md`,
`scripts/export_manuscripts.py`, `mcp_server/tools/manuscripts.py`, `tests/test_hsp.py`,
`docs/analysis/handschriften-stichprobe.md`, `json/explore/manuscripts.json`, `json/hsp/*.json`,
`oxygen-framework/lassberg/xslt/manuscripts.xsl`,
`html/manuscripts.html`.

Geändert: `data/register/lassberg-manuscripts.xml`, `data/register/lassberg-literature.xml`
(Migration), `data/letters/*.xml`, `scripts/parse_tei.py`, `scripts/lib_pipeline.py`,
`scripts/export_rdf.py`, `mcp_server/server.py` + `README.md`, `js/explore/agent.js`,
`letter-to-html.xsl`, `Makefile` (Targets `hsp-mirror`, `hsp-index`, `hsp-export`), `.gitignore`, `docs/TEI.md`, `CLAUDE.md`, Skills (Phase 8),
`tests/test_pipeline.py`.

Versionierung: **`data/hsp/` (Spiegel und `index.sqlite`) und `json/hsp-local/` in `.gitignore`**,
aus Lizenzgründen. `build/manuscripts/`
(Vorschläge, `applied.jsonl`, Berichte) **committen**, als Provenienznachweis für das automatische
Anwenden (`build/letters.jsonl` und `entities.json` sind ebenfalls versioniert).

## 7. Arbeitsweise für Sonnet

- Vor jeder Phase die hier genannten Dateien lesen und Zeilenangaben verifizieren; sie sind
  Näherungen vom 2026-09-30.
- Nach jeder Phase: `make test`, bei Datenänderungen `make parse` und `make status`, danach einen
  Commit.
- Unklarheiten, die Abschnitt 1 berühren, **nicht** selbst entscheiden, sondern nachfragen. Alles
  andere nach diesem Plan und der Konvention „nicht raten, `key=""` bzw. `needs-review`“.

## 8. Nicht im Umfang

Überarbeitung der `src/`-Pipeline; vollständige Handschriftenbeschreibungen im eigenen Register
(die liefert das HSP); Druckexemplare/Urkunden-Umbau; CORS-Proxy (stattdessen später die offizielle
HSP-API, 6d); Veröffentlichung nicht frei lizenzierter HSP-Beschreibungen.

## 9. Abnahme Tagesziel (Kolmarer Liederhandschrift)

Alle Punkte müssen erfüllt sein, als Nachweis die Ausgaben in `build/manuscripts/kolmar_acceptance.md`
ablegen:

1. `lassberg-manuscripts.xml` enthält genau einen `msDesc` mit
   `altIdentifier[@type='hsp']/idno = HSP-666242f4-0675-3121-b0d6-be697c7a9b20`, angelegt
   durch `resolve.py` (Nachweis: Eintrag in `build/manuscripts/applied.jsonl`).
2. Die Briefe 1730, 1737, 1741 und 1743 (und 1064) enthalten `rs type="witness"` mit Key auf diesen
   Eintrag sowie `ref type="cmif:mentionsBibl"` in `note type="mentioned"`. `make status` und
   `make test` sind grün.
3. Nach `make parse rdf` liefert diese Abfrage (per `rdflib` direkt auf `rdf/edition.ttl`,
   zusätzlich per `sparql_query`, falls Oxigraph läuft) die Briefe samt Datum und
   Korrespondenzpartner (Wackernagel bzw. Uhland):
   ```sparql
   PREFIX csvoc: <https://lod.academy/correspsearch/vocab/terms#>
   PREFIX voc:   <https://michaelscho.github.io/lassberg/vocab/>
   SELECT ?letter ?date WHERE {
     ?ms voc:hspId "HSP-666242f4-0675-3121-b0d6-be697c7a9b20" .
     ?letter csvoc:mentions ?ms ;
             csvoc:hasCorrespAction/csvoc:hasTimespan/csvoc:startsOn ?date .
   } ORDER BY ?date
   ```
   Als Regressionstest in `tests/test_pipeline.py` aufnehmen (erwartet: 1730, 1737, 1741, 1743
   von 1833 plus 1064 von 1826).
4. Über MCP, z. B. in Claude Code mit dem konfigurierten Server:
   `find_manuscript("Kolmar")` → Witness-ID; `manuscript_mentions(<id>)` → die Briefe oben mit
   Textauszug; `hsp_manuscript(<id>)` → München / Bayerische Staatsbibliothek / Cgm 4997 /
   um 1460 / Rheinfranken (Speyer?) / I + 854 Bl. / Beschreibung Schneider 1996, S. 425–446, Lizenz
   InC. Die Daten stammen aus `data/hsp/`, das per `mirror_hsp.py --add` über die echte HSP-API
   befüllt wurde (Nachweis: Eintrag in `data/hsp/manifest.json` mit `source_url` und `fetched_at`).
   `hsp_search("Kolmarer")` findet sie lokal.
5. `git ls-files data/hsp json/hsp-local` ist leer. Lokal mit `python3 -m http.server` zeigt die
   Explore-Seite die volle Kolmar-Beschreibung (InC); ohne `json/hsp-local/` nur Zitat und Link.
6. `grep -rn "Kolmar\|666242f4" scripts/ mcp_server/ js/` findet nichts außerhalb von Tests.
