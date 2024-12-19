import pandas as pd
import lxml.etree as ET
from datetime import date
import re

# Load CSV data
file_path = 'register.csv'  
df = pd.read_csv(file_path, delimiter=';')
# nAn values are replaced with empty strings
df = df.fillna('')

ns_xml = "{http://www.w3.org/XML/1998/namespace}"
ns_tei = "{http://www.tei-c.org/ns/1.0}"

# load tei file lassberg-persons.xml
tree_person = ET.parse('lassberg-persons.xml')
root_person = tree_person.getroot()

# load tei file lassberg-places.xml
tree_place = ET.parse('lassberg-places.xml')
root_place = tree_place.getroot()

# Define namespaces and root element
tei_ns = "http://www.tei-c.org/ns/1.0"
root = ET.Element(f'TEI', {'xmlns': tei_ns, f'{ns_xml}id': 'lassberg-register-letters'})

# Create the teiHeader
teiHeader = ET.SubElement(root, 'teiHeader')
fileDesc = ET.SubElement(teiHeader, 'fileDesc')

# Add titleStmt
titleStmt = ET.SubElement(fileDesc, 'titleStmt')
title = ET.SubElement(titleStmt, 'title')
title.text = 'Laßberg Letters Register'
editor = ET.SubElement(titleStmt, 'editor')
editor.text = 'Michael Schonhardt'
email = ET.SubElement(editor, 'email')
email.text = 'michael.schonhardt@gmail.com'

# Add publicationStmt
publicationStmt = ET.SubElement(fileDesc, 'publicationStmt')
date_pub = ET.SubElement(publicationStmt, 'date', {'when': '2024-10-19'})

# Add availability and license
availability = ET.SubElement(publicationStmt, 'availability')
licence = ET.SubElement(availability, 'licence', {'target': 'http://creativecommons.org/licenses/by/4.0/'})
licence.text = 'This file is licensed under the terms of the Creative Commons Licence CC BY 4.0'

# Add sourceDesc
sourceDesc = ET.SubElement(fileDesc, 'sourceDesc')
bibl = ET.SubElement(sourceDesc, 'bibl', {'type': 'online'})
bibl.text = r"""Born digital. Digital register of the Laßberg correspondence (https://github.com/michaelscho/lassberg/). 
               Persons retrived from <bibl>Harris, Martin: Joseph Maria Christoph
               Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. Mit einer
               Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. Die erste
               geschlossene, wissenschaftlich fundierte Würdigung von Lassbergs Wirken und
               Werk. Beihefte zum Euphorion Heft 25/C. Heidelberg 1991.</bibl>. Enriched using
               GND and other sources by Michael Schonhardt"""

# Add profileDesc and correspDesc elements for each letter
profileDesc = ET.SubElement(teiHeader, 'profileDesc')

