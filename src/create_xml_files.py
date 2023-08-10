import os
import pandas as pd
from datetime import datetime
import calendar
import re
from flair.data import Sentence
from flair.models import SequenceTagger
from flair.nn import Classifier
from flair.data import Label
from bertopic import BERTopic
import itertools


""" Create letters as xml files
"""

def load_letters_from_file(file):
    with open(file, 'r', encoding='utf8') as f:
        # split file into letters using '#' as delimitor
        letters = f.read().split('#')
        split_letters = []
        # for each item in letters list, extract text, metadata insinde '{}' and normalised text inside '[[]]' as sublist
        for letter in letters:
            braces_content = re.findall(r"(\{.*?\})", letter)  # content between braces
            brackets_content = re.findall(r"\[\[(.*?)\]\]", letter, re.DOTALL)  # content between brackets

            # remove content between braces and brackets from original string
            remaining_text = re.sub(r"(\{.*?\})", "", letter, flags=re.DOTALL)
            remaining_text = re.sub(r"\[\[(.*?)\]\]", "", remaining_text, flags=re.DOTALL)
            

            # append extracted content to split_items list
            split_letters.append([braces_content[0] if braces_content else "", 
                            brackets_content[0] if brackets_content else "", 
                            remaining_text.strip()])

    return split_letters


def save_letter(letter, id):
    with open(os.path.join(os.getcwd(), '..', 'data', 'letters', f'{id}.xml'), 'w', encoding='utf8') as f:
        f.write(letter)

def string_to_dict(input_string):
    # Remove the braces and split the string into key-value pairs
    pairs = input_string.replace("{", "").replace("}", "").split(";")
    # Split each pair into a key and value and strip whitespace
    pairs = [pair.split(":") for pair in pairs if pair.strip()]
    # Create a dictionary from the pairs
    dictionary = {key.strip(): value.strip() for key, value in pairs}
    return dictionary

def query_gpt(prompt, string):
    # TODO
    answer = "Todo"
    return answer

def named_entity_recognition(letter):

    # NER using Flair
    # load model
    tagger = Classifier.load('de-ner-large')
    tagger.to('cpu')
    
    # make example sentence in any of the four languages
    sentence = Sentence(letter)

    # predict NER tags
    tagger.predict(sentence)

    list_of_entities = []

    # print predicted NER spans
    for entity in sentence.get_spans('ner'):
        tag: Label = entity.labels[0]
        #print(f'{entity.text} [{tag.value}] ({tag.score:.4f})')
        list_of_entities.append([entity.text, tag.value])
    
    return list_of_entities

"""
def topic_extraction(letters):
    # Creating the BERTopic model
    topic_model = BERTopic(language="german", 
                       calculate_probabilities=True, 
                       embedding_model="deepset/bert-base-german-cased-oldvocab")

    # Fit the model on your letters
    topics, _ = topic_model.fit_transform(letters)

    # Get the topics for each letter
    letter_topics = [topic_model.get_topic(topic) for topic in topics]
    print(letter_topics)
"""

# Function to create a reference based on entity type
def create_reference(entity, unique_persons, unique_places):
    if entity[1] == 'PER':
        normalized_name = re.sub(r'\b\w+\.','',entity[0])
        normalized_name = re.sub('\s+',' ', normalized_name)
        normalized_name = ' '.join(normalized_name.split(' '))
        normalized_names = normalized_name.split(' ')
        if len(normalized_names) > 1:
            normalized_name = normalized_names[-1]

        if len(normalized_name) < 3:
            return None, None
        elif len(normalized_name) == 3 and (normalized_name == 'von' or normalized_name == 'vom'):
            return None, None
        elif normalized_name.isspace():
            return None, None
        elif normalized_name == '\n':
            return None, None

        print(normalized_name)


        is_present = unique_persons['PersonName'].str.contains(normalized_name)
        filtered_df = unique_persons[is_present]
        if not filtered_df.empty:
            person_name = filtered_df['PersonName'].iloc[0] 
            person_id = filtered_df['person_id'].iloc[0] 
            ref = f'../register/lassberg-persons.xml#{person_id}'
            return ref, person_name
    elif entity[1] == 'LOC':
        is_present = unique_places['Ort'].str.contains(entity[0])
        filtered_df = unique_places[is_present]
        if not filtered_df.empty:
            place_id = filtered_df['place_id'].iloc[0]
            place_name = filtered_df['Ort'].iloc[0] 
            ref = f'../register/lassberg-places.xml#{place_id}'
            return ref, place_name
    return None, None


