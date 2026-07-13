# TEI-Documentation

## Überblick: Aufbau einer Briefdatei

Jeder Brief (`data/letters/lassberg-letter-<ID>.xml`) kodiert dieselbe Korrespondenz auf zwei
Ebenen, die konsistent zueinander gehalten werden müssen:

1. **`<teiHeader>`** — strukturierte Metadaten: Absender/Empfänger mit Datum
   (`<correspDesc>`/`<correspAction>`), eine flache, nach CMIF-Vokabular sortierte Liste
   aller im Brief erwähnten Entitäten (`<note type="mentioned">`), sowie das
   `<revisionDesc>` mit dem Bearbeitungsstand des Briefes (Statusleiter
   `draft → done → reviewed → published`, s. Abschnitt „Statusmodell").
2. **`<text><body>`** — der Brieftext in bis zu vier Fassungen als `<div>`s, von denen nur eine
   die Inline-Auszeichnung (`<rs>`) trägt.

Diese beiden Ebenen sind redundant, aber bewusst: `<note type="mentioned">` erlaubt es
Werkzeugen (correspSearch, CMIF-Aggregatoren), Personen/Orte/Werke eines Briefes zu lesen, ohne
den Fließtext parsen zu müssen; `<rs>` im Fließtext verankert dieselbe Information an der
Textstelle, an der sie tatsächlich vorkommt. **Jeder Schlüssel (`@key`), der im Fließtext als
`<rs>` verwendet wird, muss daher auch als `<ref>` in `<note type="mentioned">` auftauchen, und
umgekehrt** — mit Ausnahme des Absenders/Empfängers, der nur dann zusätzlich im Fließtext/als
Notiz erscheint, wenn er dort auch tatsächlich namentlich erwähnt wird (z. B. in der
Unterschriftszeile), nicht allein aufgrund seiner Rolle in `<correspAction>`.

### Die vier `<div>`-Fassungen

| Rolle | Enthält `<rs>`-Markup? | `@type` | `@resp` |
|---|---|---|---|
| Diplomatische Transkription (Originalorthographie) | **Ja — einzige Fassung mit Markup** | `original` oder `print` — s. u. | `#transkribus #MiS` oder `ocr` |
| Normalisierte/modernisierte Fassung | Nein (reiner Text) | `normalized` | `GPT3.5`, `#GPT4` |
| Englische Übersetzung | Nein | `translation` | `#GPT4` |
| Deutsche Zusammenfassung | Nein | `summary` | `#GPT4` |

Nicht jeder Brief hat bereits alle vier Fassungen — Normalisierung/Übersetzung/Zusammenfassung
werden in einem späteren Pipeline-Schritt ergänzt (siehe `CLAUDE.md`). Das Fehlen einzelner
`<div>`s ist daher kein Kodierungsfehler.

Die Transkriptions-Fassung ist am Inhalt zu erkennen (sie enthält `<rs>`), nicht primär am
`@type`-Wert — aber `@type` und `@resp` sind hier trotzdem bedeutungstragend, nicht nur technisch:

- **`<div type="original" resp="#transkribus #MiS">`** — diplomatische Transkription **der
  Handschrift selbst**: Ausgangsbasis war ein Manuskript-Scan, per Transkribus-HTR erkannt und von
  `#MiS` korrigiert. Enthält i. d. R. `<pb n="…" corresp="../pagexml/…"/>`- und
  `<lb xml:id="…" n="…" corresp="…"/>`-Elemente, die die tatsächliche Zeilenaufteilung der
  Handschrift aus dem Transkribus-Export widerspiegeln (48 von 58 Briefen dieser Gruppe haben
  `<lb>`; das Fehlen bei den übrigen ist noch nicht nacherfasst, kein Bedeutungsunterschied).
- **`<div type="print" resp="ocr">`** — **keine** Transkription der Handschrift, sondern eine
  Texterfassung per OCR aus der gedruckten Edition, die in `<sourceDesc><msDesc><additional>
  <surrogates>` als `<bibl type="printed">` verzeichnet ist (i. d. R. Johannes Meyers
  Alemannia-Abdruck des Laßberg-Pupikofer-Briefwechsels, über Google Books erschlossen). Enthält
  **nie** `<lb>`, da die Drucklineation nichts mit der Zeilenaufteilung der Handschrift zu tun hat
  und keine erfasst wurde.

Beide Gruppen tragen dieselbe `<msDesc>`-Struktur (Aufbewahrungsort der Handschrift **und**
gedruckte Vorlage stehen nebeneinander in `<sourceDesc>`) — der Unterschied liegt einzig darin,
*welche* der beiden Quellen für die vorliegende Transkription tatsächlich abgetippt/erkannt wurde.
`@type`/`@resp` am `<div>` sind daher die primäre Quelle der Wahrheit hierfür, `<lb>`-Präsenz ist
das korroborierende Signal. Bei Unklarheit gilt: `resp="ocr"` → `type="print"`, nie `type="original"`.

### `<opener>`, `<closer>`, `<dateline>`, `<salute>`, `<signed>`

Anrede, Grußformel/Unterschrift und Orts-/Datumszeile eines Briefes werden mit den dafür
vorgesehenen TEI-Kernelementen ausgezeichnet, statt als Teil des Fließtexts in `<p>` zu verbleiben.
`<opener>` und `<closer>` stehen dabei als Geschwisterelemente von `<p>` innerhalb des
Transkriptions-`<div>` (nicht als deren Kind) — bereits vorhandenes `<rs>`-Markup bleibt davon
unberührt, es wird lediglich eine Ebene tiefer verschachtelt:

| Element | Inhalt |
|---|---|
| `<opener>` | Öffnende Formel eines Briefes (Orts-/Datumszeile und/oder Anrede) |
| `<closer>` | Schließende Formel (Grußformel, Unterschrift, ggf. Orts-/Datumszeile) |
| `<dateline>` | Orts-/Datumszeile, unabhängig davon ob sie am Anfang oder Ende steht |
| `<salute>` | Anrede- bzw. Grußformeltext selbst |
| `<signed>` | Unterschrift am Briefende |
| `<address>` | Äußere Adresszeile des Absenders selbst (Empfängertitel/-name/-ort als Briefkopf, z. B. "Seiner Hochwohlgeboren dem Herrn Baron … zu Eppishausen."), Kind von `<opener>` — zu unterscheiden von `<fw type="docket">`, das eine *fremde*, später hinzugefügte Rückvermerk-Notiz ist, s. u. |
| `<postscript>` | Nachschrift nach `<closer>` (enthält ihrerseits wieder `<p>`) — z. B. `lassberg-letter-1131.xml`, wo nach der Unterschrift noch ein "Ex mandato speziali..."-Zusatz folgt |

Beispiel (Ende von `lassberg-letter-0952.xml`, Brief endet mit Grußformel, Unterschrift und
nachgestellter Orts-/Datumszeile):

```xml
<p>… Von der <rs type="bibl" key="../register/lassberg-literature.xml#lassberg-literature-0009"
    >Chronik Heinrichs von Klingenberg</rs> scheint sie bestimmt verschieden zu sein.</p>
<closer>
    <salute>Genehmigen Sie, hochwohlgeborner, geehrtester Herr, die Versicherung wahrer
    Hochachtung und steter Dienstfertigkeit, mit der ich die Ehre habe zu sein Ihr
    ergebenster</salute>
    <signed><rs type="person" key="../register/lassberg-persons.xml#lassberg-correspondent-0179"
        >Pupikofer</rs></signed>.
    <dateline><rs type="place" key="../register/lassberg-places.xml#lassberg-place-0025"
        >Bischofszell</rs>, den <date when="1824">20 Dec. 1824</date></dateline>.
</closer>
```

Beispiel für einen `<opener>` mit kombinierter Orts-/Datumszeile und Anrede (Briefanfang, Muster
aus `lassberg-letter-1044.xml`):

```xml
<opener>
    <dateline><rs type="place" key="../register/lassberg-places.xml#lassberg-place-0043"
        >Eppishausen</rs> am <date when="1825-11-04">4. Nov. 1825</date></dateline>.
    <salute>Mein verertester Herr!</salute>
</opener>
<p>… Fließtext …</p>
```

Beispiel für `<address>` als Briefkopf vor der eigentlichen Anrede (`lassberg-letter-1154.xml`):

```xml
<opener>
    <address>Seiner Hochwohlgeboren dem Herrn Baron <rs type="person"
        key="../register/lassberg-persons.xml#lassberg-correspondent-0373">von
        Laßberg</rs> zu <rs type="place"
        key="../register/lassberg-places.xml#lassberg-place-0043">Eppishausen</rs>.</address>
    <salute>Hochwohlgeborener Herr und Gönner!</salute>
</opener>
```

Diese Auszeichnung wird **nicht** in einem separaten Massen-Durchlauf nachgetragen, sondern
schrittweise dort ergänzt, wo `check-letter-annotations` einen Brief ohnehin prüft — ein Brief ohne
`<opener>`/`<closer>` ist also kein eigenständiger Befund, sondern wird bei der nächsten Prüfung
mit erledigt.

### Archivalische Apparate (`<fw>`, `<add>`)

Manche Briefe tragen neben Laßbergs/des Absenders eigenem Text auch fremde, spätere Zusätze: Archiv-
und Registraturnummern (Seitenzahl des Sammelbandes, Journalnummer, Eingangsnummer des Empfängers),
sowie Vermerke des Empfängers selbst (typischerweise ein knappes "beantw. [Datum]" — wann geantwortet
wurde). Das ist kein Teil des eigentlichen Briefinhalts und gehört daher **nicht** in `<opener>`,
`<closer>` oder `<p>`, auch wenn es unmittelbar neben Datumszeile bzw. Unterschrift auf derselben
Seite steht. Zwei Elemente decken diesen Fall ab, beide als Geschwister von `<opener>`/`<p>`/`<closer>`
innerhalb des Transkriptions-`<div>`:

| Element | Verwendung |
|---|---|
| `<fw type="pageNum">` | Archivische Paginierung des Sammelbandes (nicht die Blattzählung der Handschrift selbst) |
| `<fw type="number">` | Sonstige Registratur-/Journalnummern (Absender- wie Empfängerarchiv) |
| `<fw type="docket">` | Rückvermerk/Dorsalnotiz — meist Ort, Datum und Absendername in Kurzform, oft vom Empfänger zur Ablage wiederholt |
| `<add>` | Nachträglich hinzugefügter Vermerk, typischerweise die Antwortnotiz des Empfängers ("beantw. …") |

Beispiel (Anfang und Ende von `lassberg-letter-1015.xml` — die Zahlen "1264"/"163."/"No. 85." am
Anfang entsprechen exakt der Archivsignatur aus `msIdentifier`; am Ende wiederholt der Empfänger
Ort/Datum/Absender als Dorsalnotiz und vermerkt sein Antwortdatum):

```xml
<div type="original" resp="…">
    <pb n="1" corresp="…"/>
    <fw type="pageNum">1264</fw>
    <fw type="number">163.</fw>
    <fw type="number">No. 85.</fw>
    <opener>
        <dateline>Constanz am 30 July 1825.</dateline>
    </opener>
    <p>… Fließtext …</p>
    <closer>
        <salute>…</salute>
        <signed><rs type="person" key="…">JvLaßzberg</rs></signed>
    </closer>
    <pb n="4" corresp="…"/>
    <fw type="pageNum">1267.</fw>
    <fw type="docket">Constantz 30. July 1825 Jos. von Laßberg</fw>
    <add>beantw. 6. Aug.</add>
</div>
```

Wie bei `<opener>`/`<closer>` gilt: Diese Auszeichnung wird nur ergänzt, wenn ein Brief ohnehin
geprüft wird — kein separater Nacherfassungs-Durchlauf für den Bestand.

### `<correspAction>` und `<note type="mentioned">`

```xml
<correspDesc xml:id="correspDesc-lassberg-letter-1044">
    <correspAction type="sent">
        <persName key="../register/lassberg-persons.xml#lassberg-correspondent-0373"
            ref="https://d-nb.info/gnd/118778862">Joseph von Laßberg</persName>
        <placeName key="../register/lassberg-places.xml#lassberg-place-0043">Eppishausen</placeName>
        <date when="1825-11-04">04.11.1825</date>
    </correspAction>
    <correspAction type="received">
        <persName key="../register/lassberg-persons.xml#lassberg-correspondent-0179"
            ref="https://d-nb.info/gnd/11565108X">Johann Adam Pupikofer</persName>
    </correspAction>
    <note type="mentioned">
        <ref type="cmif:mentionsBibl" target="../register/lassberg-literature.xml#lassberg-literature-0026">
            <rs>Samlung deutscher Gedichte aus dem XII., XIII. und XIV. Jahrhundert. 3 Bde.</rs>
        </ref>
        <ref type="cmif:mentionsPerson" target="../register/lassberg-persons.xml#lassberg-correspondent-0382">
            <rs>Hartmann von Aue</rs>
        </ref>
        <ref type="cmif:mentionsPlace" target="../register/lassberg-places.xml#lassberg-place-0043">
            <rs>Eppishausen</rs>
        </ref>
    </note>
</correspDesc>
```

`<persName>`/`<placeName>` in `<correspAction>` tragen sowohl `@key` (Verweis auf den passenden
Registereintrag) als auch, sofern der Registereintrag selbst einen `@ref` (GND- oder
Wikidata-URL) besitzt, denselben `@ref` noch einmal direkt am Element. `<note type="mentioned">`
verwendet das [CMIF-Vokabular](https://encoding-correspondence.bbaw.de/v1/CMIF.html#c-4-2) mit
genau drei `@type`-Werten: `cmif:mentionsPerson`, `cmif:mentionsPlace`, `cmif:mentionsBibl` — auch
für die neue Kategorie der Handschriften-/Druckexemplare wird `cmif:mentionsBibl` verwendet (s.
u.), da CMIF keine eigene Kategorie für Textzeugen kennt; die Unterscheidung Werk vs. Exemplar
ergibt sich dann aus dem Zielregister (`lassberg-literature.xml` vs. `lassberg-manuscripts.xml`).

### `<revisionDesc>` als Bearbeitungsstatus — das Statusmodell (seit 2026-07-12)

Das Statusmodell hat **drei Achsen mit je genau einem handgepflegten Ort**; alles andere wird
abgeleitet (validiert/synchronisiert durch `scripts/sync_letter_status.py`, `make status`):

**Achse 1 — Textquelle** (Briefdatei, `div/@type`): `original` = Transkription der Handschrift
(vom Scan, via Transkribus), `print` = OCR-Text aus der gedruckten Edition. Bereits vorhanden,
unverändert; steuert das Quellen-Badge der Briefseite.

**Achse 2 — Bearbeitungsstand** (Briefdatei, `revisionDesc/listChange/change/@status`), als
aufsteigende Leiter; der **letzte** Eintrag ist der aktuelle Stand:

| Status | Bedeutung | Wer setzt ihn |
|---|---|---|
| `draft` | Kodierung automatisch erzeugt oder in Arbeit (Transkribus-Export, Roh-OCR) | Pipeline/Bearbeiter |
| `done` | Markup vom Bearbeiter abgeschlossen | Bearbeiter |
| `reviewed` | Kodierung geprüft — **das Publikationstor** | Bearbeiter oder `check-letter-annotations`-Skill |
| `published` | Online publiziert | **nur** `scripts/sync_letter_status.py --publish`, nie von Hand |

Gilt für Transkriptionen **und** OCR-Texte gleichermaßen — ein OCR-Brief kann `reviewed` und
`published` sein (z. B. wenn kein Scan existiert und der Druck die legitime Textgrundlage ist).

```xml
<revisionDesc>
    <listChange>
        <change when="2023-08-01" who="#MiS" status="draft">File created and preprocessed automatically</change>
        <change when="2023-11-22" who="#MiS" status="done">Finished markup</change>
        <change when="2026-07-10" who="#check-letter-annotations" status="reviewed">Checked via check-letter-annotations skill (...)</change>
        <change when="2026-07-12" who="#sync-letter-status" status="published">Published online</change>
    </listChange>
</revisionDesc>
```

Der `reviewed`-Eintrag ist zugleich der Prüfnachweis (wann, von wem) und wird auf der Briefseite
als „Encoding reviewed …" angezeigt. Bei der Priorisierung von Nacharbeiten zuerst nach Briefen
filtern, deren letzter Status `draft` ist.

**Achse 3 — Publikationsstand** (Gesamtregister `lassberg-letters.xml`,
`correspDesc/@change`) — ein **abgeleiteter** Wert, den `sync_letter_status.py --write` aus den
Achsen 1+2 berechnet; von Hand wird er nicht gepflegt:

| Wert | Bedeutung |
|---|---|
| `in_register` | Brief erfasst, keine Briefdatei vorhanden |
| `preview_transcription` / `preview_print` | Briefdatei existiert, noch nicht publiziert — Seite ist als **Preview** online (mit Warnbanner, kein „Full Letter Page"-Button) |
| `online_transcription` / `online_print` | publiziert (letzter Dateistatus `published`), Quelle laut Suffix |

Zusätzlich trägt jeder Registereintrag die handgepflegte `<note type="scan">` mit den Werten
`none` (kein Scan bekannt), `internal` (Scan vorhanden, z. B. Transkribus/Archivlieferung, aber
keine öffentliche URL) oder `online` (öffentliches Digitalisat; dann muss
`<note type="url_facsimile">` gefüllt sein). Regel: Briefe ohne Scan, aber mit gedruckter
Edition, dürfen dauerhaft als OCR-Text (`*_print`) publiziert werden.

**Workflow**: Kodierung abschließen (`done`) → prüfen lassen (`reviewed`, z. B. via
`check-letter-annotations`) → `python scripts/sync_letter_status.py --publish lassberg-letter-XXXX`
(hängt den `published`-Eintrag an und aktualisiert das Register) → Briefseite/Register neu bauen
(`build-website`-Skill). `make status` prüft jederzeit die Konsistenz aller drei Achsen und
meldet Konflikte.

## Das Briefregister `data/register/lassberg-letters.xml`

Das Gesamtregister ist die **einzige Datei, die alle 3268 Briefe erfasst** (die meisten ohne
eigene Briefdatei) und damit die korpusweite Metadatenquelle für Website, Pipeline und
CMIF-Export. Ein Eintrag:

```xml
<correspDesc key="lassberg-letter-0213" ref="https://github.com/.../lassberg-letter-0213.xml" change="in_register">
  <correspAction type="sent">…</correspAction>
  <correspAction type="received">…</correspAction>
  <note type="nummer_harris">1641</note>
  <note type="journalnummer"></note>
  <note type="aufbewahrungsort">Freiburg i.Br.</note>
  <note type="aufbewahrungsinstitution">Universitätsbibliothek</note>
  <note type="signatur">Autograph Nr. 1620</note>
  <note type="url_facsimile" target="…">…</note>
  <note type="scan">online</note>
  <note type="published_in" target="…">…</note>
</correspDesc>
```

**Handgepflegt** (Ergebnis der Archiv-/Literaturrecherche): die beiden `<correspAction>`s, alle
`<note>`-Typen — `nummer_harris` (Nummer im Harris-Register 1991), `journalnummer` (Laßbergs
eigenes Briefjournal), `aufbewahrungsort`/`aufbewahrungsinstitution`/`signatur` (Überlieferung),
`url_facsimile` (öffentliches Digitalisat, mit `@target`), `scan`
(`none` | `internal` | `online`, s. Statusmodell Achse 3), `published_in` (Drucknachweis).
Vereinzelt kommen `comment`, `iiif_manifest`, `iiif_canvas` hinzu. Leere Notes bleiben als leere
Elemente stehen (Pipeline liest sie als „unbekannt", nicht als leeren String).

**Maschinell geschrieben, nie von Hand ändern**: `@change` — der abgeleitete Publikationsstand
(`scripts/sync_letter_status.py --write`, Details im Abschnitt „Statusmodell").

## Zusammenfassung: `@type`-Werte für `<rs>` im Fließtext

| `@type` | Zielregister | Wenn kein Registereintrag existiert |
|---|---|---|
| `person` | `data/register/lassberg-persons.xml` | `key=""` lassen, nicht erfinden |
| `place` | `data/register/lassberg-places.xml` | `key=""` lassen, nicht erfinden |
| `bibl` | `data/register/lassberg-literature.xml` (das **Werk**, nicht das Exemplar) | `key=""` lassen |
| `witness` | `data/register/lassberg-manuscripts.xml` (ein **konkretes** Handschriften-/Druckexemplar, s. u.) | `key=""` lassen |
| `object` | kein Register (Platzhalter für sonstige, nicht-textuelle Gegenstände) | immer `key=""` |
| `misc` | kein Register | immer `key=""` |

Für Organisationen/Körperschaften gibt es **kein eigenes Register und keinen eigenen
`<rs>`-Typ** — sie werden als `<person>`-Einträge mit `@gender="CorporateBody"` im
Personenregister geführt (s. Abschnitt „Personen"), entsprechend mit `<rs type="person">`
ausgezeichnet. Vereinzelt im Bestand vorkommendes `<rs type="organisation">` ist keine gültige
Kategorie, sondern sollte auf `type="person"` mit Verweis auf einen `CorporateBody`-Eintrag
korrigiert (oder, falls kein Eintrag existiert, als „noch nicht im Register" vermerkt) werden.

## Personen
Zentraler Bestandteil der Brieferschließung sind die an der Korrespondenz beteiligten Personen. 
Dies betrifft sowohl Absender und Empfänger der Briefe als auch darin genannte Personen.
In den Briefen selbst werden Personen auf drei Wegen ausgezeichnet:

1. als `<persName>` im Element `<correspAction>` der `<correspDesc>`.
2. als `<ref type="cmif:mentionsPerson">` unter Rückgriff auf [CMIF Vokabular](https://encoding-correspondence.bbaw.de/v1/CMIF.html#c-4-2) im Element `<note type="mentioned">` in der `<correspDesc>` gemeinsam mit weiteren genannten Inhalten.
3. als `<rs type="person">` Element im Fließtext des Briefes.

Alle Elemente verweisen durch das Attribut `@key` über eine eindeutige ID auf das interne Personenregister in `data/register/lassberg-persons.xml` (ID-Muster: `lassberg-correspondent-NNNN`, vierstellig, nicht brieflokal sondern korpusweit eindeutig — dieselbe Person hat in jedem Brief denselben Schlüssel). 
Dieses Register wurde zunächst automatisch aus Harris, Martin: Joseph Maria Christoph Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. Mit einer
Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. Die erste geschlossene, wissenschaftlich fundierte Würdigung von Lassbergs Wirken und Werk. Beihefte zum Euphorion Heft 25/C. Heidelberg 1991
erstellt und die dort verzeichneten Personen mit einer ggf. vorhandenen GND Nummer ergänzt. Über diese GND Nummer wurden dann weitere GND-Informationen abgefragt und dem Datensatz hinzugefügt, außerdem wurden ggf. vorhandene weiterführende Infromationen verlinkt.
Insbesondere Standen hier Informationen im Vordergrund, die einen Mehrwert für die Analyse des Gelehrten Netzwerkes Laßbergs aufweisen, so Informationen zu Beruf und Bildungsstand, Geschlecht und Alter.
Unterschieden werden diese Personen über das Attribut `@type="contemporary|historical` in Zeitgenossen (einschließlich Herausgeber mittelalterlicher Texte des 16. und 17. Jahrhunderts), 
mit denen Laßberg in einen diskursiven Austausch - trat sowie historische Persönlichkeiten der antiken und mittelalterlichen Geschichte, die Laßberg als Untersuchungsgegenstände betrachtete - zum Beispiel Hartmann von Aue.
Entsprechend inkludiert der Wert 'historical' auch mythologische Figuren der Geschichte. Geschlechter werden durch das Element `<personGrp>` ausgezeichnet. Das Attribut `@ref` verweist nach Möglichkeit auf eine eindeutige GND-Nummer, ggf. auf eine vorhandene eindeutige URL (z.B. Wikipedia).

```xml                
<person xml:id="lassberg-correspondent-0406" gender="male" ref="https://d-nb.info/gnd/118529560" type="historical">
    <persName type="main">Einhard</persName>
    <education/>
    <occupation>Gelehrter</occupation>
    <occupation>Geschichtsschreiber</occupation>
    <birth when="0770">0770</birth>
    <ref target="https://de.wikipedia.org/wiki/Einhard">https://de.wikipedia.org/wiki/Einhard</ref>
</person>
```

`@gender` kennt neben `male`/`female` auch `none` (für `<personGrp>`, s. u.), `notKnown` (Person
identifiziert, Geschlecht aber nicht ermittelbar) sowie **`CorporateBody`** — dieser Wert markiert
Einträge, die keine natürliche Person, sondern eine **Institution, einen Verlag, eine Behörde oder
einen Verein** repräsentieren (z. B. `Allgemeine Geschichtforschende Gesellschaft der Schweiz`,
`Artaria (Verlag)`, `Badische Amortisationskasse`). Solche Einträge werden trotzdem im
Personenregister geführt und im Text ganz normal als `<rs type="person" key="…">` ausgezeichnet
— es gibt kein separates Organisationsregister. `@ref=""` bzw. `<birth when=""/>` (leeres
Attribut statt fehlendem Element) ist der übliche Platzhalter, wenn ein Wert noch nicht ermittelt
wurde.

`<occupation>` und `<education>` sind freitextliche, nicht kontrollierte deutsche
Berufs-/Bildungsbezeichnungen (z. B. `Historiker`, `Bibliothekar`, `Dr. phil.`) — mehrere
`<occupation>`-Elemente pro Person sind üblich, es existiert kein Verweis auf eine externe
Normdatei für diese Werte.

```xml
<personGrp xml:id="lassberg-correspondent-0415" gender="none" ref="https://de.wikipedia.org/wiki/Neuenburg_(Adelsgeschlecht)" type="historical">
    Neuenburg (Geschlecht)
    <ref target="https://de.wikipedia.org/wiki/Neuenburg_(Adelsgeschlecht)"/>
</personGrp>
```

`<personGrp>` steht für Familien bzw. Adelsgeschlechter als Kollektiv (z. B. „Klingen
(Adelsgeschlecht)", „Herren von Kenzingen") — zu unterscheiden von einer einzelnen benannten
Person mit demselben Nachnamen, die einen eigenen `<person>`-Eintrag erhält.

Eine weitere Form der Auszeichnung betrifft Personen, die als Autoren lediglich über die Nennnung ihrer Werke in Erscheinung treten. Diese werden im Literaturregister (s.u.) als `<author>` ausgezeichnet und über das Attribut `@key` mit dem Personenregister verbunden.

Im Fließtext werden Personen nicht ausschließlich über ihren Eigennamen erwähnt, sondern häufig
auch über eine relationale Beschreibung, sobald sie im Kontext bereits eingeführt sind (z. B.
„seiner Wittwe", „meine Nichte", „meine Schwägerin"). Auch solche Erwähnungen erhalten
`<rs type="person" key="…">`, sofern die gemeinte Person identifizierbar ist:

```xml
die anhaltende Krankheit meines Freundes <rs type="person"
    key="../register/lassberg-persons.xml#lassberg-correspondent-0224">v. Ittner</rs> ...
bin ich mit seiner <rs type="person"
    key="../register/lassberg-persons.xml#lassberg-correspondent-0624">Wittwe</rs>
und <rs type="person"
    key="../register/lassberg-persons.xml#lassberg-correspondent-0625">Tochter</rs>
hier angekommen
```

## Orte

Analog zu den Personen werden auch Orte auf drei Wegen ausgezeichnet:

1. als `<placeName>` im Element `<correspAction>` (Absendeort des Briefes).
2. als `<ref type="cmif:mentionsPlace">` im Element `<note type="mentioned">`.
3. als `<rs type="place">` im Fließtext.

Alle drei verweisen über `@key`/`@target` auf `data/register/lassberg-places.xml` (ID-Muster:
`lassberg-place-NNNN`). Das Ortsregister ist deutlich schlanker aufgebaut als das Personenregister
und kennt keine `contemporary`/`historical`-Unterscheidung:

```xml
<place xml:id="lassberg-place-0001">
    <placeName ref="https://www.wikidata.org/wiki/Q14274">Aarau</placeName>
    <location>
        <geo ana="wgs84">47.4,8.05</geo>
    </location>
    <desc type="wikidata">Hauptstadt des Kantons Aargau</desc>
</place>
```

`<placeName>` trägt den Wikidata-Link direkt als `@ref` (nicht als separates `<ref>`-Kindelement
wie im Personenregister). `<location><geo ana="wgs84">` speichert die Koordinaten im Format
`Breitengrad,Längengrad` (WGS84, kommasepariert). `<desc type="wikidata">` ist eine optionale, aus
Wikidata übernommene Kurzbeschreibung und nicht bei jedem Eintrag vorhanden.

Wie bei Personen gilt: Historische Gebietsbezeichnungen, die heute keiner modernen Verwaltungseinheit
mehr entsprechen (z. B. „Schwaben", „Asien" als Herkunftsregion), werden trotzdem als eigener
`<place>`-Eintrag geführt, sofern sie im Korpus wiederholt referenziert werden.

## Literatur
Zentrales Ziel der Erschließung sind die in der Korrespondenz erwähnten Texte, da sie einen Einblick in die diskursiven Netzwerke in Laßbergs Umfeld ermöglichen.
Analog zur Erschließung der Personen und Orte erfolgt sie auf den Ebenen der 
1. `<correspDesc>` als `<ref type="cmif:mentionsBibl">` unter Rückgriff auf [CMIF Vokabular](https://encoding-correspondence.bbaw.de/v1/CMIF.html#c-4-2) im Element `<note type="mentioned">`.
2. als `<rs type="bibl">` im Fließtext des Briefes.

Auch hier wird durch ein `@key`Attribut auf das Literaturregister verwiesen (ID-Muster:
`lassberg-literature-NNNN`), in dem die Titel entsprechend verzeichnet und durch das Attribut `@type` in `historicalSource|contemporaryPublication` differenziert sind. Ein dritter Wert, `unknown`, markiert Werke, die bislang nicht sicher identifiziert werden konnten (Platzhaltertitel „Unbekannt").
Diese Unterscheidung geschieht, um zwischen den zeitgenössischen Diskursen und der Rezeption bestimmter Ausgaben, die in den Briefen genannt werden, sowie der eigentlichen Mittelalterlichen Quelle zu unterscheiden.
Allerdings ist diese Unterscheidung in vielen Fällen nicht ohne weiteres möglich und Bedarf weiterer Untersuchung im Verlauf des Projekts. ANgegeben werden, so möglich, jeweils Autor oder Editor des Werkes im Element `<author>`, 
das im Projektverlauf näher differenziert werden muss. Dann erfolgt die Titelnennung in `<title>`, der Veröffentlichungsort in `pubPlace>` sowie das Datum der veröffentlichung in `<date>`. 
Bei historischen Quellen enthalten diese Elemente das vermutete Entstehungsdatum bzw. den vermuteten Entstehungsort. Die Elemente `<author>` und `<pubPlace>`verweisen außerdem über ein `@key`Attribut auf das Personen- und Ortsregister.
Nach Möglichkeit der der Eintrag durch einen Identifier in `<idno>` angegeben, etwa durch eine VD16, VD17 oder VD18 Nummer oder der RI-OPAC URL. Bei Quellen wird auf eine bestehende www.queschichtsquellen.de URL zurück gegriffen.

```xml
<bibl xml:id="lassberg-literature-0011" type="contemporaryPublication">
    <author key="">Zapf, Georg W.</author>
    <title>Monumenta Anecdota Historiam Germaniae Illustrantia</title>
    <pubPlace key="">Augsburg</pubPlace>
    <date>1785</date>
    <idno type="contemporaryPublication">VD18-90029372</idno>
</bibl>
```

`<idno>` wird im Bestand mit unterschiedlichen `@type`-Werten je nach Herkunft der Kennung
verwendet:

| `idno/@type` | Bedeutung |
|---|---|
| `vd16`, `vd17`, `vd18` | Verzeichnis der im deutschen Sprachraum erschienenen Drucke des 16./17./18. Jahrhunderts (`vd16` bislang nicht im Bestand verwendet, aber vorgesehen) |
| `gw` | Gesamtkatalog der Wiegendrucke (Inkunabeln, Drucke bis ca. 1500; bislang nicht im Bestand verwendet, aber vorgesehen) |
| `gnd` | Gemeinsame Normdatei (Werk-/Normdatensatz) |
| `handschriftencensus` | Verweis auf [handschriftencensus.de](https://handschriftencensus.de) (mittelalterliche deutschsprachige Handschriften) |
| `geschichtsquellen` | Verweis auf [geschichtsquellen.de](https://geschichtsquellen.de) (Repertorium „Geschichtsquellen des deutschen Mittelalters") |
| `riopac` | Verweis auf den RI-OPAC (Regesta Imperii) |
| `googlebooks` | Digitalisat bei Google Books |
| `doi` | Digital Object Identifier (bislang nicht im Bestand verwendet, aber vorgesehen) |
| `uri` | generischer, sonst nicht kategorisierbarer Persistent-Identifier |
| `kalliope` | Verweis auf den [Kalliope-Verbundkatalog](https://kalliope-verbund.info) (Nachlässe, Autographen) |
| `mdz` | Digitalisat der Münchener DigitalisierungsZentrum (Bayerische Staatsbibliothek) |
| `dnb` | Katalogeintrag der Deutschen Nationalbibliothek (nicht zu verwechseln mit `gnd`, dem Normdatensatz) |
| `hathitrust` | Digitalisat bei HathiTrust |
| `bsb`, `bsbink` | Katalog-/Inkunabel-Signatur der Bayerischen Staatsbibliothek |
| `istc` | Incunabula Short Title Catalogue |
| `worldcat` | WorldCat-Verbundkatalog |
| `bavarikon` | Digitalisat/Objekt bei [bavarikon.de](https://www.bavarikon.de) |
| `archive` | Digitalisat bei archive.org |
| `dmgh` | Digitale MGH (Monumenta Germaniae Historica) |
| `varia` | sonstige, nicht weiter kategorisierte externe Verweise (mit Abstand am häufigsten verwendet) |

Die Basisliste ist in `src/enrich_bibl_register.py` (`IDNO_TYPES`) kodifiziert — dort allerdings
mit `opac-ri` statt `riopac` benannt; **im Bestand wird durchgängig `riopac` verwendet**, das ist
die maßgebliche Schreibweise. Die zusätzlichen Typen ab `kalliope` sind (Stand Juli 2026) noch
nicht in `IDNO_TYPES` nachgetragen, aber bereits in Gebrauch (siehe
`data/register/lassberg-literature.COMBINED.csv`) — bei Gelegenheit dort ergänzen.

### `@ana="projected"` — angekündigte, aber nicht verifizierbar erschienene Werke

Briefe erwähnen gelegentlich Publikationsprojekte, die zum Zeitpunkt des Briefes erst geplant,
angekündigt oder um Beiträge/Subskribenten beworben werden (z. B. ein Verleger, der um Material für
ein noch ungeschriebenes Sammelwerk bittet). Das ist ein anderer Fall als `type="unknown"`: Dort
wissen wir nicht, *welches* Werk gemeint ist; hier wissen wir es genau, können aber (noch) nicht
bestätigen, dass das Projekt je als fertige Publikation erschienen ist.

Für diesen Fall wird `@ana="projected"` auf das `<bibl>`-Element gesetzt, zusätzlich zum
inhaltlich zutreffendsten `@type`-Wert (meist `contemporaryPublication`, da als Publikation
angekündigt). Ein `<note type="review">` hält fest, welche Recherche zur Verifikation
unternommen wurde (und erfolglos blieb) — das unterscheidet einen recherchierten Fehlschlag von
einem noch gar nicht untersuchten Eintrag:

```xml
<bibl xml:id="lassberg-literature-NNNN" type="contemporaryPublication" ana="projected">
    <author key="…">…</author>
    <title>[im Brief angekündigter/beworbener Projekttitel]</title>
    <idno type="varia">-</idno>
    <note type="review" resp="…">Als Projekt/Subskriptionswerbung in Brief NNNN (Datum) erwähnt;
        Recherche (GND, VD16-18, WebSearch) ergab keinen Beleg für eine tatsächlich erschienene
        Publikation. Quelle: …, bestätigt YYYY-MM-DD.</note>
</bibl>
```

Wichtig: `@ana="projected"` beschreibt den **Rechercheausgang**, nicht automatisch den
historischen Zustand zum Briefdatum — stellt sich später (in diesem oder einem späteren Brief,
oder durch weitere Recherche) heraus, dass das Werk doch erschienen ist, wird der Eintrag zu einem
regulären Eintrag ausgebaut (Verlag, Erscheinungsjahr, `idno` etc. ergänzt) und `@ana="projected"`
entfernt; ein Hinweis auf den ursprünglichen Ankündigungskontext kann in der `<note>` verbleiben.
Beispiel für diesen Übergang: `lassberg-literature-0223` — in `lassberg-letter-0993.xml` (1825)
warb der Buchhändler Dalp noch um Beiträge zu einer unbetitelten Projektidee
("Beschreibung aller Ritterburgen der Schweiz"); die Recherche konnte das Werk aber bereits
eindeutig mit der 1828–1839 erschienenen, unter Gustav Schwab herausgegebenen Publikation *Die
Schweiz in ihren Ritterburgen und Bergschlössern* identifizieren (an der auch der Briefautor
Pupikofer später als Beiträger mitwirkte) — der Eintrag wurde deshalb direkt regulär angelegt,
ohne den Umweg über `@ana="projected"`.

### Drei Ebenen: Werk, Ausgabe, Exemplar

Literaturerwähnungen in den Briefen liegen faktisch auf drei unterschiedlichen Ebenen, die beim
Kodieren häufig durcheinandergehen, weil der Brieftext selbst meist nicht klar zwischen ihnen
unterscheidet: dem **Werk** als solchem (z. B. „der Tristan"), einer **konkreten Ausgabe/Edition**
dieses Werks (z. B. „Gottfried von Straßburgs Tristan in der Ausgabe von Hagen/Büsching") oder
einem **einzelnen physischen Exemplar** dieser Ausgabe bzw. einer Handschrift (z. B. „mein
Exemplar, das ich Ihnen sende"). Alle drei werden unterschiedlich kodiert, aber im selben
Literaturregister bzw. im Handschriften-/Druckexemplarregister geführt — es gibt kein viertes
Register, nur eine bewusste Differenzierung innerhalb der bestehenden zwei:

| Ebene | Kodierung | Merkmale |
|---|---|---|
| **Werk** (abstrakt) | `<bibl>`/`<biblStruct type="work">` in `lassberg-literature.xml` | nur Titel + Normdaten (GND-Filter `type:Work`), **kein** `<pubPlace>`/`<date>` — die abstrakte Textidentität, unabhängig von einer bestimmten Druck- oder Editionsgeschichte |
| **Ausgabe** (konkrete Edition) | `<bibl>`/`<biblStruct>` (ohne `type="work"`) in `lassberg-literature.xml`, mit `<pubPlace>`/`<date>`/`<idno type="vd16\|vd17\|vd18\|gw\|…">` | das ist bereits der faktische Regelfall der meisten bestehenden Einträge im Register — die meisten heutigen `<bibl>`-Einträge sind, auch wenn `docs/TEI.md` sie bisher unter „Werk" gefasst hat, tatsächlich Ausgaben-Einträge |
| **Exemplar** (physische Kopie) | `<witness>` in `lassberg-manuscripts.xml` | `@corresp` verweist auf die zugehörige Ausgabe oder, falls keine spezifische Ausgabe identifizierbar ist, auf das Werk; siehe folgende Kategorie |

In der Praxis lässt sich diese Zuordnung selten mechanisch aus dem Brieftext ableiten — ob eine
Erwähnung das Werk allgemein, eine bestimmte Ausgabe oder ein konkretes Exemplar meint, erfordert
Lektüre des Kontexts (wird zurückgesendet? wird eine Signatur/ein Bibliotheksort genannt? wird nur
der Werktitel genannt?). Bei Unsicherheit gilt dieselbe Regel wie bei der Entitätsverlinkung
generell: die spezifischste **belegbare** Ebene wählen, nicht raten — im Zweifel eher auf der
Werk-Ebene verorten und die genauere Zuordnung offenlassen, statt eine Ausgabe oder ein Exemplar
zu erfinden, das sich aus dem Text nicht sicher ergibt.

## Handschriften- und Druckexemplare (Textzeugen)

Laßbergs Briefe kreisen zu einem großen Teil um den Leihverkehr, Abschriften und den Verbleib
konkreter Bücher und Handschriften — nicht nur um Werke im abstrakten Sinn. Beispiele aus dem
Korpus: „ich schreibe wirklich das Breviarium dieser Handschrift ab", „könnten Sie mir wohl eine
Abschrift der Urkunde verschaffen", „ich sende Ihnen das einzige Exemplar vom III. Bande des
Liedersaales, das ich bei Handen habe". In allen diesen Fällen ist nicht der Text als solcher
gemeint (der ggf. bereits im Literaturregister erfasst ist), sondern ein **bestimmtes,
identifizierbares physisches Exemplar** — eine Handschrift in einer bestimmten Bibliothek mit
eigener Signatur, oder ein bestimmtes Druckexemplar (ggf. mit Provenienz, Anmerkungen,
Randglossen).

Diese Unterscheidung Werk/Exemplar entspricht der aus der Handschriften- und Editionskunde
bekannten Unterscheidung zwischen Text und **Textzeuge** (engl. *witness*) und wird als eigene
Kategorie eingeführt, die weder im Literatur- noch im (kaum genutzten) Objektregister sauber
abzubilden wäre.

### Auszeichnung im Brief

Im Fließtext: `<rs type="witness" key="…">`. In `<note type="mentioned">` weiterhin
`<ref type="cmif:mentionsBibl">` (CMIF kennt keine eigene Kategorie für Exemplare; die
Unterscheidung ergibt sich aus dem Zielregister im `@target`).

```xml
<!-- Fließtext -->
Ich schreibe wirklich das <rs type="witness"
    key="../register/lassberg-manuscripts.xml#lassberg-witness-0001">Breviarium dieser
    Handschrift</rs> ab, welche wol so bald noch nicht im Druk erscheinen wird.

<!-- note type="mentioned" -->
<ref type="cmif:mentionsBibl" target="../register/lassberg-manuscripts.xml#lassberg-witness-0001">
    <rs>Breviarium dieser Handschrift</rs>
</ref>
```

### Register `data/register/lassberg-manuscripts.xml`

ID-Muster: `lassberg-witness-NNNN`. Jeder Eintrag ist ein `<witness>` mit `@type`
(`manuscript`|`print`) und — sofern das zugrundeliegende Werk im Literaturregister bereits
erfasst ist — einem `@corresp`-Attribut, das auf den entsprechenden `<bibl>`-Eintrag verweist.
Innerhalb von `<witness>` wird, in Anlehnung an die bereits im Projekt verwendeten
`msIdentifier`-Angaben (vgl. `<sourceDesc><msDesc>` im `teiHeader` jedes Briefes), ein `<bibl>`
mit `<settlement>`/`<repository>`/`<idno type="signature">` verwendet:

```xml
<!-- Handschrift -->
<witness xml:id="lassberg-witness-0001" type="manuscript"
    corresp="../register/lassberg-literature.xml#lassberg-literature-0028">
    <bibl>
        <settlement>Stuttgart</settlement>
        <repository>Württembergische Landesbibliothek</repository>
        <idno type="signature">Cod.HB.XIII.1</idno>
    </bibl>
</witness>

<!-- Druckexemplar -->
<witness xml:id="lassberg-witness-0002" type="print"
    corresp="../register/lassberg-literature.xml#lassberg-literature-0026">
    <bibl>
        <settlement>Winterthur</settlement>
        <repository>Stadtbibliothek</repository>
        <idno type="signature">Ms BRH 46/5</idno>
        <note>Laßbergs eigenes, mit handschriftlichen Anmerkungen versehenes Exemplar.</note>
    </bibl>
</witness>
```

Ist das zugrundeliegende Werk noch nicht im Literaturregister erfasst, bleibt `@corresp` leer
(`corresp=""`) statt einen Verweis zu erfinden. Ebenso wird `key=""` im Brieftext belassen, wenn
ein Exemplar zwar als solches erkannt, aber noch nicht ins Register aufgenommen wurde — analog zum
Vorgehen bei Personen, Orten und Werken.

### Abgrenzung zu `object`/`misc`

`type="witness"` gilt ausschließlich für Text tragende Objekte (Handschriften, Drucke,
Abschriften). Für sonstige im Brief erwähnte physische Gegenstände ohne (bekannten) Textinhalt —
Urkunden ohne identifizierten Text, Siegel, Alltagsgegenstände — bleibt `type="object"` bzw.
`type="misc"` zuständig; für diese existiert weiterhin kein Register, `key=""` ist hier der
dauerhafte Normalzustand, kein Kodierungsfehler.
