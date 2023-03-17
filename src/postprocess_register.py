import pandas as pd
import os
import requests


data = pd.read_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'enriched_register_new.csv'), sep=';')
print(data)

# create df of unique places
unique_places = data[['Ort']].copy()
unique_places.drop_duplicates(subset=None, keep="first", inplace=True)
unique_places = unique_places.reset_index(drop=True)

# get coordinates of places
def get_coordinates(row):
    try:
        S = requests.Session()
        URL = "https://en.wikipedia.org/w/api.php"
        PARAMS = {
            "action": "query",
            "format": "json",
            "titles": f"{row['Ort']}",
            "prop": "coordinates"
        }

        R = S.get(url=URL, params=PARAMS)
        DATA = R.json()
        PAGES = DATA['query']['pages']

        for k, v in PAGES.items():
            print("Latitute: " + str(v['coordinates'][0]['lat']))
            print("Longitude: " + str(v['coordinates'][0]['lon']))
            coordinates = str(v['coordinates'][0]['lat']) + ',' + str(v['coordinates'][0]['lon'])
            return coordinates
    except:
        coordinates = '-'
        return coordinates

unique_places = unique_places.assign(coordinates_wiki=unique_places.apply(get_coordinates, axis=1))

# apply ids to each place using the pattern 'lassberg-places-0001'
unique_places['place_id'] = unique_places.apply(lambda row: 'lassberg-place-' + str(row.name+1).zfill(4), axis=1)
# save unique_places to csv as ; separated file in utf8 encoding
unique_places.to_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'unique_places.csv'), sep=';', index=False, encoding='utf8')

# create tei xml encoded list of places

base_xml_places = []
# for each row in unique_persons, create variables to be inserted into the snippet
def get_variables_for_snippet_places(row):
    xml_id = row['place_id']
    name = row['Ort']
    coordinates = row['coordinates_wiki']

    place = f"""
                <place xml:id="{xml_id}">
                    <placeName>{name}</placeName>
                    <location>
                        <geo ana="wgs84">{coordinates}</geo>
                    </location>
                </place>
                """

    base_xml_places.append(place)
    
unique_places.apply(get_variables_for_snippet_places, axis=1)
places = '\n'.join(base_xml_places)

places_xml_snippet = f"""
<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="lassberg-place">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title>Places</title>
                <respStmt>
                    <name xml:id="MiS">Michael Schonhardt</name>
                    <resp>Konzeption, Datenmodel und Codierung nach TEI</resp>
                </respStmt>
            </titleStmt>
            <publicationStmt>
                <p>Working files.</p>
            </publicationStmt>
            <sourceDesc>
                <p>Born digital.</p>
            </sourceDesc>
        </fileDesc>
    </teiHeader>
    <text>
        <body>
            <listPlace>
                {places}
            </listPlace>
        </body>
    </text>
</TEI>
"""

# save xml to file
with open(os.path.join(os.getcwd(), '..', 'data', 'register', 'lassberg-places.xml'), 'w', encoding='utf8') as xml_file:
    xml_file.write(places_xml_snippet)


print(unique_places)

# join data with unique_places to get place_id
data = data.merge(unique_places, on='Ort', how='left')
print(data)

# save data to csv with ';' as separator
data.to_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'enriched_register_new_new.csv'), sep=';', index=False)





