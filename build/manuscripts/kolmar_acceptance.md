# Abnahme Tagesziel: Kolmarer Liederhandschrift (Plan Abschnitt 9)

Erzeugt am 2026-09-30 aus den tatsächlichen Repo-Zuständen (Skript: Sonnet 5.5, Claude Code).

## 1. Registereintrag

Vorkommen der HSP-ID in `lassberg-manuscripts.xml`: **1** (in 1 `msDesc`).

```xml
                <msDesc xml:id="lassberg-witness-0291" ana="needs-review">
                    <msIdentifier>
                        <settlement>München</settlement>
                        <repository>Bayerische Staatsbibliothek</repository>
                        <idno type="shelfmark">Cgm 4997</idno>
                        <altIdentifier type="hsp"><idno>HSP-666242f4-0675-3121-b0d6-be697c7a9b20</idno></altIdentifier>
                        <msName>Kolmarer Liederhandschrift</msName>
                    </msIdentifier>
                    <note>Identifiziert via HSP (title-match) beim Handschriften-Scan, zuerst in Brief 1064.</note>
                </msDesc>
```

Anlage durch `resolve.py` (Einträge in `build/manuscripts/applied.jsonl`):

```json
{"ts": "2026-09-30T09:10:10+00:00", "action": "register-create", "witness_id": "lassberg-witness-0291", "hsp_id": "HSP-666242f4-0675-3121-b0d6-be697c7a9b20", "letter": "lassberg-letter-1064", "how": "title-match"}
{"ts": "2026-09-30T09:12:13+00:00", "letter": "lassberg-letter-1064", "action": "wrap", "quote": "Kolmarer Handschrift", "witness_id": "lassberg-witness-0291", "confidence": 0.85, "how": "hsp-live", "mode": "wrap"}
{"ts": "2026-09-30T09:12:13+00:00", "letter": "lassberg-letter-1730", "action": "retype", "quote": "Colmarer lieder codex", "witness_id": "lassberg-witness-0291", "confidence": 0.85, "how": "register-fuzzy", "mode": "retype"}
{"ts": "2026-09-30T09:12:13+00:00", "letter": "lassberg-letter-1737", "action": "retype", "quote": "Colmarer codex", "witness_id": "lassberg-witness-0291", "confidence": 0.85, "how": "register-fuzzy", "mode": "retype"}
{"ts": "2026-09-30T09:12:13+00:00", "letter": "lassberg-letter-1741", "action": "retype", "quote": "Colmarer Codex", "witness_id": "lassberg-witness-0291", "confidence": 0.9, "how": "register-fuzzy", "mode": "retype"}
{"ts": "2026-09-30T09:12:13+00:00", "letter": "lassberg-letter-1743", "action": "retype", "quote": "Colmarer liedercodex", "witness_id": "lassberg-witness-0291", "confidence": 0.95, "how": "register-fuzzy", "mode": "retype"}
```

## 2. Briefe

| Brief | `rs type="witness"` mit Key auf den Eintrag | `ref cmif:mentionsBibl` in `note type="mentioned"` |
|---|---|---|
| 1064 | `<rs type="witness" key="../register/lassberg-manuscripts.xml#lassberg-witness-0291" resp="#manuscript-scan">Kolmarer Handschrift` | 1 |
| 1730 | `<rs type="witness" key="../register/lassberg-manuscripts.xml#lassberg-witness-0291" resp="#manuscript-scan">Colmarer lieder codex` | 1 |
| 1737 | `<rs type="witness" key="../register/lassberg-manuscripts.xml#lassberg-witness-0291" resp="#manuscript-scan">Colmarer codex` | 1 |
| 1741 | `<rs type="witness" key="../register/lassberg-manuscripts.xml#lassberg-witness-0291" resp="#manuscript-scan">Colmarer Codex` | 1 |
| 1743 | `<rs type="witness" key="../register/lassberg-manuscripts.xml#lassberg-witness-0291" resp="#manuscript-scan">Colmarer liedercodex` | 1 |

`make status`: status model consistent. `make test`: siehe unten.

## 3. SPARQL (rdflib direkt auf `rdf/edition.ttl`)

```
lassberg-letter-1064 1826-01-25
lassberg-letter-1730 1833-06-30
lassberg-letter-1737 1833-08-13
lassberg-letter-1741 1833-08-30
lassberg-letter-1743 1833-09-26
```

Regressionstest: `tests/test_pipeline.py::test_manuscript_mentions_via_sparql_on_generated_rdf`.

## 4. MCP-Tools (`mcp_server/tools/manuscripts.py`, dieselben Funktionen wie in `server.py`)

