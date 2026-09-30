# Handschriften im Korpus: Stichprobenanalyse (Phase 1, 2026-09-30)

Grundlage: alle 281 Briefdateien mit Transkription (`scripts/manuscripts/tei_text.py`), dazu
Lektüre der Wackernagel-Briefe (1730–1743) und aller `rs type="object"`-Belege.

## Häufigkeiten: wie Handschriften heute ausgezeichnet sind

| `rs/@type` (Transkriptions-div) | Anzahl gesamt | davon Handschriften-Bezug (Schätzung) |
|---|---|---|
| `person` / `place` / `organisation` | 1404 / 1212 / 28 | – |
| `bibl` | 423 | 21 mit Stichwort (Codex/Sammlung/Msc.), davon nur 2–3 echte Handschriften, die übrigen gedruckte Sammlungen bzw. Editionstitel (Myller, Müller, Cod. diplom.) |
| `object` | 118 | ca. 30: Codices („Colmarer Codex“, „Weingartner Codex“, „Maness. Codex“, „münchner codex“), „handschrift“ generisch; Rest Urkunden, Gemälde, Glasscheiben, Bücherpakete |
| `misc` | 112 | 5 mit „Codex“ („Maneßscher Codex“, „Weißenauer Codex“, „Mediceische Codex“) |
| `witness` | 8 | 4 Handschriften (Weingartner, Heidelberger 350/357, Nibelungen C), 2 Urkunden, 1 Druckexemplar, 1 anaphorisch („die älteste bekannte Handschrift“) |
| nicht ausgezeichnet | – | Stichwortsuche findet in 159 von 281 Briefen mindestens einen unmarkierten Treffer (682 Treffer gesamt; überwiegend generische „Handschrift“/„Abschrift“) |

## Typische Belege und Entscheidungen

| Brief | Beleg | heute | Entscheidung nach Plan 3.1 |
|---|---|---|---|
| 1743 | „Colmarer liedercodex“ | `object` | `witness` (Regel 5, umtypisieren), Kolmarer Liederhandschrift |
| 1730, 1737, 1741 | „Colmarer lieder codex“ / „Colmarer codex“ | `object` | `witness`, dieselbe Handschrift |
| 1064 | „der Kolmarer Handschrift“ | nicht ausgezeichnet | `witness` (`wrap`) |
| 1959, 1961, 2262, 2263, 1952 | „Weingartner Codex“ | `object`, z. T. Key auf Werk lit-0069 | `witness` auf Handschrift (Werkbezug im msDesc) |
| 0626 | „Weingartner Handschrift der Minnesänger“ | `witness`→lit-0230 | Migration auf msDesc (Phase 2) |
| 1787, 1154, 1410 | „Manessischen/Maness. Codex“ | `object`/`misc` | `witness` (identifizierbar: Große Heidelberger Liederhs.) |
| 1779 | „münchner codex“ / „codex“ | `object` | nur mit Kontext; sonst `key=""` (spezifisch, nicht identifiziert) |
| 1784 | „pariser codex“ | `object` | wie 1779 |
| 1766 | „Berliner codex“, „schönen carolingischen Codex“ | `object` | Berliner: `witness key=""` bzw. identifizieren; „carolingischer Codex“ spezifisch nach Kontext |
| 1787 | „meine handschrift“ / „meiner eigenen Handschrift“ | `object` | `witness` nur, wenn Kontext eine bestimmte Hs. nennt; sonst nicht auszeichnen |
| 1741, 1802, 1999, 2319 | „Handschriften“ (Plural, unspezifisch) | `object` | **nicht** auszeichnen (Regel 3); bestehendes `object` bleibt |
| 1039, 1044, 1051 | „Myllers Sammlung“, „Müllersche Sammlung“ | `bibl` | bleibt `bibl` (gedruckte Sammlung) |
| 1015, 1051, 1370 | „Codex trad. S. Gallensium“, „Cod. diplom. …“ | `bibl` | bleibt `bibl` (Urkundenbuch/Edition, kein einzelner Textzeuge) |
| 1015, 1044, 1164, … | „Urkunde(n)“ | `object` | bleibt (Urkunden, nicht Gegenstand des Handschriftenscans) |
| 2319 | „Merseburger Missale“ | `object` | `witness` (Hs., identifizierbar über HSP prüfen) |
| 1449 | „codex traditionum augiae albae“ | `object` | Handschrift/Urbar (Reichenau?) → `witness`, HSP-Lookup |

## Grenzfälle und Präzisierungen (nur Klarstellungen zu 3.1)

1. **„Codex“ als Titelbestandteil einer Edition** („Codex diplomaticus …“, „Codex probationum“) ist ein
   Werk/eine Ausgabe (`bibl`), kein Textzeuge.
2. **„Sammlung“ + Herausgebername** (Myller, Müller, Bodmer) ist eine gedruckte Sammlung (`bibl`).
   Nur „X’s Sammlung“ im Sinn einer handschriftlichen Sammlung (Laßbergs, Neukirchs) ist `witness`.
3. **Urkunden** bleiben `object` bzw. `witness`→`bibl type="charter"` im Literaturregister und sind nicht
   Ziel des Handschriftenscans.
4. **Sammelbezeichnungen im Plural** („meine handschriften und bücher“) werden nicht ausgezeichnet.
5. **Handschrift und Text zugleich genannt** („Weingartner Codex“ als Träger der Minnesänger-Lieder):
   `witness` auf die Handschrift; der Werkbezug (Minnesang) steht im Register, nicht im Brieftext.
6. **Bestehender Key auf ein Werk** (1959/1961: `object` mit Key auf `lassberg-literature-0069`) wird beim
   Umtypisieren durch den Handschriften-Key ersetzt.
