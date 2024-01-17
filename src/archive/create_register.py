# Script for creating xml files of letters as indicated in register of letters
import os
import pandas as pd
from datetime import datetime
import openai
import config
import requests
import json
from dateutil.parser import parse

openai.api_key = config.openai_key

# import register as pandas df
data = pd.read_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'register.csv'), sep=';')

# get an overview on data
print(data.head)

""" Persons
"""


# create df of unique persons
unique_persons = data[['Name_voll','GND','Wiki']].copy()
unique_persons.drop_duplicates(subset=None, keep="first", inplace=True)

# add row with Lassberg to unique_persons'
unique_persons = unique_persons.append({'Name_voll': 'Joseph von Laßberg', 'GND': '118778862', 'Wiki': 'https://de.wikipedia.org/wiki/Joseph_von_La%C3%9Fberg'}, ignore_index=True)
unique_persons = unique_persons.reset_index(drop=True)

# query lobid api http://lobid.org/gnd/{GND}.json and safe data as gnd_number.json

def get_data_from_gnd(row):
    name = row['Name_voll'] 
    gnd = row['GND']
    if gnd == "-":
        print(f"Keine GND: {name}")
    else:
        api_request = requests.get(f"http://lobid.org/gnd/{gnd}.json")
        if api_request.status_code == 404:
            print(f"FEHLER: {api_request} == {gnd} == {name}")
            
        else:
            json_data = api_request.json()
            gnd_name = json_data["preferredName"]
            # check if correct data is downloaded
            print(f"GND: {gnd_name} == {name}")
            with open(os.path.join(os.getcwd(), '..', 'data', 'gnd', f'{gnd}.json'), 'w', encoding='utf8') as json_file:
                json.dump(json_data, json_file)

# query data (comment out once saved)
#unique_persons.apply(get_data_from_gnd, axis=1)

# enrich dataframe of unique persons

# add unique ids to dataframe
unique_persons['person_id'] = unique_persons.apply(lambda row: 'lassberg-correspondent-' + str(row.name+1).zfill(4), axis=1)

# query json file for preferredName if exists
def query_name_gnd(row):
    gnd = row['GND']
    gnd = gnd.strip()
    if gnd != '-':
        with open(os.path.join(os.getcwd(), '..', 'data', 'gnd', f'{gnd}.json'), 'r', encoding='utf8') as json_file:
            gnd_json = json.load(json_file)
            return gnd_json['preferredName']
    else:
        return '-'
            
unique_persons = unique_persons.assign(name_gnd=unique_persons.apply(query_name_gnd, axis=1))

# query json file for gender if exists
def query_gender_gnd(row):
    gnd = row['GND']
    gnd = gnd.strip()
    if gnd != '-':
        with open(os.path.join(os.getcwd(), '..', 'data', 'gnd', f'{gnd}.json'), 'r', encoding='utf8') as json_file:
            gnd_json = json.load(json_file)
            type = gnd_json['type']
            for i in type:
                if 'Person' in i:
                    gender = gnd_json['gender'][0]['id']
                    print(gender)
                    gender = gender.replace('https://d-nb.info/standards/vocab/gnd/gender#','')
                    return gender
                else:
                    gender = 'CorporateBody' 
            return gender
    else:
        return '-'
            
unique_persons = unique_persons.assign(gender_gnd=unique_persons.apply(query_gender_gnd, axis=1))

# query json file for birthdate if exists
def query_birth_gnd(row):
    gnd = row['GND']
    gnd = gnd.strip()
    if gnd != '-':
        with open(os.path.join(os.getcwd(), '..', 'data', 'gnd', f'{gnd}.json'), 'r', encoding='utf8') as json_file:
            gnd_json = json.load(json_file)
            type = gnd_json['type']
            for i in type:
                if 'Person' in i:
                    try:
                        birthdate = gnd_json['dateOfBirth'][0]                 
                        birthdate = parse(birthdate, fuzzy=True).year
                        print(birthdate)
                        return birthdate
                    except:
                        birthdate = '-'
                else:
                    birthdate = '-'
            
            return birthdate
    else:
        return '-'
            
unique_persons = unique_persons.assign(birth_gnd=unique_persons.apply(query_birth_gnd, axis=1))

# query json file for occupations if exists
def query_occupations_gnd(row):
    gnd = row['GND']
    gnd = gnd.strip()
    if gnd != '-':
        with open(os.path.join(os.getcwd(), '..', 'data', 'gnd', f'{gnd}.json'), 'r', encoding='utf8') as json_file:
            gnd_json = json.load(json_file)
            type = gnd_json['type']
            for i in type:
                if 'Person' in i:
                    try:
                        occupations = gnd_json['professionOrOccupation']
                        occupations_list = ""
                        for item in occupations:
                            occupation = item['label']
                            occupations_list = occupations_list + "," + occupation
                        occupations_list = occupations_list[1:]         
                        print(occupations_list)
                        return occupations_list
                    except:
                        occupations_list = '-'
                else:
                    occupations_list = '-'
            
            return occupations_list
    else:
        return '-'
            
unique_persons = unique_persons.assign(occupations_gnd=unique_persons.apply(query_occupations_gnd, axis=1))

