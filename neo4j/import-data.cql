CALL apoc.load.xml('https://raw.githubusercontent.com/michaelscho/lassberg/gh-pages/data/register/lassberg-persons.xml') 
YIELD value 
UNWIND value._children AS child
WITH child
WHERE child._type = "text"
UNWIND child._children AS grandChild
WITH grandChild
WHERE grandChild._type = "body"
UNWIND grandChild._children AS greatGrandChild
WITH greatGrandChild
WHERE greatGrandChild._type = "div"
UNWIND greatGrandChild._children AS greatGreatGrandChild
WITH greatGreatGrandChild
WHERE greatGreatGrandChild._type = "listPerson"
UNWIND greatGreatGrandChild._children AS greatGreatGreatGrandChild
WITH greatGreatGreatGrandChild
WHERE greatGreatGreatGrandChild._type = "person"

MERGE (p:Person {id: greatGreatGreatGrandChild.`xml:id`})
SET p.name = [x IN greatGreatGreatGrandChild._children WHERE x._type = "persName" | x._text][0],
    p.gender = greatGreatGreatGrandChild.gender,
    p.ref = greatGreatGreatGrandChild.ref,
    p.occupation = [x IN greatGreatGreatGrandChild._children WHERE x._type = "occupation" | x._text][0],
    p.education = [x IN greatGreatGreatGrandChild._children WHERE x._type = "education" | x._text][0],
    p.birth = [x IN greatGreatGreatGrandChild._children WHERE x._type = "birth" | x._text][0],
    p.wikipediaRef = [x IN greatGreatGreatGrandChild._children WHERE x._type = "ref" | x._text][0]

RETURN p.name, p.gender, p.ref, p.occupation, p.education, p.birth, p.wikipediaRef LIMIT 10;


LOAD CSV WITH HEADERS FROM 'https://raw.githubusercontent.com/michaelscho/lassberg/gh-pages/data/register/register.csv' AS row FIELDTERMINATOR ';'

// Create or update the letter node
MERGE (l:Letter {id: row.ID})
SET l += {
    nummerHarris: row.Nummer_Harris,
    ort: row.Ort,
    name: row.Name,
    gnd: row.GND,
    wiki: row.Wiki,
    journalnummer: row.Journalnummer,
    aufbewahrungsort: row.Aufbewahrungsort,
    aufbewahrungsinstitution: row.Aufbewahrungsinstitution,
    jahr: toInteger(row.Jahr),
    datum: row.Datum,
    letter_text: row.letter_text,
    status_letter_text: row.status_letter_text,
    summary_en: row.summary_en,
    persons_mentioned: row.persons_mentioned,
    topics_mentioned: row.topics_mentioned,
    normalized_text: row.normalized_text
}

// Create or find the person node
MERGE (p:Person {id: row.person_id})

// Create or find the Joseph von Laßberg node
MERGE (lassberg:Person {id: "lassberg-correspondent-0373"})

// Connect based on 'VON' or 'AN'
FOREACH (_ IN CASE WHEN row.`VON/AN` = "AN" THEN [1] ELSE [] END | 
    MERGE (p)-[:SENT_LETTER]->(l)
    MERGE (l)-[:RECEIVED_LETTER]->(lassberg))

FOREACH (_ IN CASE WHEN row.`VON/AN` = "VON" THEN [1] ELSE [] END | 
    MERGE (lassberg)-[:SENT_LETTER]->(l)
    MERGE (l)-[:RECEIVED_LETTER]->(p))

RETURN l, p LIMIT 10;