```
find_manuscript('Kolmar'):
[
 {
  "witness_id": "lassberg-witness-0291",
  "label": "Kolmarer Liederhandschrift",
  "settlement": "München",
  "repository": "Bayerische Staatsbibliothek",
  "shelfmark": "Cgm 4997",
  "hsp_id": "HSP-666242f4-0675-3121-b0d6-be697c7a9b20",
  "n_letters": 5,
  "score": 100.0
 }
]

manuscript_mentions('lassberg-witness-0291'):
- lassberg-letter-1064 1826-01-25 Ludwig Uhland -> Joseph von Laßberg
    …ich ihm dasselbe nachgeschickt habe. Maßmann ist vor etwa 14 Tagen nach Straßburg abgereist, er will besonders auch der Kolmarer Handschrift nachspüren. Was veranlaßte, daß ihm der Gebrauch der Hofbibliothek gänzlich verweigert wurde, ist mir räthselhaft. Ihre…
- lassberg-letter-1730 1833-06-30 Joseph von Laßberg -> Wilhelm Wackernagel
    … iezt in Neapel ist :/ über den fraglichen codex abfragen konnte, ließ mich vermuten, daß es wol der verloren geglaubte Colmarer lieder codex seie, den ich einmal in meiner iugend bei dem alten blinden Pfeffel sahe. erkundigen Sie sich doch, Sie werden bald wis…
- lassberg-letter-1737 1833-08-13 Joseph von Laßberg -> Wilhelm Wackernagel
    …en Sie wol, gott befolen von Irem ergebensten JvLaßberg. Ser begierig wäre ich zu erfaren, ob meine vermutung wegen des Colmarer codex der meistersänger einigen grund hat? oder was des H. Neukirch handschrift denn eigentlich enthaltet? Dabam ex villa epp…
- lassberg-letter-1741 1833-08-30 Wilhelm Wackernagel -> Joseph von Laßberg
    …e Aufsätze von Docen sind mir für die rechte Nutzung der Zürcher Manuscripte unentbehrlich. Herrn Neukirchs Hs. ist der Colmarer Codex, soviel ich aus dem was er sagt abnehmen kann; er hat ihn auch aus dem Pfeffelschen Hause, ich glaube durch Heirath, üb…
- lassberg-letter-1743 1833-09-26 Joseph von Laßberg -> Wilhelm Wackernagel
    …n Sie uns vest an diesem glauben halten, ein einziger augenblik kann alles umgestalten. Nun bin ich doch frohe, daß der Colmarer liedercodex wieder aufgefunden ist. natürlich denkt herr Neukirch iezt an keine herausgabe, die im auch gar nicht zuzumuten ist; al…

hsp_manuscript('lassberg-witness-0291', 'summary'):
{
 "witness_id": "lassberg-witness-0291",
 "hsp_id": "HSP-666242f4-0675-3121-b0d6-be697c7a9b20",
 "portal_url": "https://handschriftenportal.de/search?hspobjectid=HSP-666242f4-0675-3121-b0d6-be697c7a9b20",
 "core": {
  "settlement-display": "München",
  "repository-display": "Bayerische Staatsbibliothek",
  "idno-display": "Cgm 4997",
  "title-display": "‘Kolmarer Liederhandschrift’",
  "orig-date-lang-display": [
   "um 1460"
  ],
  "orig-place-display": "Rheinfranken (Speyer (?))",
  "leaves-count-display": "I + 854 Bl.",
  "material-display": "Papier",
  "dimensions-display": [
   "29,3 × 20"
  ],
  "object-type-display": "codex"
 },
 "fetched_at": "2026-09-30T09:00:39+00:00",
 "core_licence": {
  "licence_status": "free",
  "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/deed.de"
 }
}
{
 "id": "HSP-1963f105-df95-39ea-b821-2e294e9e53b1",
 "citation": "Beschreibung von München, Bayerische Staatsbibliothek, Cgm 4997 (SCHNEIDER, Karin: Die deutschen Handschriften der Bayerischen Staatsbibliothek München: Die mittelalterlichen Handschriften aus Cgm 4001-5247. - Editio altera. - Wiesbaden: Harrassowitz, 1996. - (Catalogus codicum manu scriptorum Bibliothecae Monacensis; T. 5, Ps. 7))S. 425–446",
 "licence_status": "restricted",
 "licence_url": "http://rightsstatements.org/vocab/InC/1.0/",
 "fetched_at": "2026-09-30T09:00:40+00:00"
}
headline: Papier · I + 854 (Blatt) · 29,3 × 20 (cm) · Rheinfranken (Speyer (?) · um 1460

hsp_search('Kolmarer'):
  HSP-666242f4-0675-3121-b0d6-be697c7a9b20 Cgm 4997 | Kolmarer Liederhandschrift | lassberg-witness-0291
  HSP-8f8428dc-9cb1-35dd-9c20-fdfab0749655 Cod. Donaueschingen 120 | I: Hugo Ripelin von Straßburg: Compendium theologicae veritatis, dt. · Bewährung, dass die Juden irren · II: Donaueschinger Liederhandschrift | lassberg-witness-0131
```

