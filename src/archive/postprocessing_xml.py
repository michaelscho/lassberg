from lxml import etree
import os
import re

def apply_template(element):
    """ Takes reutrn from chatgpt stored in noteGrp as text and adds it to list as child of noteGrp
    """        
    xml_snippet = root.find(f'.//tei:note[@type="chatgpt-{element}"]', namespaces={'tei': 'http://www.tei-c.org/ns/1.0'})
    xml_id_root = root.xpath("//tei:TEI/@xml:id", namespaces={"tei":"http://www.tei-c.org/ns/1.0"})[0]        
    xml_snippet_text = xml_snippet.text
    if xml_snippet_text is not None:
        list_xml = etree.SubElement(xml_snippet, "{http://www.tei-c.org/ns/1.0}list")
        xml_snippet_list = xml_snippet_text.split('\n')
        xml_snippet.text = None
        n = 1
        for i in xml_snippet_list:
            
            i = i.strip()
            i = i.replace('- ','')
            i = re.sub('^\d+. ', '', i)
            if i != '':
                item_id = xml_id_root + '-' + element + '-' + str(n).zfill(3)
                item_xml = etree.SubElement(list_xml, "{http://www.tei-c.org/ns/1.0}item")
                item_xml.text = i
                n += 1
                item_xml.attrib["{http://www.w3.org/XML/1998/namespace}id"] = item_id
                print(item_id)
        return True
    



# open each file in A folder and read content as xml
for filename in os.listdir(os.path.join(os.getcwd(),'..','data','letters')):
    applied = False
    # read content as xml
    with open(os.path.join(os.getcwd(),'..','data','letters',filename), 'r', encoding='utf-8') as file:
        #print(filename)
        tree = etree.parse(file)
        root = tree.getroot()
        apply_template('keytopics')
        apply_template('persons')
        applied = apply_template('objects')
    filename_new = filename.replace('.xml','_new.xml')
    if applied == True:
        tree.write(f'{filename_new}', encoding='utf-8', pretty_print=True)

            


