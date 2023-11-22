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
CALL apoc.load.xml('https://raw.githubusercontent.com/michaelscho/lassberg/main/data/register/lassberg-literature.xml', '//bibl') 
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

MERGE (b:Bibl {id: bibl.`xml:id`, type: bibl.`type`})
SET b.title = [x IN bibl._children WHERE x._type = "title" | x._text],
    b.date = [x IN bibl._children WHERE x._type = "date" | x._text],
    b.idno = [x IN bibl._children WHERE x._type = "idno" | x._text]
    
RETURN b.title, b.date, b.idno;  

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