# query json file for number of publications if exist
def query_publications_gnd(row):
    gnd = row['GND']
    gnd = gnd.strip()
    if gnd != '-':
        with open(os.path.join(os.getcwd(), '..', 'data', 'gnd', f'{gnd}.json'), 'r', encoding='utf8') as json_file:
            gnd_json = json.load(json_file)
            type = gnd_json['type']
            for i in type:
                if 'Person' in i:
                    try:
                        publications = gnd_json['publication']
                        publications_number = len(publications)         
                        print(publications_number)
                        return publications_number
                    except:
                        publications_number = '-'
                else:
                    publications_number = '-'
            
            return publications_number
    else:
        return '-'
            
unique_persons = unique_persons.assign(publications_gnd=unique_persons.apply(query_publications_gnd, axis=1))
print(unique_persons)

# query json file for academic degrees if exist
def query_degrees_gnd(row):
    gnd = row['GND']
    gnd = gnd.strip()
    if gnd != '-':
        with open(os.path.join(os.getcwd(), '..', 'data', 'gnd', f'{gnd}.json'), 'r', encoding='utf8') as json_file:
            gnd_json = json.load(json_file)
            type = gnd_json['type']
            for i in type:
                if 'Person' in i:
                    try:
                        degrees = gnd_json['academicDegree']
                        degrees_list = ""
                        for i in degrees:
                            degrees_list = degrees_list + ',' + i
                        degrees_list = degrees_list[1:] 
                        return degrees_list
                    except:
                        degrees_list = '-'
                else:
                    degrees_list = '-'
            
            return degrees_list
    else:
        return '-'
            
unique_persons = unique_persons.assign(degrees_gnd=unique_persons.apply(query_degrees_gnd, axis=1))
print(unique_persons)

# gut duplettes in unique_persons['Name_voll']
print(unique_persons[unique_persons['Name_voll'].duplicated(keep=False)])

# save unique persons to csv as ; separated file
#unique_persons.to_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'unique_persons.csv'), sep=';', index=False, encoding='utf8')

# Create tei xml encoded list of persons




base_xml_persons = []

# for each row in unique_persons, create variables to be inserted into the snippet
def get_variables_for_snippet(row):
    xml_id = row['person_id']
    name = row['Name_voll']
    gender = row['gender_gnd']
    gnd = row['GND']
    occupations = row['occupations_gnd'].split(',')
    occupation_xml = ""
    for occupation in occupations:
        occupation = occupation.strip()
        occupation_xml = occupation_xml +'\n'+ f'<occupation>{occupation}</occupation>'
    birth = row['birth_gnd']
    education_xml = ""
    educations = row['degrees_gnd'].split(',')
    for education in educations:
        education = education.strip()
        education_xml = education_xml +'\n'+ f'<education>{education}</education>'
    wiki = row['Wiki']
    person = f"""
                <person xml:id="{xml_id}" gender="{gender}" ref="{gnd}">
                    <persName type="main">{name}</persName>
                    <occupation>{occupation}</occupation>
                    <birth when="{birth}">{birth}</birth>
                    <education>{education}</education>
                    <ref>{wiki}</ref>
                </person>\n
                """
    base_xml_persons.append(person)
    
unique_persons.apply(get_variables_for_snippet, axis=1)
persons = '\n'.join(base_xml_persons)
xml_persons = f"""
<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="lassberg-register-persons">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title>Persons and institutions</title>
            </titleStmt>
            <publicationStmt>
                <p>In preparation.</p>
            </publicationStmt>
            <sourceDesc>
                <p>Born digital. Persons retrived from <bibl>Harris, Martin: Joseph Maria Christoph 
                    Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. 
                    Mit einer Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. 
                    Die erste geschlossene, wissenschaftlich fundierte Würdigung von Lassbergs Wirken und Werk. 
                    Beihefte zum Euphorion Heft 25/C. Heidelberg 1991.</bibl>. Enriched using GND and other sources by Michael Schonhardt
                </p>
            </sourceDesc>
        </fileDesc>
    </teiHeader>
    <text>
        <body>
            <div>
                <listPerson>
                    {persons}
                </listPerson>
            </div>
        </body>
    </text>
</TEI>

"""

# save xml to file
with open(os.path.join(os.getcwd(), '..', 'data', 'register', 'lassberg-persons.xml'), 'w', encoding='utf8') as xml_file:
    xml_file.write(xml_persons)





""" Places
"""

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

# split coordinates in unique_places into long and lat columns at ','
unique_places[['lat', 'long']] = unique_places.coordinates_wiki.str.split(",",expand=True,)
print(unique_places)

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
                <place xml:id="{id}">
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
    xml_file.write(xml_persons)



# merge data with unique_persons on column 'Name_voll'
data = pd.merge(data, unique_persons, on='Name_voll', how='left')
print(data)

# merge data with unique_places on column 'Ort' and print
data = pd.merge(data, unique_places, on='Ort', how='left')
print(data)

# save data to csv as ; separated file in utf8 encoding
data.to_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'enriched_register.csv'), sep=';', index=False, encoding='utf8')
