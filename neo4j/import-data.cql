// Add persons
CALL apoc.load.xml('https://raw.githubusercontent.com/michaelscho/lassberg/main/data/register/lassberg-persons.xml') 
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
UNWIND greatGreatGrandChild._children AS personOrGroup
WITH personOrGroup
WHERE personOrGroup._type IN ["person", "personGrp"]  // Modified to include personGrp

MERGE (p:Person {id: personOrGroup.`xml:id`, type: personOrGroup.`type`})
SET p.name = [x IN personOrGroup._children WHERE x._type = "persName" | x._text][0],
    p.gender = personOrGroup.gender,
    p.gnd = personOrGroup.ref,
    p.occupation = [x IN personOrGroup._children WHERE x._type = "occupation" | x._text][0],
    p.education = [x IN personOrGroup._children WHERE x._type = "education" | x._text][0],
    p.birth = [x IN personOrGroup._children WHERE x._type = "birth" | x._text][0],
    p.wikipediaRef = [x IN personOrGroup._children WHERE x._type = "ref" | x._text][0]

RETURN p.name, p.gender, p.gnd, p.occupation, p.education, p.birth, p.wikipediaRef LIMIT 10;


// Add places
CALL apoc.load.xml('https://raw.githubusercontent.com/michaelscho/lassberg/main/data/register/lassberg-places.xml') 
YIELD value 
UNWIND value._children AS child
WITH child
WHERE child._type = "text"
UNWIND child._children AS grandChild
WITH grandChild
WHERE grandChild._type = "body"
UNWIND grandChild._children AS greatGrandChild
WITH greatGrandChild
WHERE greatGrandChild._type = "listPlace"
UNWIND greatGrandChild._children AS place
WITH place
WHERE place._type = "place"

MERGE (p:Place {id: place.`xml:id`})
SET p.name = [x IN place._children WHERE x._type = "placeName" | x._text][0],
    p.wikidata = [x IN place._children WHERE x._type = "placeName" | x.`ref`][0],
    p.latitude = toFloat(split([geo IN place._children WHERE geo._type = "location" | [x IN geo._children WHERE x._type = "geo" | x._text][0]][0], ",")[0]),
    p.longitude = toFloat(split([geo IN place._children WHERE geo._type = "location" | [x IN geo._children WHERE x._type = "geo" | x._text][0]][0], ",")[1])

RETURN p.name, p.wikidata, p.latitude, p.longitude;


// Add texts
CALL apoc.load.xml('https://raw.githubusercontent.com/michaelscho/lassberg/main/data/register/lassberg-literature.xml')
YIELD value
UNWIND value._children AS child
WITH child
WHERE child._type = "text"
UNWIND child._children AS grandChild
WITH grandChild
WHERE grandChild._type = "body"
UNWIND grandChild._children AS greatGrandChild
WITH greatGrandChild
WHERE greatGrandChild._type = "listBibl"
UNWIND greatGrandChild._children AS bibl
WITH bibl
WHERE bibl._type = "bibl"
CREATE (b:Bibl {id: bibl.xml:id, type: bibl.type})
SET b.title = head([x IN bibl._children WHERE apoc.meta.cypher.type(x)='MAP' AND x._text IS NOT NULL AND x._type = "title" | x._text]),
    b.date = head([x IN bibl._children WHERE apoc.meta.cypher.type(x)='MAP' AND x._text IS NOT NULL AND x._type = "date" | x._text]),
    b.idno = head([x IN bibl._children WHERE apoc.meta.cypher.type(x)='MAP' AND x._text IS NOT NULL AND x._type = "idno" | x._text]),
    b.author = [x IN bibl._children WHERE apoc.meta.cypher.type(x)='MAP' AND x._text IS NOT NULL AND x._type = "author" | x._text][0],
    b.authorID = [x IN bibl._children WHERE apoc.meta.cypher.type(x)='MAP' AND x._text IS NOT NULL AND x._type = "author" | x.key],	  
    b.pubPlace = [x IN bibl._children WHERE apoc.meta.cypher.type(x)='MAP' AND x._text IS NOT NULL AND x._type = "pubPlace" | x._text][0]
RETURN b.title, b.date, b.idno, b.author, b.authorID, b.pubPlace LIMIT 10;


// Replace path in ID
MATCH (b:Bibl)
WHERE b.authorID IS NOT NULL
SET b.authorID = [x IN b.authorID | apoc.text.replace(x, '../register/lassberg-persons.xml#', '')]
RETURN b;


// Create connections between Bibl and Person nodes
MATCH (b:Bibl)
WHERE b.authorID IS NOT NULL
UNWIND b.authorID AS authorID
MATCH (p:Person {id: authorID})

CREATE (p)-[:HAS_AUTHORED]->(b);


