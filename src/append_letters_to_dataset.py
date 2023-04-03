"""
This script automatically appends printed letters of the Laßberg correspondence.
If the letters are already printed, they are usually available on Googlebooks or similar service.
This, they are ocred and stored in a large textfile that can be included in the dataset automatically.
The files are checked manually and individual letters are seperated by the string '###'

Each letter typically ends with a dateline, such as '12. Dez. 1841', but other formats might be used as well.
To append the letters to a corresponding row in the register file, the script reads this date  
and appends them to the corresponding rows in a CSV file.

Usage:
1. Install the required Python packages: `pip install pandas`
2. Update the INPUT_TEXT_FILE, INPUT_CSV_FILE, and OUTPUT_CSV_FILE variables to match your file paths
3. Run the script: `python append_letters_to_dataset.py`

Author: Michael Schonhardt
Date: 01.04.2023
"""

import pandas as pd
import os
import re
import locale

# Update the following variables to match your file paths
INPUT_TEXT_FILE = os.path.join(os.getcwd(), '..', 'data', 'literature', 'lassberg_pupikofer_allemania_16.txt')
INPUT_CSV_FILE = os.path.join(os.getcwd(), '..', 'data', 'register', 'final_register.csv')
OUTPUT_CSV_FILE = os.path.join(os.getcwd(), '..', 'data', 'register', 'final_register_new.csv')
OUTPUT_LOG_FILE = os.path.join(os.getcwd(), '..', 'data', 'literature', 'lassberg_pupikofer_allemania_16_rest.txt')

# Empty list for logging letters without a proper dateline
letters_without_proper_dateline = []

# Read letters from the text file
def read_texts_from_file(INPUT_TEXT_FILE):
    """
    Reads individual letters from a text file separated by a specified delimiter.
    
    This function takes an input text file containing letters separated by a delimiter 
    (in this case, a single '#') and returns a list of cleaned letter texts. 
    It removes leading and trailing whitespaces from each text.

    Args:
        INPUT_TEXT_FILE (str): The path to the input text file containing the letters.

    Returns:
        list: A list of cleaned letter texts.

    Example:
        INPUT_TEXT_FILE = "path/to/your/letters.txt"
        letters = read_texts_from_file(INPUT_TEXT_FILE)
    """
    with open(INPUT_TEXT_FILE, "r", encoding="utf-8") as file:
        content = file.read()
        letters = content.split("#")
        # Remove leading and trailing whitespaces from each text
        letters = [letter.strip() for letter in letters if letter.strip()]
        print(letters)
    return letters


def extract_datelines(letters):
    """
    Extracts datelines from a list of letter texts.
    
    This function takes a list of letter texts and attempts to extract the datelines found at the end of each text. A dateline is expected to have the format 'DD. Month YYYY' (e.g., '12. Aug. 1834'), 'DD.MM.YYYY' (e.g., '12.08.1934'), 'DD. M. YYYY' (e.g., '12. 8. 1934'), or 'd-m-yyyy' (e.g., '8-12-1832'). If no dateline is found for a text or there is more than one match, the function appends None to the list of datelines and adds the letter to a list of letters without a proper dateline.

    Args:
        letters (list): A list of letter texts from which to extract the datelines.

    Returns:
        tuple: A tuple containing a list of extracted datelines and a list of letters without a proper dateline. If a dateline is not found for a text or there is more than one match, the corresponding entry in the output list is None.

    Example:
        letters = ["Letter text 1...", "Letter text 2..."]
        datelines, letters_without_proper_dateline = extract_datelines(letters)
    """
    datelines = []
    letters_without_proper_dateline = []
    for letter in letters:
        # Look for date patterns in the text
        matches = re.findall(r'(\d{1,2}(\.|-)?\s?(\w{1,3}|[\w\u00C0-\u017F]{3,})(\.|-)?\s?(1(7|8)\d{2}|\d{2}))', letter)
        
        if len(matches) == 1:
            datelines.append(matches[0][0])
        else:

            matches = re.findall(r'(\d{1,2}(\.|-)?\s?(\w{1,3}|[\w\u00C0-\u017F]{3,})(\.|-)?\s?(1(7|8)\d{2}))', letter)
            if len(matches) == 1:
                print(matches)
                datelines.append(matches[0][0])
            else:
                datelines.append(None)
                letters_without_proper_dateline.append(letter)
    return datelines, letters_without_proper_dateline


