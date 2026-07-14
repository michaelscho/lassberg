"""
Briefwechsel Laßberg-Uhland Postprozessor & ID-Matcher

Dieses Skript verarbeitet das extrahierte rohe Text-Korpus, bereinigt es
(Auflösung von Paginierung, Fußnoten, Zeilenumbrüchen) und gleicht die 
Briefe mit dem Laßberg-Register (XML) ab, um sie unter der korrekten 
`lassberg-letter-XXXX`-ID abzuspeichern.
"""

import re
import os
import xml.etree.ElementTree as ET

def load_register(xml_file_path):
    """Lädt das TEI-XML-Register und extrahiert Metadaten."""
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    namespace = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    register = []
    for corresp_desc in root.findall('.//tei:correspDesc', namespace):
        letter_id = corresp_desc.get('key')
        
        sent_action = corresp_desc.find('./tei:correspAction[@type="sent"]', namespace)
        sender = ""
        date = ""
        if sent_action is not None:
            sender_node = sent_action.find('./tei:persName', namespace)
            if sender_node is not None and sender_node.text:
                sender = sender_node.text
            date_node = sent_action.find('./tei:date', namespace)
            if date_node is not None and date_node.get('when'):
                date = date_node.get('when')
                
        received_action = corresp_desc.find('./tei:correspAction[@type="received"]', namespace)
        receiver = ""
        if received_action is not None:
            receiver_node = received_action.find('./tei:persName', namespace)
            if receiver_node is not None and receiver_node.text:
                receiver = receiver_node.text
                
        register.append({
            'id': letter_id,
            'sender': sender,
            'receiver': receiver,
            'date': date
        })
    return register

def clean_and_split_corpus(raw_text):
    """Filtert Fußnoten, Bogensignaturen und teilt den Text in Einzelbriefe."""
    pages = re.split(r'--- \d+ \(\d+\) ---', raw_text)
    cleaned_pages = []
    
    for page in pages:
        lines = page.split('\n')
        valid_lines = []
        for line in lines:
            line_stripped = line.strip()
            # Seitenzahlen und Datums-Kopfzeilen filtern
            if line_stripped.isdigit() or re.match(r'^\d+\.\s+[a-zA-ZäöüÄÖÜ]+\s+\d{4}\s*\.?$', line_stripped):
                continue
            # Fußnoten am Seitenende abtrennen
            if line_stripped.startswith('* )') or line_stripped.startswith('** )'):
                break
            # Isolierte Bogensignaturen ignorieren
            if line_stripped in ['*', '1 *', '2 *', '3 *', '4 *', '5 *', '6 *', '7 *']:
                continue
            valid_lines.append(line.replace('|', '').strip())
        cleaned_pages.append('\n'.join(valid_lines))
        
    full_text = '\n'.join(cleaned_pages)
    # Splitten an Mustern wie "1 .\n" oder "2 .\n"
    return re.split(r'\n(?=\d+\s*\.\n)', '\n' + full_text)

def map_month_german_to_num(month_str):
    """Mappt auch historische Monatsbezeichnungen auf ISO-Zahlen."""
    mapping = {
        'januar': '01', 'jener': '01', 'horn': '02', 'hornung': '02', 'hornungs': '02',
        'märz': '03', 'mrz': '03', 'april': '04', 'mai': '05', 'may': '05',
        'juni': '06', 'juny': '06', 'jun': '06', 'juli': '07', 'july': '07', 'jul': '07',
        'august': '08', 'aug': '08', 'september': '09', 'sept': '09', 'weinmond': '10', 'october': '10', 'oktober': '10', 'oct': '10',
        'november': '11', 'nov': '11', 'december': '12', 'dec': '12', 'christmond': '12', 'xber': '12', 'xbers': '12'
    }
    for k, v in mapping.items():
        if k in month_str.lower():
            return v
    return None

def extract_date_from_text(text):
    """Sucht nach Datumsangaben im Text für das Matching."""
    # Vollständiges Datum: "16. Hornungs 1821"
    matches = re.finditer(r'(\d{1,2})\.?\s+([a-zA-ZäöüÄÖÜ]+)\s+(\d{4})', text)
    for match in matches:
        day = match.group(1).zfill(2)
        month_str = match.group(2)
        year = match.group(3)
        month = map_month_german_to_num(month_str)
        if month:
            return f"{year}-{month}-{day}"
            
    # Partielles Datum: "Hornung 1821"
    matches = re.finditer(r'([a-zA-ZäöüÄÖÜ]+)\s+(\d{4})', text)
    for match in matches:
        month_str = match.group(1)
        year = match.group(2)
        month = map_month_german_to_num(month_str)
        if month:
            return f"{year}-{month}-" 
            
    return None

def process_and_match(input_file, register_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    register = load_register(register_file)
    print(f"TEI-Register geladen. {len(register)} Einträge gefunden.")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_text = f.read()
        
    letters = clean_and_split_corpus(raw_text)
    
    export_count = 0
    matched_count = 0
    
    for letter in letters:
        letter = letter.strip()
        if not letter:
            continue
            
        match = re.match(r'^(\d+)\s*\.', letter)
        if not match:
            continue
            
        letter_num = match.group(1).zfill(3)
        
        # Fließtext rekonstruieren (De-Hyphenation)
        paragraphs = re.split(r'\n\s*\n', letter)
        formatted_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if not para: continue
            # Trennstriche am Zeilenende auflösen
            para = re.sub(r'([a-zA-ZäöüÄÖÜß])\s*[-=]\s*\n\s*', r'\1', para)
            # Übrige Zeilenumbrüche durch Leerzeichen ersetzen
            para = re.sub(r'\n\s*', ' ', para)
            formatted_paragraphs.append(para)
            
        final_text = '\n\n'.join(formatted_paragraphs)
        
        # Datum aus dem Kopf- oder Fußbereich extrahieren
        search_area = " ".join(formatted_paragraphs[:3]) + " " + " ".join(formatted_paragraphs[-3:])
        extracted_date = extract_date_from_text(search_area)
        
        # Fallback-ID, falls kein Match gefunden wird
        assigned_id = f"lassberg_uhland_unmatched_{letter_num}"
        
        if extracted_date:
            # Suche im TEI-Register nach diesem Datum
            potential_matches = [
                entry for entry in register 
                if entry['date'] and entry['date'].startswith(extracted_date)
            ]
            if potential_matches:
                assigned_id = potential_matches[0]['id']
                matched_count += 1
                
        out_path = os.path.join(output_dir, f'{assigned_id}.txt')
        with open(out_path, 'w', encoding='utf-8') as out_f:
            out_f.write(final_text)
        export_count += 1
        
    print(f"Verarbeitung abgeschlossen. {export_count} Briefe exportiert.")
    print(f"Davon erfolgreich mit dem TEI-Register verknüpft: {matched_count}.")

if __name__ == '__main__':
    # Passen Sie diese Dateinamen ggf. an Ihre lokalen Dateien an
    TEXT_KORPUS = 'bsb10620870_fulltext.txt'
    XML_REGISTER = '../data/register/lassberg-letters.xml'
    OUTPUT_ORDNER = 'Exportierte_Briefe'
    
    process_and_match(TEXT_KORPUS, XML_REGISTER, OUTPUT_ORDNER)