import os
import lxml.etree as LET

xml_file = os.path.join(os.getcwd(), 'output', 'lassberg-letter-1935.xml')
tree = LET.parse(xml_file)
root = tree.getroot()
print(root)