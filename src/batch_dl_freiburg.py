import requests
import datetime
from bs4 import BeautifulSoup
import pandas as pd
import csv
import os
import time
import pandas as pd

def crawl_and_download(urls):
    log = []
    with open('output.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(['url', 'signature_letter', 'place_letter', 'date_letter', 'letter_id'])

        for url in urls:
            try:
                response = requests.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
                print(soup.title.string)

                signature_element = soup.find('p', id='signatur')
                signature_letter = signature_element.text.strip()
                print(signature_letter)

                place_date_element = soup.find('p', id='publ_place_date')
                place_date_text = place_date_element.text.strip()
                place_letter, date_letter = place_date_text.split(', ')
                print(place_letter)
                date_letter_day, date_letter_month, date_letter_year = date_letter.split('.')
                date_letter = f'{date_letter_day.zfill(2)}-{date_letter_month.zfill(2)}-{date_letter_year}'
                date_letter = datetime.datetime.strptime(date_letter, '%d-%m-%Y').date().isoformat()
                print(date_letter)

                # Load the register.csv file
                df = pd.read_csv('..\\data\\register\\register.csv', delimiter=';')

                # Filter rows where 'Datum' is equal to letter_date
                filtered_df = df[df['Datum'] == date_letter]
                print(filtered_df)

                filtered_df = filtered_df[filtered_df['Aufbewahrungsort'].str.startswith('Freiburg')]

                # If there are still several rows, check if column "Ankunftsort" contains place_letter_text
                # Ensure 'Ankunftsort' is of string type
                filtered_df['Absendeort'] = filtered_df['Absendeort'].astype(str)

                # Optionally, handle missing values
                filtered_df['Absendeort'] = filtered_df['Absendeort'].fillna('No Place')
                print(filtered_df['Absendeort'])
                if len(filtered_df) > 1:
                    print('several columns')
                    filtered_df = filtered_df[filtered_df['Absendeort'].str.contains(place_letter)]

                # If a letter with this date exists, add the id from column 'ID' to the csv file you are creating as letter_id
                if not filtered_df.empty:
                    letter_id = filtered_df['ID'].values[0]
                    print(letter_id)
                else:
                    letter_id = 'No letter found'
                    print(letter_id)

                # create a folder using letter_id in folder 'UB Freiburg'
                folder_name = f'UB Freiburg/{letter_id}'
                os.makedirs(folder_name, exist_ok=True)

                # download the images using this url pattern 'https://dl.ub.uni-freiburg.de/diglitData/image/{letter_id}/{page_number}/003.jpg'
                # where {letter_id} needs to be adapted to the letter at hand
                # and {page_number} is the page number. Use a range from 1 to 10 until you get a 404 error. Make a pause of 1 second between each download
                for page_number in range(1, 11):
                    autograph_number = url.split('/')[-2]
                    image_url = f'https://dl.ub.uni-freiburg.de/diglitData/image/{autograph_number}/{page_number}/{str(page_number).zfill(3)}.jpg'
                    response = requests.get(image_url)
                    if response.status_code == 404:
                        break
                    with open(f'{folder_name}/{letter_id}-{str(page_number).zfill(3)}.jpg', 'wb') as image_file:
                        image_file.write(response.content)
                    time.sleep(1)


                writer.writerow([url, signature_letter, place_letter, date_letter, letter_id])
            except Exception as e:
                print(f'Error: {e}')
                log.append(url)
        print(log)



    print('Data has been successfully written to output.csv')

# Example usage
urls = ['https://dl.ub.uni-freiburg.de/diglit/autogr0342/', 'https://dl.ub.uni-freiburg.de/diglit/autogr0378/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1536/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1539/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1544/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1545/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1546/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1556/', 
'https://dl.ub.uni-freiburg.de/diglit/autogr1579/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1580/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1581/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1582/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1583/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1608/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1616/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1632/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1649/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1697/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1699/', 'https://dl.ub.uni-freiburg.de/diglit/autogr1700/']

# Open 'UB_Freiburg_Insert_Signaturenoutput.csv' and '../data/register/register.csv' using pandas
df_signature = pd.read_csv('UB_Freiburg_Insert_Signaturenoutput.csv', delimiter=';')
df_register = pd.read_csv('../data/register/register.csv', delimiter=';')

# insert value of df_signature['signature_letter'] into df_register['Signatur'] where df_register['ID'] == df_signature['letter_id']
for index, row in df_signature.iterrows():
    print(row)
    df_register.loc[df_register['ID'] == row['letter_id'], 'Signatur'] = row['signature_letter'].replace('Universitätsbibliothek Freiburg i. Br., ', '')
    # insert url into iiif_manifest
    df_register.loc[df_register['ID'] == row['letter_id'], 'iiif_manifest'] = row['url']
# save df_register to 'register.csv'
df_register.to_csv('register.csv', sep=';', index=False)


#crawl_and_download(urls)