# Iterate through each row of the CSV to create correspDesc entries
for index, row in df.iterrows():
    # Unique key for each correspondence
    correspDesc = ET.SubElement(profileDesc, 'correspDesc', {
        'key': row['ID'],
        'ref': "https://github.com/michaelscho/lassberg/tree/main/data/letters/" + row['ID'] + ".xml",
        'change': 'in_register' # 'scan_ordered', 'in_transcribus_waiting', 'in_transcribus_done', 'in_oxygen_waiting', 'in_oxygen_done', 'online' 
    })

    # Sent action
    correspAction_sent = ET.SubElement(correspDesc, 'correspAction', {'type': 'sent'})

    person = root_person.find(f".//{ns_tei}person[@{ns_xml}id='{row['SENT_FROM_ID']}']")
    if person:
        ref_person = person.get('ref')
        wiki_person = person.find(f"./{ns_tei}ref").text

        if ref_person is None:
            ref_person = ''
            wiki_person = ''
    else:
        ref_person = ''
        wiki_person = ''

    persName_sent = ET.SubElement(correspAction_sent, 'persName', {
        'key': row['SENT_FROM_ID'],
        # get gnd number from lassberg-person using id
        'ref': ref_person,
        'ana': str(wiki_person)
    })
    persName_sent.text = row['SENT_FROM_NAME']
    persName_sent.text = re.sub("([a-z])([A-Z])", "$1 $2", persName_sent.text)
    if persName_sent.text.endswith('-'):
        persName_sent.text = persName_sent.text[:-1]
    
    place = root_place.find(f".//{ns_tei}place[@{ns_xml}id='{row['Absendeort_id']}']")
    if place:
        ref_place = place.find(f"{ns_tei}placeName").get('ref')
        if ref_place is None:
            ref_place = ''
        print(ref_place)
        ana_place = place.find(f"{ns_tei}location/{ns_tei}geo").text
        if ana_place is None:
            ana_place = ''
        elif ana_place == '-':
            ana_place = ''
        print(ana_place)
    else:
        ref_place = ''
        ana_place = ''

    placeName_sent = ET.SubElement(correspAction_sent, 'placeName',
        {'key': row['Absendeort_id'],
        # get wikidata url from lassberg-places using id
        'ref': ref_place,
        # get coordinates from lassberg-places using id
        'ana': ana_place,
        })
    
    placeName_sent.text = row['Absendeort']
    
    # Add date if available
    if 'Datum' in row and pd.notnull(row['Datum']):
        date_sent = ET.SubElement(correspAction_sent, 'date', {'when': row['Datum']})
        # convert iso into human readable format
        try:
            date_sent.text = date.fromisoformat(row['Datum']).strftime('%Y-%m-%d')
        except ValueError:
            date_sent.text = row['Datum']

    # Received action
    correspAction_received = ET.SubElement(correspDesc, 'correspAction', {'type': 'received'})
    
    person_re = root_person.find(f".//{ns_tei}person[@{ns_xml}id='{row['RECIVED_BY_ID']}']")
    if person_re:
        wiki_person_re = person_re.find(f"./{ns_tei}ref").text
        ref_person_re = person_re.get('ref')
        if ref_person_re is None:
            ref_perso_re = ''
            wiki_person_re = ''

    else:
        ref_person_re = ''
        wiki_person_re = ''
    
    persName_received = ET.SubElement(correspAction_received, 'persName', 
        {'key': row['RECIVED_BY_ID'],
        'ref': ref_person_re,
        'ana': str(wiki_person_re)
        })
    
    persName_received.text = row['RECIVED_BY_NAME']
    persName_received.text = re.sub("([a-z])([A-Z])", "$1 $2", persName_received.text)
    if persName_received.text.endswith('-'):
        persName_received.text = persName_received.text[:-1]

    # add Nummer_Harris;Journalnummer;Aufbewahrungsort;Aufbewahrungsinstitution;Signatur;url_facsimile;published_in;published_in_url; as note
    notes = ['Nummer_Harris', 'Journalnummer', 'Aufbewahrungsort', 'Aufbewahrungsinstitution', 'Signatur', 'url_facsimile', 'published_in']
    for item in notes:
        note = ET.SubElement(correspDesc, 'note', {
            'type': item.lower().replace(' ', '_')
        })
        note.text = str(row[item])
        if item == 'published_in' and row['published_in_url'] != '':
            note.set('target', row['published_in_url'])
        elif item == 'url_facsimile' and row['url_facsimile'] != '':
            note.set('target', row[item])
        
pi = ET.ProcessingInstruction("xml-stylesheet", text='type="text/css" href="../../oxygen-framework/lassberg/css/reg-letters.css"')
root.addprevious(pi)
    
# Create the final XML tree
tree = ET.ElementTree(root)

# Save the XML to a file
print("Save file")
output_path = 'lassberg-letters.xml'  # Specify the desired output path

tree.write(output_path, encoding='UTF-8', xml_declaration=True, pretty_print=True)

print(f"CMIF TEI XML file saved to {output_path}")
