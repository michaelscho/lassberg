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
CREATE (b:Bibl {id: bibl.`xml:id`, type: bibl.type})
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

RETURN l;

// Define the list of letter IDs
WITH ["0952", "0966", "0971", "0993", "1015", "1039", "1044", "1051", "1077", "1131", "1132", "1137", "1138", "1141", "1146", "1151", "1153", "1154", "1157", "1159", "1164", "1165", "1166", "1167", "1170", "1171", "1175", "1186", "1204", "1222", "1247", "1260", "1301", "1323", "1370", "1400", "1408"] AS letterIDs

// Unwind the list to process each letter ID
UNWIND letterIDs AS letterID

// Match or create the letter node
MERGE (l:Letter {id: letterID})
WITH l, letterID

// Load the XML for the current letter
CALL apoc.load.xml('https://raw.githubusercontent.com/michaelscho/lassberg/main/data/letters/lassberg-letter-' + letterID + '.xml')
YIELD value 
UNWIND value._children AS child
WITH l,child
WHERE child._type = "teiHeader"
UNWIND child._children AS grandChild
WITH l,grandChild
WHERE grandChild._type = "revisionDesc"
UNWIND grandChild._children AS revDesc
WITH l,revDesc
WHERE revDesc._type = "listChange"
UNWIND revDesc._children AS listChange
WITH l,listChange
WHERE listChange._type = "profileDesc"
UNWIND listChange._children AS profileDesc
WITH l,profileDesc
WHERE profileDesc._type = "correspDesc"
UNWIND profileDesc._children AS correspDesc
WITH l,correspDesc
WHERE correspDesc._type = "note"
UNWIND correspDesc._children AS ref
WITH l, ref

// Create or find the mentioned nodes and link them to the letter
FOREACH (item IN CASE WHEN ref.type = "cmif:mentionsPerson" THEN [1] ELSE [] END |
    MERGE (p:Person {id: apoc.text.replace(ref.target, '../register/lassberg-persons.xml#', '')})
    MERGE (l)-[:MENTIONS]->(p)
)
FOREACH (item IN CASE WHEN ref.type = "cmif:mentionsPlace" THEN [1] ELSE [] END |
    MERGE (place:Place {id: apoc.text.replace(ref.target, '../register/lassberg-places.xml#', '')})
    MERGE (l)-[:MENTIONS]->(place)
)
FOREACH (item IN CASE WHEN ref.type = "cmif:mentionsBibl" THEN [1] ELSE [] END |
    MERGE (b:Bibl {id: apoc.text.replace(ref.target, '../register/lassberg-literature.xml#', '')})
    MERGE (l)-[:MENTIONS]->(b)
)
RETURN l;

// Create letters
// Define the list of letter IDs
WITH ["0952", "0966", "0971", "0993", "1015", "1039", "1044", "1051", "1077", "1131", "1132", "1137", "1138", "1141", "1146", "1151", "1153", "1154", "1157", "1159", "1164", "1165", "1166", "1167", "1170", "1171", "1175", "1186", "1204", "1222", "1247", "1260", "1301", "1323", "1370", "1400", "1408"] AS letterIDs

// Unwind the list to process each letter ID
UNWIND letterIDs AS letterID

// Match or create the letter node
MERGE (l:Letter {id: letterID})
WITH l, letterID

// Load the XML for the current letter
CALL apoc.load.xml('https://raw.githubusercontent.com/michaelscho/lassberg/main/data/letters/lassberg-letter-' + letterID + '.xml')

YIELD value 
UNWIND value._children AS child
WITH l,child
WHERE child._type = "teiHeader"
UNWIND child._children AS grandChild
WITH l,grandChild
WHERE grandChild._type = "profileDesc"
UNWIND grandChild._children AS profileDesc
WITH l,profileDesc
WHERE profileDesc._type = "correspDesc"
UNWIND profileDesc._children AS correspDesc
WITH l,correspDesc
WHERE correspDesc._type = "note"
UNWIND correspDesc._children AS ref
WITH l, ref

// Create or find the mentioned nodes and link them to the letter
FOREACH (item IN CASE WHEN ref.type = "cmif:mentionsPerson" THEN [1] ELSE [] END |
    MERGE (p:Person {id: apoc.text.replace(ref.target, '../register/lassberg-persons.xml#', '')})
    MERGE (l)-[:MENTIONS]->(p)
)
FOREACH (item IN CASE WHEN ref.type = "cmif:mentionsPlace" THEN [1] ELSE [] END |
    MERGE (place:Place {id: apoc.text.replace(ref.target, '../register/lassberg-places.xml#', '')})
    MERGE (l)-[:MENTIONS]->(place)
)
FOREACH (item IN CASE WHEN ref.type = "cmif:mentionsBibl" THEN [1] ELSE [] END |
    MERGE (b:Bibl {id: apoc.text.replace(ref.target, '../register/lassberg-literature.xml#', '')})
    MERGE (l)-[:MENTIONS]->(b)
)
RETURN l;