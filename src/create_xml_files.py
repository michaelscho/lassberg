import os
import pandas as pd
from datetime import datetime
import calendar

""" Create letters as xml files
"""
debug = []
e = ""

data = pd.read_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'final_register.csv'), sep=';')


# Create xml file for each letter

def create_letter(row):

    register_harris = row['Nummer']
    register_lassberg = row['Journalnummer']
    date = row['Datum']
    place_from_id = row['place_id']
    place_from = row['Ort']
    journal = row['Journalnummer']
    place_bib = row['Aufbewahrungsort']
    name_bib = row['Aufbewahrungsinstitution']
    print = row['text']
    scan_print = row['url']
    year = row['Jahr']
    from_to = row['VON/AN']
    #text = row['text']
    #summary = row['chatgpt-summary']
    try:
        if year == '-':
            date_format = 'unknown'
            date_print = 'unbekanntes Datum'
        elif date == '-' and year != '-':
            date_format = datetime.strptime(year, '%Y').strftime('%Y')
            date_print = year
        elif date == '-' and year == '-':
            date_format = 'unknown'
            date_print = 'unbekanntes Datum'
        elif date.count('.') == 1:
            date_format =  datetime.strptime(date + year, '%m.%Y').strftime('%Y-%m')
            date_print = calendar.month_name[int(date.replace('.',''))] + ' ' + year
        else:
            date_format = datetime.strptime(date + year, '%d.%m.%Y').strftime('%Y-%m-%d')
            date_print = date + year
    except Exception as i:
        e = i
        date_format = 'error'
        date_print = 'error'
        debug.append([date,year,register_harris])
        
    if from_to == 'VON':
        name_to = row['Name_voll']
        gnd_to = row['GND']
        name_from = 'Joseph von Laßberg'
        gnd_from = '118778862'
        person_id_from = 'lassberg-correspondent-0373'
        person_id_to = row['person_id']
    else:
        name_from = row['Name_voll']
        gnd_from = row['GND']
        name_to = 'Joseph von Laßberg'
        gnd_to = '118778862'
        person_id_to = 'lassberg-correspondent-0373'
        person_id_from = row['person_id']


    xml_snippet = f"""<?xml version="1.0" encoding="utf-8"?>
<?xml-model href="http://www.tei-c.org/release/xml/tei/custom/schema/relaxng/tei_all.rng" type="application/xml" schematypens="http://relaxng.org/ns/structure/1.0"?>
<TEI xmlns="http://www.tei-c.org/ns/1.0" xml:id="lassberg-letter-{str(register_harris)}">
    <teiHeader>
        <fileDesc>
            <titleStmt>
                <title>Brief von {name_from} an {name_to} ({date_print}).</title>
                <respStmt>
                    <resp>Encoding to TEI</resp>
                    <name>Michael Schonhardt</name>
                </respStmt>
            </titleStmt>
            <publicationStmt>
                <p>Correspondence data based on <bibl>Harris, Martin: Joseph Maria Christoph Freiherr von Lassberg 1770-1855. Briefinventar und Prosopographie. Mit einer Abhandlung zu Lassbergs Entwicklung zum Altertumsforscher. Die erste geschlossene, wissenschaftlich fundierte Würdigung von Lassbergs Wirken und Werk. Beihefte zum Euphorion Heft 25/C. Heidelberg 1991.</bibl>.</p>
            </publicationStmt>
            <sourceDesc>
                <msDesc>
                    <msIdentifier>
                        <settlement>{place_bib}</settlement>
                        <repository>{name_bib}</repository>
                        <idno type="signature"/>
                        <idno type="register-harris">{register_harris}</idno>
                        <idno type="register-lassberg">{register_lassberg}</idno>
                    </msIdentifier>
                    <additional>
                        <surrogates>
                            <bibl type="printed">{print}
                            <ref>{scan_print}</ref>
                            </bibl>
                        </surrogates>
                    </additional>
                </msDesc>
            </sourceDesc>
        </fileDesc>
        <profileDesc>
            <correspDesc xml:id="correspDesc-{str(register_harris)}">
                <correspAction type="sent">
                    <persName ref="{person_id_from}">{name_from}</persName>
                    <placeName ref="{place_from_id}">{place_from}</placeName>
                    <date when="{date_format}">{date_print}</date>
                </correspAction>
                <correspAction type="received">
                    <persName ref="{person_id_to}">{name_to}</persName>
                </correspAction>
                <noteGrp type="chatgpt">
                    <note type="chatgpt-summary"/>
                    <note type="chatgpt-keytopics"/>
                    <note type="chatgpt-persons"/>
                    <note type="chatgpt-texts"/>
                    <note type="chatgpt-objects"/>
                    <note type="chatgpt-manuscripts"/>
                </noteGrp>
            </correspDesc>
        </profileDesc>
    </teiHeader>
    <text>
        <body>
            <p/>
        </body>
    </text>
</TEI>
    """

    filename = f"lassberg-letter-{register_harris}.xml"

    # save xml to file
    with open(os.path.join(os.getcwd(), '..', 'data', 'letters', filename), 'w', encoding='utf8') as xml_file:
        xml_file.write(xml_snippet)

# create letters
data.apply(create_letter, axis=1)
print(debug)
print(e)