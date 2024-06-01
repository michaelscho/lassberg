import os
import re


with open('46b_pdf.txt', 'r') as file:
    content = file.read()
    parts = content.split('*=*')
    for part in parts:
        digits = re.findall(r'\d+', part)[0]
        new_file_name = f'{digits}.txt'
        new_file_path = os.path.join(os.curdir, new_file_name)
        with open(new_file_path, 'w') as new_file:
            new_file.write(part.replace(digits + '\n', ''))