// Create letters
LOAD CSV WITH HEADERS FROM 'https://raw.githubusercontent.com/michaelscho/lassberg/main/data/register/register.csv' AS row FIELDTERMINATOR ';'

// Create or update the letter node
MERGE (l:Letter {id: row.ID})
SET l.Nummer_Harris = row.Nummer_Harris,
    l.Journalnummer = row.Journalnummer,
    l.Signatur = row.Signatur,
    l.published_in = row.published_in,
    l.Datum = row.Datum

// Create or find the person node for sender and receiver
MERGE (sender:Person {id: row.SENT_FROM_ID})
MERGE (receiver:Person {id: row.RECIVED_BY_ID})

// Create or find the place node for sending location
MERGE (sendingPlace:Place {id: row.Absendeort_id})

// Connect letter to sender and receiver
MERGE (sender)-[:SENT]->(l)
MERGE (l)-[:RECEIVES]->(receiver)

// Connect letter to sending place
MERGE (l)-[:SENT_FROM]->(sendingPlace)
<<<<<<< HEAD

RETURN l;

// Load in mentiones in letters
// Iterate through each letter
MATCH (l:Letter)
WITH l, 'https://raw.githubusercontent.com/michaelscho/lassberg/main/data/letters/' + l.id + '.xml' AS url

// Attempt to load the XML file
CALL apoc.load.xml(url, null, {failOnError: false}) 
YIELD value AS xmlFile
WITH l, url, xmlFile, xmlFile IS NOT NULL AS fileExists
SET l.processed = fileExists

// Proceed only if the XML file exists
WITH l, url, xmlFile
WHERE l.processed AND xmlFile IS NOT NULL
UNWIND xmlFile._children AS child
WITH l, child
WHERE child._type = "note" AND child.type = "mentioned"
UNWIND child._children AS ref
WITH l, ref
WHERE ref._type IN ["cmif:mentionsPerson", "cmif:mentionsPlace", "cmif:mentionsBibl"]

// Create or find the mentioned nodes and link them to the letter
FOREACH (item IN CASE WHEN ref._type = "cmif:mentionsPerson" THEN [1] ELSE [] END |
    MERGE (p:Person {id: apoc.text.replace(ref.target, '../register/lassberg-persons.xml#', '')})
    MERGE (l)-[:MENTIONS]->(p)
)
FOREACH (item IN CASE WHEN ref._type = "cmif:mentionsPlace" THEN [1] ELSE [] END |
    MERGE (place:Place {id: apoc.text.replace(ref.target, '../register/lassberg-places.xml#', '')})
    MERGE (l)-[:MENTIONS]->(place)
)
FOREACH (item IN CASE WHEN ref._type = "cmif:mentionsBibl" THEN [1] ELSE [] END |
    MERGE (b:Bibl {id: apoc.text.replace(ref.target, '../register/lassberg-literature.xml#', '')})
    MERGE (l)-[:MENTIONS]->(b)
)
RETURN l;
=======

RETURN l;

// Load in mentiones in letters
// Iterate through each letter
MATCH (l:Letter)
WITH l, 'https://raw.githubusercontent.com/michaelscho/lassberg/main/data/letters/' + l.id + '.xml' AS url

// Attempt to load the XML file
CALL apoc.load.xml(url, null, {failOnError: false}) 
YIELD value AS xmlFile
WITH l, url, xmlFile, xmlFile IS NOT NULL AS fileExists
SET l.processed = fileExists

// Proceed only if the XML file exists
WITH l, url, xmlFile
WHERE l.processed AND xmlFile IS NOT NULL
UNWIND xmlFile._children AS child
WITH l, child
WHERE child._type = "note" AND child.type = "mentioned"
UNWIND child._children AS ref
WITH l, ref
WHERE ref._type IN ["cmif:mentionsPerson", "cmif:mentionsPlace", "cmif:mentionsBibl"]

// Create or find the mentioned nodes and link them to the letter
FOREACH (item IN CASE WHEN ref._type = "cmif:mentionsPerson" THEN [1] ELSE [] END |
    MERGE (p:Person {id: apoc.text.replace(ref.target, '../register/lassberg-persons.xml#', '')})
    MERGE (l)-[:MENTIONS]->(p)
)
FOREACH (item IN CASE WHEN ref._type = "cmif:mentionsPlace" THEN [1] ELSE [] END |
    MERGE (place:Place {id: apoc.text.replace(ref.target, '../register/lassberg-places.xml#', '')})
    MERGE (l)-[:MENTIONS]->(place)
)
FOREACH (item IN CASE WHEN ref._type = "cmif:mentionsBibl" THEN [1] ELSE [] END |
    MERGE (b:Bibl {id: apoc.text.replace(ref.target, '../register/lassberg-literature.xml#', '')})
    MERGE (l)-[:MENTIONS]->(b)
)
RETURN l;

>>>>>>> b0b5098e8503640eb7d6ef5749b7b9a45c69bd1a
