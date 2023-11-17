# TEI-Documentation

## Personen
Zentraler Bestandteil der Brieferschließung sind die an der Korrespondenz beteiligten Personen. 
Dies betrifft sowohl Absender und Empfänger der Briefe als auch dartin genannte Personen.
In den Briefen selbst werden Personen auf drei Wegen ausgezeichnet:

1. als `<persName>` im Element `<correspAction>` der `<correspDesc>`.
2. als `<ref type="cmif:mentionsPerson">` unter Rückgriff auf [CMIF Vokabular](https://encoding-correspondence.bbaw.de/v1/CMIF.html#c-4-2) im Element `<note type="mentioned">` in der `<correspDesc>` gemeinsam mit weiteren genannten Inhalten.
3. als `<rs type="person">` Element im Fließtext des Briefes.

Alle Elemente verweisen durch das Attribut `@key` über eine eindeutige ID auf das interne Personenregister in `data/register/lassberg-persons.xml`. 
Dieses Register wurde zunächst automatisch aus Harris, Martin: Joseph Maria Christoph Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. Mit einer
Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. Die erste geschlossene, wissenschaftlich fundierte Würdigung von Lassbergs Wirken und Werk. Beihefte zum Euphorion Heft 25/C. Heidelberg 1991
erstellt und die dort verzeichneten Personen mit einer ggf. vorhandenen GND Nummer ergänzt. Über diese GND Nummer wurden dann weitere GND-Informationen abgefragt und dem Datensatz hinzugefügt, außerdem wurden ggf. vorhandene weiterführende Infromationen verlinkt.
Insbesondere Standen hier Informationen im Vordergrund, die einen Mehrwert für die Analyse des Gelehrten Netzwerkes Laßbergs aufweisen, so Informationen zu Beruf und Bildungsstand, Geschlecht und Alter.
Unterschieden werden diese Personen über das Attribut `@type="contemporary|historical` in Zeitgenossen (einschließlich bereits verstorbene Personen des 17. und 18. Jahrhunderts), 
mit denen Laßberg in einen diskursiven Austausch - zum Beispiel Heinrich Canisius - trat sowie historische Persönlichkeiten der antiken und mittelalterlichen Geschichte, die Laßberg als Untersuchungsgegenstände betrachtete - zum Beispiel Hartmann von Aue.
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

```xml
<personGrp xml:id="lassberg-correspondent-0415" gender="none" ref="https://de.wikipedia.org/wiki/Neuenburg_(Adelsgeschlecht)" type="historical">
    Neuenburg (Geschlecht)
    <ref target="https://de.wikipedia.org/wiki/Neuenburg_(Adelsgeschlecht)"/>
</personGrp>
```

Eine weitere Form der AUszeichnung betrifft Personen, die als Autoren lediglich über die Nennnung ihrer Werke in Erscheinung treten. Diese werden im Literaturregister (s.u.) als `<author>` ausgezeichnet und über das Attribut `@key` mit dem Personenregister verbunden.  

## Orte

## Literatur