Manifest-Einträge (`data/hsp/manifest.json`, gitignored):

```json
{
 "HSP-1963f105-df95-39ea-b821-2e294e9e53b1": {
  "fetched_at": "2026-09-30T09:20:18+00:00",
  "kind": "desc",
  "kod_id": "HSP-666242f4-0675-3121-b0d6-be697c7a9b20",
  "licence_status": "restricted",
  "licence_url": "http://rightsstatements.org/vocab/InC/1.0/",
  "sha256": "f5e37eed1875be347792c8b8c4b9738a96b38f9f2b6d0e0a4438312b05d20ceb",
  "source_url": "https://handschriftenportal.de/api/tei/HSP-1963f105-df95-39ea-b821-2e294e9e53b1",
  "witness_id": "lassberg-witness-0291"
 },
 "HSP-666242f4-0675-3121-b0d6-be697c7a9b20": {
  "fetched_at": "2026-09-30T09:20:16+00:00",
  "kind": "kod",
  "licence_status": "free",
  "licence_url": "https://creativecommons.org/publicdomain/zero/1.0/deed.de",
  "sha256": "4aa509c04e30e0114968eb3bbb5603b441b1542fc0e5d8626dd08f596eed5b54",
  "source_url": "https://handschriftenportal.de/api/tei/HSP-666242f4-0675-3121-b0d6-be697c7a9b20",
  "witness_id": "lassberg-witness-0291"
 },
 "HSP-666242f4-0675-3121-b0d6-be697c7a9b20:json": {
  "fetched_at": "2026-09-30T09:20:15+00:00",
  "kind": "kod",
  "licence_status": "unknown",
  "licence_url": null,
  "sha256": "8ebe47f2ade50f4b67a0151ead6cafcf8f44d5ce81fc0f2ad2ff85e8e592ea54",
  "source_url": "https://handschriftenportal.de/api/kods/HSP-666242f4-0675-3121-b0d6-be697c7a9b20",
  "witness_id": "lassberg-witness-0291"
 }
}
```

Hinweis zur Herkunft: Der Spiegel-Eintrag wurde zuerst vor dem `resolve.py`-Lauf durch einen manuellen
Testaufruf `mirror_hsp.py --add <ID>` mit der ID aus dem Plan erzeugt (Test der API); die Registerzeile selbst und
ihre ID hat `resolve.py` unabhängig über `hsp.search()` ermittelt (siehe `applied.jsonl`, `how: title-match`).
Danach wurde der Spiegel mit `--add <ID> --refresh` neu geholt, damit das Manifest `witness_id` und den frischen
`fetched_at` trägt (Daten stammen aus der echten HSP-API).

## 5. Versionskontrolle / Lokalmodus

`git ls-files data/hsp json/hsp-local` (muss leer sein): `(leer)`

Lokaler Vollexport `json/hsp-local/lassberg-witness-0291.json` enthält die volle Beschreibung (InC), der
öffentliche Export `json/hsp/lassberg-witness-0291.json` nur Zitat, Lizenz und Link
(`content: null`). Das Frontend (`js/explore/manuscripts.js`, Tab „Manuscripts“, `?ms=<id>`) wählt
automatisch `json/hsp-local/`, wenn `json/hsp-local/index.json` existiert.

## 6. Keine Hartkodierung

`grep -rn "Kolmar\|666242f4" scripts/ mcp_server/ js/` liefert: `(keine Treffer)`

## 7. Explore-Seite im Browser geprüft

Mit `python3 -m http.server` und headless Chromium (`--dump-dom`, `html/explore.html?ms=<witness-id>`):

- mit `json/hsp-local/index.json`: Hinweis „Lokale Vollversion …“, Kerndaten, 5 Briefe, Katalogzitat
  (Schneider 1996, S. 425–446), Lizenz „eingeschränkt“ und der volle Beschreibungstext in `<details>`.
- ohne `json/hsp-local/index.json` (Datei zeitweise umbenannt): nur Kerndaten, Briefe, Zitat, Lizenz und der Satz
  „nicht frei lizenziert und wird hier nur zitiert und verlinkt“, kein Beschreibungstext.

Nicht geprüft: die Agent-Tools `find_manuscript`/`get_manuscript` (`js/explore/agent.js`) im laufenden LLM-Chat
(kein API-Schlüssel); die Datenfunktionen (`js/explore/manuscripts.js`) wurden per Node-Smoke-Test geprüft.
