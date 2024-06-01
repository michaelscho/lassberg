import config

import os
import re
import lxml.etree as LET
from flair.data import Sentence
from flair.models import SequenceTagger
from flair.nn import Classifier
from flair.data import Label
from langchain_community.llms import Ollama
from openai import OpenAI

client = OpenAI(api_key = config.openai_key)

class GetData():
    """ This class gets user input and loads the xml files with the register data and creates a list of persons, places and literature for further processing.

    """

    def __init__(self):
        self.start_pipeline()
        self.method = self.get_retrival_method_from_input()
        self.llm = self.get_llm_from_input()
        self.ids = self.get_ids_from_input()
        self.list_of_persons = self.create_list_from_xml('person', 'lassberg-persons.xml')
        self.list_of_places = self.create_list_from_xml('place','lassberg-places.xml')
        self.list_of_literature = self.create_list_from_xml('bibl', 'lassberg-literature.xml')
        
        self.print_pipeline_parameter()

    def get_ids_from_input(self):
        ids = []
        user_input = input("Enter one or document ids (separated by spaces): ")
        numbers_str = user_input.split()
        for num_str in numbers_str:
            try:
                id = num_str.zfill(4)
                ids.append(id)
            except ValueError:
                print(f"Invalid number: {num_str}")
                exit()
        return ids

    def get_retrival_method_from_input(self):
        user_input = input("Enter method of retrival: \"transkribus\", \"escriptorium\" or \"local\": ")
        if user_input in ["transkribus", "escriptorium", "local"]:
            return user_input
        else:
                print(f"Invalid method: {user_input}")
                exit()

    def get_llm_from_input(self):
        llm = []
        user_input = input("Enter llm to be used: \"gpt4\", \"llama3\" or \"mock\": ")
        if user_input in ["gpt4", "llama3", "mock"]:
            return user_input
        else:
                print(f"Invalid llm: {user_input}")
                exit()

    def start_pipeline(self):
        print(f"Starting processing pipeline.\n".center(20, '#'))

    def print_pipeline_parameter(self):
        print(f"\nRetrival method: {self.method}")
        print(f"LLM: {self.llm}")
        print(f"IDs: {self.ids}")
        print(f"\nProcessing letters...\n".center(20, '#'))

    def load_and_get_root(self, file):
        """ This helper function loads the xml file and returns the root element."""

        xml_file = os.path.join(os.getcwd(), '..', 'data', 'register', file)
        tree = LET.parse(xml_file)
        root = tree.getroot()

        return root

    def create_list_from_xml(self, element, file):
        """ This helper function creates a list from a xml register file."""

        list_of_items = []
        root = self.load_and_get_root(file)
        for item in root.findall('.//{*}' + element):
            if element == 'person':
                list_of_items.append([item.get('{http://www.w3.org/XML/1998/namespace}id'), item.get('ref'), re.sub('\s+',' ', item.find('.//{*}persName').text.replace('\n',''))])
            if element == 'place':
                list_of_items.append([item.get('{http://www.w3.org/XML/1998/namespace}id'), item.find('.//{*}placeName').get('ref'), re.sub('\s+',' ', item.find('.//{*}placeName').text.replace('\n',' '))])
            if element == 'bibl':
                list_of_items.append([item.get('{http://www.w3.org/XML/1998/namespace}id'), item.find('.//{*}author').text])
        return list_of_items

class ProcessText():
    def __init__(self, method, id):
        self.method = method
        self.id = id
        self.letter_text = self.load_text()
        self.preprocess_text()

    def load_text(self):
        if self.method == "transkribus":
            pass
        elif self.method == "escriptorium":
            pass
        elif self.method == "local":
            letter_path = os.path.join(os.getcwd(),'input', f"{self.id}.txt")
            with open(letter_path, 'r', encoding='utf8') as file:
                letter_text = file.read()
        return letter_text
    
    def preprocess_text(self):
        self.letter_text = re.sub(r'\n', ' ', self.letter_text)