def match_texts_to_letters(df, datelines, letters, correspondent, to_from):
    """
    Matches the letters to the corresponding rows in the DataFrame and updates the 'letter_text' field.

    Args:
        df (pd.DataFrame): The DataFrame containing the metadata of the letters, with columns 'Datum', 'Jahr', 'letter_text', and 'status_letter_text'.
        datelines (list): The list of extracted datelines from the letters.
        letters (list): The list of letter texts.
    """
    for dateline, letter in zip(datelines, letters):
        if dateline:
            # clean up dateline:
            dateline = dateline.replace('Febr.','Feb.')
            dateline = dateline.replace('II','Feb.')
            dateline = dateline.replace('Mart.','Mar.')
            dateline = dateline.replace('Mär.','Mar.')
            dateline = dateline.replace('Dez.','Dec.')

            # relplace 2-digit years with 4-digit years using regex
            dateline = re.sub(r' (\d{2})$', r' 18\1', dateline)
            
            # Abbreviate all months to 3 letters
            dateline = dateline.replace('Junij','Jun.')
            dateline = dateline.replace('Julij','Jul.')
            dateline = dateline.replace('Januar','Jan.')
            dateline = dateline.replace('Februar','Feb.')
            dateline = dateline.replace('Hornung','Feb.')
            dateline = dateline.replace('März','Mar.')
            dateline = dateline.replace('April','Apr.')
            dateline = dateline.replace('april','Apr.')
            dateline = dateline.replace('Mai','May.')
            dateline = dateline.replace('Mey','May.')
            dateline = dateline.replace('May ','May. ')

            dateline = dateline.replace('Juni','Jun.')
            dateline = dateline.replace('Juny','Jun.')
            dateline = dateline.replace('Márz','Mar.')
            dateline = dateline.replace('márz','Mar.')

            dateline = dateline.replace('Juli','Jul.')
            dateline = dateline.replace('August','Aug.')
            dateline = dateline.replace('September','Sep.')
            dateline = dateline.replace('Septber','Sep.')
            dateline = dateline.replace('Septembr','Sep.')

            dateline = dateline.replace('Novbrs','Nov.')

            dateline = dateline.replace('Sept.','Sep.')
            dateline = dateline.replace('Oktober','Oct.')
            dateline = dateline.replace('November','Nov.')
            dateline = dateline.replace('Dezember','Dec.')
            dateline = dateline.replace('Jenner','Jan.')

            # Convert dateline to a date object
            dateline_date = pd.to_datetime(dateline, format='%d. %b. %Y', errors='coerce')
            print(f"The date of the letter is {dateline_date}, based on date string '{dateline}'")

            
            # Convert the datetime object to a string with the desired format
            # date_formatted = dateline_date.strftime('%Y-%m-%d')
            date_formatted = dateline_date
            
            if dateline_date is not pd.NaT:
                # Create a combined 'date' column in the DataFrame
                df['date'] = pd.to_datetime(df['Datum'] + df['Jahr'], errors='coerce', dayfirst=True)
                # Find the row in the DataFrame with the matching date
                matching_row = df.loc[df['date'] == date_formatted]
                # Check if letter was from or to specific correspondent

                matching_row = matching_row.loc[matching_row['Name_voll'] == correspondent]
                matching_row = matching_row.loc[matching_row['VON/AN'] == to_from]


                #print(f"The matching row is: {matching_row}")

                if len(matching_row) > 1:
                    print(f"WARNING: More than one row matches the date '{dateline_date}'")
                    letters_without_proper_dateline.append(letter)
                else:
                    if not matching_row.empty:
                        # Update the text field in the matching row
                        letter = letter.replace('\n', ' ')
                        lezzer = letter.replace('  ',' ')
                        df.loc[matching_row.index, 'letter_text'] = letter
                        df.loc[matching_row.index, 'status_letter_text'] = 'to_be_processed'

            else:
                letters_without_proper_dateline.append(letter)


letters = read_texts_from_file(INPUT_TEXT_FILE)
print(f"There are {len(letters)} individual letters in your file.")

datelines, letters_without_proper_dateline = extract_datelines(letters)

# print number of None instances in datelines
print(f"There are {datelines.count(None)} letters without a proper dateline.")
print(f"{len(letters_without_proper_dateline)} Briefe werden nicht bearbeitet.")

# Read the CSV file
df = pd.read_csv(INPUT_CSV_FILE, sep="|")

# Match the letters to the corresponding rows in the DataFrame
match_texts_to_letters(df, datelines, letters, 'Johann Adam Pupikofer', 'VON')
print(f"{len(letters_without_proper_dateline)} Briefe werden nicht bearbeitet.")

# Save the updated CSV file
df.to_csv(OUTPUT_CSV_FILE, index=False, sep='|')

# save log in txt_file
with open(OUTPUT_LOG_FILE, 'w', encoding="utf8") as f:
    for letter in letters_without_proper_dateline:
        f.write(letter + '#')
    