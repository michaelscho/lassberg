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

```xml
<personGrp xml:id="lassberg-correspondent-0415" gender="none" ref="https://de.wikipedia.org/wiki/Neuenburg_(Adelsgeschlecht)" type="historical">
    Neuenburg (Geschlecht)
    <ref target="https://de.wikipedia.org/wiki/Neuenburg_(Adelsgeschlecht)"/>
</personGrp>
```

Eine weitere Form der Auszeichnung betrifft Personen, die als Autoren lediglich über die Nennnung ihrer Werke in Erscheinung treten. Diese werden im Literaturregister (s.u.) als `<author>` ausgezeichnet und über das Attribut `@key` mit dem Personenregister verbunden.  

## Orte

## Literatur
Zentrales Ziel der Erschließung sind die in der Korrespondenz erwähnten Texte, da sie einen Einblick in die diskursiven Netzwerke in Laßbergs Umfeld ermöglichen.
Analog zur Erschließung der Personen und Orte erfolgt sie auf den Ebenen der 
1. `<correspDesc>` als `<ref type="cmif:mentionsBibl">` unter Rückgriff auf [CMIF Vokabular](https://encoding-correspondence.bbaw.de/v1/CMIF.html#c-4-2) im Element `<note type="mentioned">`.
2. als `<rs type="bibl">` im Fließtext des Briefes.

Auch hier wird durch ein `@key`Attribut auf das Literaturregister verwiesen, in dem die Titel entsprechend verzeichnet und durch das Attribut `@type` in `historicalSource|contemporaryPublication` differenziert sind.
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