import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

def create_letter_archive(xml_path: str, txt_path: str, output_zip: str, log_path: str):
    """
    Parst TEI-XML und Rohtext, ordnet Briefe basierend auf dem Datum zu,
    verpackt sie in ein ZIP-Archiv und schreibt ungematchte Briefe in ein Log.
    Die Originalinhalte der Briefe werden dabei strikt nicht verändert.
    """
    
    # 1. TEI-XML Register parsen
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Fehler beim Parsen der XML-Datei: {e}")
        return

    ns = {'tei': 'http://www.tei-c.org/ns/1.0'}
    
    # Mapping: Datum (YYYY-MM-DD) -> Liste von Brief-IDs
    date_to_ids = {}
    for corresp in root.findall('.//tei:correspDesc', ns):
        key = corresp.get('key')
        date_elem = corresp.find('.//tei:correspAction/tei:date', ns)
        if date_elem is not None and date_elem.get('when'):
            date_val = date_elem.get('when')
            if date_val not in date_to_ids:
                date_to_ids[date_val] = []
            date_to_ids[date_val].append(key)
            
    # 2. Rohtext der Briefe einlesen
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Briefe am Header (## Brief) splitten. re.DOTALL erfasst den gesamten Text bis zum nächsten Brief.
    letter_blocks = re.findall(r'(## Brief.*?(?=\n## Brief|\Z))', content, re.DOTALL)
    
    # Historisches und modernes Monats-Mapping für die Datums-Extraktion
    months = {
        'januar': '01', 'jenner': '01', 'jan': '01',
        'februar': '02', 'hornung': '02', 'febr': '02', 'feb': '02',
        'märz': '03', 'mart': '03', 'maerz': '03',
        'april': '04',
        'mai': '05', 'mey': '05',
        'juni': '06', 'junij': '06', 'jun': '06',
        'juli': '07', 'julij': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'septber': '09', 'sept': '09',
        'oktober': '10', 'october': '10', 'oct': '10', 'weinmonat': '10',
        'november': '11', 'novbr': '11', 'nov': '11',
        'dezember': '12', 'december': '12', 'dez': '12', 'dec': '12', 'christmonat': '12'
    }
    
    # Regex für die Datumsfindung (z.B. "3. Dezember 1825" oder "22. Hornung 1830")
    date_pattern = re.compile(r'(\d{1,2})\.\s*([A-Za-zäöüÄÖÜ]+)\s*(\d{4})')
    
    unmatched = []
    
    # 3. Briefe evaluieren und verpacken
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for block in letter_blocks:
            # Suche nach dem Datum in den ersten Zeilen (Header des Briefs)
            header_match = date_pattern.search(block[:300])
            assigned_id = None
            
            if header_match:
                day = header_match.group(1).zfill(2)
                month_str = header_match.group(2).lower()
                year = header_match.group(3)
                
                month = months.get(month_str)
                if month:
                    iso_date = f"{year}-{month}-{day}"
                    
                    # Abgleich mit TEI Register
                    if iso_date in date_to_ids and date_to_ids[iso_date]:
                        assigned_id = date_to_ids[iso_date].pop(0) 
            
            if assigned_id:
                # Brief in das ZIP unter seiner Brief_id ablegen
                zipf.writestr(f"{assigned_id}.txt", block.strip())
            else:
                unmatched.append(block)
                
    # 4. Fehlerprotokoll für nicht zuordenbare Briefe erstellen
    with open(log_path, 'w', encoding='utf-8') as logf:
        logf.write(f"Nicht zugeordnete Briefe: {len(unmatched)}\n")
        logf.write("="*40 + "\n\n")
        for u in unmatched:
            logf.write("--- UNMATCHED LETTER ---\n")
            logf.write(u.strip() + "\n\n")
            
    print(f"Verarbeitung abgeschlossen. Erfolgreich: {len(letter_blocks) - len(unmatched)}. Ungematcht: {len(unmatched)}.")

if __name__ == "__main__":
    # Vor der Ausführung Dateinamen entsprechend anpassen
    create_letter_archive(
        xml_path='/home/micha/github/lassberg/data/register/lassberg-letters.xml',
        txt_path='pupikofer_new.txt',
        output_zip='lassberg_einzelbriefe.zip',
        log_path='unmatched_letters.log'
    )