class NamedEntityRecognition():
    def __init__(self, letter_text, id, data):
        self.data = data
        self.id = id
        self.letter_text = letter_text
        self.list_of_entities = self.flair_ner_extraction()
        # create gpt lookup strings with less tokens to reduce costs
        self.persons_gpt_lookup = self.create_gpt_lookup(self.data.list_of_persons)
        self.places_gpt_lookup = self.create_gpt_lookup(self.data.list_of_places)
        #self.literature_gpt_lookup = self.create_gpt_lookup(self.data.list_of_literature)
        self.ner_identification()
        #self.persons = self.get_persons()
        #self.places = self.get_places()
        #self.misc = self.get_misc()

    def flair_ner_extraction(self):
        print(f"\nStarting NER extraction for {self.id}")
        #log.log(f"\nStarting NER extraction for {self.id}")
        
        # load model
        tagger = Classifier.load('de-ner-large')
        tagger.to('cpu')
    
        sentence = Sentence(self.letter_text)

        tagger.predict(sentence)

        list_of_entities = []

        # print predicted NER spans
        for entity in sentence.get_spans('ner'):
            tag: Label = entity.labels[0]
            list_of_entities.append([entity.text, tag.value, tag.score])
    
        return list_of_entities
    
    def create_gpt_lookup(self, list):
        # create new list from register files with only number of id and name to reduce tokens used
        list_for_gpt = []
        for item in list:
            list_for_gpt.append([item[0].replace('lassberg-place-','').replace('lassberg-correspondent-',''), item[2]])
        # create string representation from list
        string_for_gpt = ''
        for item in list_for_gpt:
            string_for_gpt += f'{item[0]};{item[1]}|'
        
        return string_for_gpt

    def identification_gpt4(self):
        system_prompt = f'You are a machine build to retrieve information and will only return precisely the information you are asked for, without adding further smalltalk or information. You will also adhere to the format asked.'
        look_up_string_person = ''
        look_up_string_places = ''
        look_up_string_literature = ''
        for item in self.list_of_entities:
            if item[1] == "PER":
                look_up_string_person = look_up_string_person + item[0] + '|'
            elif item[1] == "LOC":
                look_up_string_places = look_up_string_places + item[0] + '|'
            elif item[1] == "MISC":
                look_up_string_literature = look_up_string_literature + item[0] + '|'

        prompt_person_persons = f"""The following is a list of names of persons mentioned in a letter from the 19th century. 
                            It could refer to medieval figures as well as contemporary persons. Each person is separated by '|'. 
                            Check for each person if it might be referenced in the following register and return the list I send you with the corresponding id in '()' after each name.
                            Be aware that ther are propably no exact matches: There might be orthographic differences between the text given in the letter and the register, or abbreviations such as H. (Herr) or v. (von). Additionally, there might be functional words such as 'Graf' or 'Oberamtman', etc. in the text that are not part of the register.
                            However, the person might not be in the register at all.
                            If you cannot find a corrsponding match in the register, just return 'none' instead of the id. 
                            It is important that the list keeps being seperated by '|'. This is the list of names to check: {look_up_string_person}. This is the register in the format 'id-1; name1|id-2; name2|': {self.persons_gpt_lookup}"""

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt_person_persons}]
        
        completion = client.chat.completions.create(model='gpt-4o',messages=messages)
        returned_list_persons_gpt4 = completion.choices[0].message
        print(returned_list_persons_gpt4)







    def ner_identification(self):
        if self.data.llm == "llama3":
            for entity in self.list_of_entities:
                # TODO
                llm = Ollama(model="llama3", system="You are a machine build for information retrival and will only return precisely the information you are asked for, a single id ending with four digits, without adding further smalltalk or information. If you don't know the answer, you will return 'none'.")
                print(llm.invoke(f'"{entity[0]}" is a named entity extracted from a historical letter. Can you identify this entity in the following register and return its id? The register: {str(self.data.list_of_persons)}'))
        elif self.data.llm == "gpt4":
            self.identification_gpt4()
        elif self.data.llm == "mock":
            pass


def main():

    data = GetData()
    for id in data.ids:

        print(f"Processing letter {id}...")
        
        processing = ProcessText(data.method, id)

        print(f"{processing.letter_text}\n")

        ner = NamedEntityRecognition(processing.letter_text, id, data)



        # Process letter
        print(f"Letter {id} processed.\n".center(20, '#'))


if __name__ == "__main__":
    main()