def create_letter(letters, xml_template):
    # read in xml template as string
    with open(xml_template, 'r', encoding='utf8') as f:
        xml_template = f.read()
        #print(xml_template)

    # read in register.csv as dataframe
    register = pd.read_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'register.csv'), sep=';')

    # read in unique_places.csv as dataframe
    unique_places = pd.read_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'unique_places.csv'), sep=';')

    # read in unique_persons.csv as dataframe
    unique_persons = pd.read_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'unique_persons.csv'), sep=';')

    for letter in letters:
        try:
            xml_file = xml_template
            # extract metadata from braces as dictionary
            metadata = string_to_dict(letter[0])
            # get additionaL metadata from register.csv by marching metadata["ID"] with register["ID"] and safe as new df
            metadata_df = register[register['ID'] == metadata['ID']]
            # get item with metadata_df["place_id"].values[0]
            place_from_metadata = unique_places[unique_places['place_id'] == metadata_df["place_id"].values[0]]

            # replace placeholders in xml template with content from letters list
            # replace xml:id
            xml_file = xml_file.replace('xml:id="lassberg-letter-{XML_ID}"', f'xml:id="{metadata["ID"]}"')
            xml_file = xml_file.replace('{XML_ID}', f'{metadata["ID"]}')
            # get date from metadata
            date = metadata_df['Datum'].values[0]
            # replace {SENT_DATE_ISO}
            xml_file = xml_file.replace('{SENT_DATE_ISO}', date)
            # format date from yyy-mm-dd to dd.mm.yyyy
            date = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')
            xml_file = xml_file.replace('{SENT_DATE}', date)
            # determine if letter was send to or from Lassberg
            if metadata_df['VON/AN'].values[0] == 'VON':
                xml_file = xml_file.replace('{SENT_BY}','Joseph von Laßberg')
                xml_file = xml_file.replace('{SENT_TO}', metadata_df['Name'].values[0])
                xml_file = xml_file.replace('{PERS_TO_NUMBER}\" ref=\"{GND}\"', f'{metadata_df["person_id"].values[0]}\" ref=\"https://d-nb.info/gnd/{metadata_df["GND"].values[0]}\"')
                xml_file = xml_file.replace('{PERS_FROM_NUMBER}\" ref=\"{GND}\"', f'lassberg-correspondent-0373\" ref=\"https://d-nb.info/gnd/118778862\"')
                xml_file = xml_file.replace('<placeName key="../register/lassberg-places.xml#lassberg-place-{PLACE_FROM_NUMBER}" ref="{PLACE_FROM_METADATA}">{PLACE_SENT_FROM}</placeName>', f'<placeName key="../register/lassberg-places.xml#{metadata_df["place_id"].values[0]}\">{place_from_metadata["Ort"].values[0]}</placeName>')
                xml_file = xml_file.replace('<placeName key="../register/lassberg-places.xml#lassberg-place-{PLACE_TO_NUMBER}" ref="{PLACE_TO_METADATA}">{PLACE_SENT_TO}</placeName>', '')
                sent_from = 'Joseph von Laßberg'
                sent_to = metadata_df['Name'].values[0]

            else:
                xml_file = xml_file.replace('{SENT_TO}','Joseph von Laßberg')
                xml_file = xml_file.replace('{SENT_BY}', metadata_df['Name'].values[0])
                xml_file = xml_file.replace('{PERS_FROM_NUMBER}\" ref=\"{GND}\"', f'{metadata_df["person_id"].values[0]}\" ref=\"https://d-nb.info/gnd/{metadata_df["GND"].values[0]}\"')
                xml_file = xml_file.replace('{PERS_TO_NUMBER}\" ref=\"{GND}\"', f'lassberg-correspondent-0373\" ref=\"https://d-nb.info/gnd/118778862\"')
                xml_file = xml_file.replace('<placeName key="../register/lassberg-places.xml#lassberg-place-{PLACE_FROM_NUMBER}" ref="{PLACE_FROM_METADATA}">{PLACE_SENT_FROM}</placeName>', '')
                xml_file = xml_file.replace('<placeName key="../register/lassberg-places.xml#lassberg-place-{PLACE_TO_NUMBER}" ref="{PLACE_TO_METADATA}">{PLACE_SENT_TO}</placeName>', f'<placeName key="../register/lassberg-places.xml#{metadata_df["place_id"].values[0]}\">{place_from_metadata["Ort"].values[0]}</placeName>')
                sent_to = 'Joseph von Laßberg'
                sent_from = metadata_df['Name'].values[0]

            # replace {REPOSITORY_PLACE}, {REPOSITORY_INSTITUTION}, {REPOSITORY_SIGNATURE}, {REGISTER_HARRIS}, {REGISTER_LASSBERG}, {PRINTED_IN}, {PRINTED_IN_URL} with value from metadata_df
            xml_file = xml_file.replace('{REPOSITORY_PLACE}', str(metadata_df['Aufbewahrungsort'].values[0]))
            xml_file = xml_file.replace('{REPOSITORY_INSTITUTION}', str(metadata_df['Aufbewahrungsinstitution'].values[0]))
            xml_file = xml_file.replace('{REPOSITORY_SIGNATURE}', '')
            xml_file = xml_file.replace('{REGISTER_HARRIS}', str(metadata_df['Nummer_Harris'].values[0]))
            xml_file = xml_file.replace('{REGISTER_LASSBERG}', str(metadata_df['Journalnummer'].values[0]))
            xml_file = xml_file.replace('{PRINTED_IN}', str(metadata_df['text'].values[0]))
            xml_file = xml_file.replace('{PRINTED_IN_URL}', str(metadata_df['url'].values[0]))

            # add abstract German and English
            abstract_en = query_gpt("Summarize the following letter sent from {sent_from} to {SENT_TO} in English: ", letter[1])
            xml_file = xml_file.replace('{ABSTRACT_ENGLISH}', abstract_en)
            abstract_de = query_gpt("Summarize the following letter sent from {sent_from} to {SENT_TO} in German: ", letter[1])
            xml_file = xml_file.replace('{ABSTRACT_GERMAN}', abstract_de)

            original_text = letter[2]
            normalized_text = letter[1]

            list_of_entities_normalized = named_entity_recognition(normalized_text)
            list_of_entities_original = named_entity_recognition(original_text)
            #print(list_of_entities_original)
            #print(list_of_entities_normalized)

            # Removing duplicates when order doesn't matter
            list_of_entities_normalized = list(k for k,_ in itertools.groupby(sorted(list_of_entities_normalized)))
            list_of_entities_original = list(k for k,_ in itertools.groupby(sorted(list_of_entities_original)))

            print(list_of_entities_normalized)
            print(list_of_entities_original)


            list_of_mentioned_entities = []

            # put entities into <rs> element in xml file
            for entity in list_of_entities_normalized:


                ref, entity_name = create_reference(entity, unique_persons, unique_places)
                if ref:
                    pass
                    #print(ref, entity_name)
                else:
                    ref=""

                normalized_text = normalized_text.replace(entity[0], f'<rs type="{entity[1]}" key="{ref}">{str(entity[0])[:1] + "#+#" + str(entity[0])[1:]}</rs>')
                normalized_text = normalized_text.replace('MISC', 'misc')
                normalized_text = normalized_text.replace('PER','person')
                normalized_text = normalized_text.replace('LOC','place')
                normalized_text = normalized_text.replace('ORG','organisation')

                """

                ref_element = f'<ref type="cmif:mentions{entity[1]}" target="{ref}"><rs>{entity[0]}</rs></ref>'
                ref_element = ref_element.replace('PER', 'Person')
                ref_element = ref_element.replace('LOC', 'Place')
                ref_element = ref_element.replace('ORG', 'Organisation')
                ref_element = ref_element.replace('MISC', 'Bibl')

                list_of_mentioned_entities.append(ref_element)

                """

            normalized_text = normalized_text.replace('#+#','')

            list_of_mentioned_entities = list(set(list_of_mentioned_entities)) 



            for entity in list_of_entities_original:
                ref, entity_name = create_reference(entity, unique_persons, unique_places)
                if ref:
                    print(ref, entity_name)
                else:
                    ref=""

                original_text = original_text.replace(entity[0], f'<rs type="{entity[1]}" key="{ref}">{str(entity[0])[:1] + "#+#" + str(entity[0])[1:]}</rs>')
                original_text = original_text.replace('MISC', 'misc')
                original_text = original_text.replace('PER','person')
                original_text = original_text.replace('LOC','place')
                original_text = original_text.replace('ORG','organisation')

                
                """
                ref_element = f'<ref type="cmif:mentions{entity[1]}" target="{ref}"><rs>{entity[0]}</rs></ref>'
                ref_element = ref_element.replace('PER', 'Person')
                ref_element = ref_element.replace('LOC', 'Place')
                ref_element = ref_element.replace('ORG', 'Organisation')
                ref_element = ref_element.replace('MISC', 'Bibl')

            # replace list of mentioned entities by joined list
            xml_file = xml_file.replace('<ref type="cmif:mentionsPerson" target="../register/lassberg-persons.xml#lassberg-correspondent-{PERS_NUMBER}"><rs>{ORIGINAL_STRING_MENTION}</rs></ref>', '\n'.join(list_of_mentioned_entities))
            
            """
            original_text = original_text.replace('#+#','')

                
            # replace {ORIGINAL_TEXT} and {NORMALIZED_TEXT} with value from letters list
            xml_file = xml_file.replace('{ORIGINAL_TEXT}', original_text)
            xml_file = xml_file.replace('{NORMALIZED_TEXT}', normalized_text)

            save_letter(xml_file, metadata["ID"])
        except Exception as e:
            print(e)
            try:
                print(letter[0])
            except:
                pass
            

def process_letters(letters):
    for letter in letters:
        create_letter(letter)
        save_letter(letter)
    
# textfile containing letters and metadata in {} as well as normalisation of text in [[]]
xml_template = os.path.join(os.getcwd(), '..', 'data', 'letter_template.xml')

file_with_letters = os.path.join(os.getcwd(), '..', 'data', 'temp', 'pupikofer_normalized.txt')

split_letters = load_letters_from_file(file_with_letters)
create_letter(split_letters, xml_template)