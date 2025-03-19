import config
from datetime import datetime
import os
import re
import pandas as pd
import lxml.etree as LET
from flair.data import Sentence
from flair.models import SequenceTagger
from flair.nn import Classifier
from flair.data import Label
from langchain_community.llms import Ollama
from openai import OpenAI
import requests
import time
from zipfile import ZipFile

client = OpenAI(api_key = config.openai_key)

class GetData:
    """ This class gets user input and loads the xml files with the register data and creates a list of persons, places and literature for further processing.

    """

    def __init__(self):
        self.start_pipeline()
        self.method = self.get_retrival_method_from_input()
        self.llm = self.get_llm_from_input()
        self.ids = self.get_ids_from_input()
        self.transkribus_id = self.get_transkribus_id_from_input()
        self.processing_method = self.get_processing_method_from_input()
        self.letters_data = self.read_register_csv() 
        self.list_of_persons = self.create_list_from_xml('person', 'lassberg-persons.xml')
        self.list_of_places = self.create_list_from_xml('place','lassberg-places.xml')
        self.list_of_literature = self.create_list_from_xml('bibl', 'lassberg-literature.xml')
        self.list_of_ners_for_identification = []
        
        self.print_pipeline_parameter()

    def read_register_csv(self):
        """ This function reads the csv file with the register data and returns a letter as a pandas dataframe.
        """
        # read in register file
        register = pd.read_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'register.csv'), sep=';', encoding='utf-8') 
        register = register.fillna('')

        #register = pd.read_csv(os.path.join(os.getcwd(), '..', 'data', 'register', 'register.csv'), sep=';', encoding='latin1') 
            

        return register

    def get_ids_from_input(self):
        ids = []
        user_input = input("Enter a document id: ")
        numbers_str = user_input.split()
        for num_str in numbers_str:
            try:
                id = num_str.zfill(4)
                ids.append(id)
            except ValueError:
                print(f"Invalid number: {num_str}")
                exit()
        return ids
    
    def get_transkribus_id_from_input(self):
        
        user_input = input("Enter a transkribus document id: ")
        numbers_str = user_input
        return numbers_str

    def get_retrival_method_from_input(self):
        user_input = input("Enter method of retrival: \"transkribus\", \"escriptorium\" or \"local\": ")
        if user_input in ["transkribus", "escriptorium", "local"]:
            return user_input
        else:
                print(f"Invalid method: {user_input}")
                exit()

    def get_processing_method_from_input(self):
        user_input = input("Enter method of processing: \"cpu\" or \"gpu\": ")
        if user_input in ["cpu", "gpu"]:
            return user_input
        else:
                print(f"Invalid method: {user_input}")
                exit()

    def get_llm_from_input(self):
        llm = []
        user_input = input("Enter llm to be used: \"gpt4\", \"llama3\", \"mock\" or \"none\": ")
        if user_input in ["gpt4", "llama3", "mock", "none"]:
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
                id = item.get('{http://www.w3.org/XML/1998/namespace}id')
                idno = item.find('.//{*}idno').text if item.find('.//{*}idno') is not None else ''
                author = item.find('.//{*}author').text if item.find('.//{*}author') is not None else ''
                title = item.find('.//{*}title').text if item.find('.//{*}title') is not None else ''
                list_of_items.append([id, idno, f"{author} {title}"])
        print(list_of_items)
        
        return list_of_items
    
class ProcessPageXMLFromTranskribus:
    """ This class processes the page-xml files from Transkribus, processes text using gpt3.5 or gpt4 
        via openai and creates a TEI representation of the letter.
    """

    def __init__(self, doc_title, document_id):
        self.doc_title = doc_title
        self.path_to_folder = self.create_export_folder()
        self.document_id = document_id
        self.collection_id = config.collection_id
        self.user = config.transcribus_user
        self.pw = config.transcribus_pw
        self.session = self.login_transkribus()
        self.export_file_url = self.export_pagexml()
        self.zip_file_name = self.download_export()
        self.export_folder = config.export_folder
        self.unzip_file()
        self.rename_files()        
        

    def login_transkribus(self):
        """ Login to Transkribus and start session

        Uses REST url https://transkribus.eu/TrpServer/rest/auth/login
        :param user: Username as string (should be specified in config.py)
        :param pw: Password as string (should be specified in config.py)
        :return: Returns session
        """

        # set session...
        session = requests.Session()
        # ..post credentials
        req = session.post('https://transkribus.eu/TrpServer/rest/auth/login',data = {'user': self.user, 'pw': self.pw})
        return session

    def export_pagexml(self):
        """ Export page-XML to local machine for further processing

        Uses REST url https://transkribus.eu/TrpServer/rest/collections/{collection-ID}/{document-ID}/fulldoc

        :param session: Transkribus session as returned from login_transkribus()
        :param collection_id: Transkribus collection number as Int
        :param document_id: Transkribus document number as Int
        :param startpage: First page of document to be exported as Int
        :param endpage: Last page of document to be exported as Int
        :return: Returns url to exported data that can be downloaded as zip-file
        """

        # concat url to document...
        url = 'https://transkribus.eu/TrpServer/rest/collections/' + str(self.collection_id) + '/' + str(self.document_id) + '/export'

        # ...set paramater for exporting page-xml...
        params = '{"commonPars":{"doExportDocMetadata":true,"doWriteMets":true,"doWriteImages":false,"doExportPageXml":true,"doExportAltoXml":false,"doExportSingleTxtFiles":false,"doWritePdf":false,"doWriteTei":false,"doWriteDocx":false,"doWriteOneTxt":false,"doWriteTagsXlsx":false,"doWriteTagsIob":false,"doWriteTablesXlsx":false,"doCreateTitle":false,"useVersionStatus":"Latest version","writeTextOnWordLevel":false,"doBlackening":false,"selectedTags":["add","date","Address","supplied","work","capital-rubricated","unclear","sic","structure","div","regionType","seg-supp","speech","person","gap","organization","comment","abbrev","place","rubricated"],"font":"FreeSerif","splitIntoWordsInAltoXml":false,"pageDirName":"page","fileNamePattern":"${filename}","useHttps":true,"remoteImgQuality":"orig","doOverwrite":true,"useOcrMasterDir":true,"exportTranscriptMetadata":true,"updatePageXmlImageDimensions":false},"altoPars":{"splitIntoWordsInAltoXml":false},"pdfPars":{"doPdfImagesOnly":false,"doPdfImagesPlusText":true,"doPdfWithTextPages":false,"doPdfWithTags":false,"doPdfWithArticles":false,"pdfImgQuality":"view"},"docxPars":{"doDocxWithTags":false,"doDocxPreserveLineBreaks":false,"doDocxForcePageBreaks":false,"doDocxMarkUnclear":false,"doDocxKeepAbbrevs":false,"doDocxExpandAbbrevs":false,"doDocxSubstituteAbbrevs":false}}'

        # ...post export request, starts export and returns job number...
        export_request = self.session.post(url,params)
        export_request = export_request.text

        # ...check status of job after a couple of seconds (usually, it takes around 5 seconds to export a page)...
        time.sleep(6)
        export_status = self.session.get('https://transkribus.eu/TrpServer/rest/jobs/' + export_request)
        export_status = export_status.json()

        while export_status["state"] != 'FINISHED':
            # ...check again after 5 seconds...
            export_status = self.session.get('https://transkribus.eu/TrpServer/rest/jobs/' + export_request)
            export_status = export_status.json()
            time.sleep(10)

        # ..get url of exported zip file...
        export_file_url = export_status["result"]
        return export_file_url

    def download_export(self):
        """ Download of exported data

        Downloads exported data from transkribus server using url returned by export_pagexml() as zip file,
        saves it to export folder on local machine specified in config.py and returns name of zip file

        :param url: Url to zip file as string
        :return: Name of downloaded zip file as string
        """

        # download zip file to the subfolder ./documents on a local machine...
        zip_file_name = os.path.join(os.getcwd(),'..','data','pagexml','export.zip')
        zip_file = requests.get(self.export_file_url)
        zip_file.raise_for_status()
        save_file = open(zip_file_name,'wb')
        for chunk in zip_file.iter_content(100000):
            save_file.write(chunk)
        save_file.close()
        return zip_file_name
    
    def create_export_folder(self):
        path = os.path.join(os.getcwd(),'..','data','pagexml',f'lassberg-letter-{self.doc_title}')
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def unzip_file(self):
        """ Extracts data from zip file

        Extracts data from zip file into local folder specified in config.py
        and returns path to pageXML for further processing

        :param zip_file_name: name of zip file as string as returned by download_export()
        :return: path to downloaded pageXML as string
        """

        with ZipFile(self.zip_file_name, 'r') as zip_obj:
            # Identify the parent directory containing the "page" subfolder
            for file in zip_obj.namelist():
                parts = file.split("/")
                if len(parts) > 1 and parts[-2] == "page":
                    # Extract only files inside the "page" subfolder
                    target_path = os.path.join(self.path_to_folder, os.path.basename(file))
                    print(target_path)
                    with zip_obj.open(file) as source, open(target_path, 'wb') as target:
                        target.write(source.read())
        

    def rename_files(self):
        """ Renames downloaded files

        Renames downloaded files to numbered filenames using 4 leading zeros
        :param path_to_pagexml: Path to file as provided by function unzip_file
        """
        n = 1
        # get sorted list of files in folder
        for filename in os.listdir(self.path_to_folder):
            # rename files
            os.rename(os.path.join(self.path_to_folder,filename), os.path.join(self.path_to_folder, f"lassberg-letter-{self.doc_title}-{str(n)}.xml"))
            n = n + 1


    

class ProcessText:
    def __init__(self, method, id, transkribus_id=None):
        self.method = method
        self.doc_title = id
        self.transkribus_id = transkribus_id
        self.id = id
        self.letter_text = self.load_text()
        self.letter_text_ner = self.post_process(self.letter_text)
        self.preprocess_text()

    def load_text(self):
        if self.method == "transkribus":
            transkribus = ProcessPageXMLFromTranskribus(self.id, self.transkribus_id)
            letter_text = self.create_tei_from_pagexml(transkribus.path_to_folder)
            
        elif self.method == "escriptorium":
            pass
        elif self.method == "local":
            #letter_path = os.path.join(os.getcwd(),'input', f"{self.id}.txt")
            #with open(letter_path, 'r', encoding='utf8') as file:
            #    letter_text = file.read()
            xml_path = os.path.join(os.getcwd(),'..', "data", "pagexml", f"lassberg-letter-{self.id}")
            letter_text = self.create_tei_from_pagexml(xml_path)
            print(letter_text)
            
        return letter_text
    
    def create_tei_from_pagexml(self, path_to_folder):
        """
        Creates TEI representation from the extracted text in the PAGE XML files.

        This function processes each PAGE XML file and extracts the text from the columns and headers.
        It constructs the TEI representation by combining the extracted text and applying certain
        replacements and transformations. The TEI representation is stored in the 'bdd_tei_text' attribute of the object.
        """

        letter_text = ""
        # open folder with pagexml-files
        path_to_pagexml_files = [os.path.join(path_to_folder,f) for f in os.listdir(path_to_folder) if f.endswith('.xml')]

        # open each pagexml-file for exporting text to tei
        n = 1
        lb_break = False
        for filename in path_to_pagexml_files:
            tree = LET.parse(filename)
            root = tree.getroot()
            page_text = ""
            text_regions = root.findall('.//{*}TextRegion')
            if len(text_regions) > 2:
                print("Too many TextRegions.")
                exit()
            elif len(text_regions) > 2:
                print("Double Page.")
            
            # iterate over all text regions
            for text_region in text_regions:
                # creates page beginning for each xml-pagefile using data taken from config file
                page_break = f'<pb n="{n}" corresp="../pagexml/{self.doc_title}/{self.doc_title}-{n}.xml"/>'
                page_text = page_text + page_break    
            
                # iterate over all text lines
                e = 1
                for text_line in text_region.findall('.//{*}TextLine'):
                        
                    # ad <lb> element and text
                    break_equals_no = "break=\"no\" "
                    line_content = f"<lb {break_equals_no if lb_break == True else ''}xml:id=\"lassberg-letter-{self.doc_title}-{n}-{e}\" n=\"{e}\" corresp=\"{text_line.get('id')}\"/>{text_line.findall('.//{*}Unicode')[0].text}\n"
                    e = e + 1
                    page_text = page_text + line_content
                    if '¬' in text_line.findall('.//{*}Unicode')[0].text:
                        lb_break = True
                        page_text = page_text.replace('¬','')
                    else:
                        lb_break = False

                n = n + 1

            letter_text = letter_text + page_text
        
        return letter_text
    
    def preprocess_text(self):
        self.letter_text = re.sub(r'\n', ' ', self.letter_text)

    def post_process(self, text):
        text = re.sub(r'<.*?/>', '', text)
        text = re.sub(r'<.*?>', '', text)
        print(text)
        return text

class NamedEntityRecognition:
    def __init__(self, processing, id, data):
        self.data = data
        self.id = id
        self.letter_text = processing.letter_text
        self.letter_text_ner = processing.letter_text_ner

        self.list_of_entities = []
        if data.llm == "mock":
            print("""Starting NER extraction for 0971
            2024-06-03 10:40:13,884 SequenceTagger predicts: Dictionary with 20 tags: <unk>, O, B-PER, E-PER, S-LOC, B-MISC, I-MISC, E-MISC, S-PER, B-ORG, E-ORG, S-ORG, I-ORG, B-LOC, E-LOC, S-MISC, I-PER, I-LOC, <START>, <STOP>
            [['Eppishausen', 'LOC', 0.9999920129776001], ['Raumers Geschichte der Hohenstaufen', 'MISC', 0.9997226893901825], ['v. Ittner', 'PER', 0.9981066981951395], ['Zapfs Monument', 'PER', 0.7412565350532532], ['Augsburg', 'LOC', 0.9999911785125732], ['Trutpert Neugarts', 'PER', 0.9999922513961792], ['Episcopatus Constantiensis', 'MISC', 0.9998691082000732], ['Graven Mülinen', 'PER', 0.9889882802963257], ['Bern', 'LOC', 0.9999779462814331], ['Appenzeller Krieges', 'MISC', 0.9999639987945557], ['H. v. Arx', 'PER', 0.9999239444732666], ['Anshelms', 'PER', 0.5269403457641602], ['Justinger', 'PER', 0.9996330738067627], ['Tschachtlan', 'PER', 0.9996806383132935], ['Rozmital', 'LOC', 0.9818222522735596], ['von Constanz', 'PER', 0.49804477393627167], ['Joseph v. Laßberg', 'PER', 0.928373247385025]]""")
            self.list_of_entities = [['Eppishausen', 'LOC', 0.9999920129776001], ['Raumers Geschichte der Hohenstaufen', 'MISC', 0.9997226893901825], ['v. Ittner', 'PER', 0.9981066981951395], ['Zapfs Monument', 'PER', 0.7412565350532532], ['Augsburg', 'LOC', 0.9999911785125732], ['Trutpert Neugarts', 'PER', 0.9999922513961792], ['Episcopatus Constantiensis', 'MISC', 0.9998691082000732], ['Graven Mülinen', 'PER', 0.9889882802963257], ['Bern', 'LOC', 0.9999779462814331], ['Appenzeller Krieges', 'MISC', 0.9999639987945557], ['H. v. Arx', 'PER', 0.9999239444732666], ['Anshelms', 'PER', 0.5269403457641602], ['Justinger', 'PER', 0.9996330738067627], ['Tschachtlan', 'PER', 0.9996806383132935], ['Rozmital', 'LOC', 0.9818222522735596], ['von Constanz', 'PER', 0.49804477393627167], ['Joseph v. Laßberg', 'PER', 0.928373247385025]]
        else:
            self.flair_ner_extraction(data)
            
        self.replace_text_with_tei_tags(processing)
        
    def flair_ner_extraction(self, data):
        print(f"\nStarting NER extraction for {self.id}")
        #log.log(f"\nStarting NER extraction for {self.id}")
        
        # load model
        tagger = Classifier.load('de-ner-large')
        if self.data.processing_method == 'cpu':
            tagger.to('cpu')
        else:
            tagger.to('cuda')


        sentence = Sentence(self.letter_text_ner)

        tagger.predict(sentence)

        # print predicted NER spans
        for entity in sentence.get_spans('ner'):
            tag: Label = entity.labels[0]
            self.list_of_entities.append([entity.text, tag.value, tag.score])
        
        data.list_of_ners_for_identification = data.list_of_ners_for_identification + self.list_of_entities 

    def replace_text_with_tei_tags(self, processing):
        print(self.list_of_entities)
        for item in self.list_of_entities:
            if item[1] == 'PER':
                type = 'person'
            elif item[1] == 'LOC':
                type = 'place'
            elif item[1] == 'MISC':
                type = 'bibl'
            else:
                type = ''

            if item[0] == 'Inen':
                pass
            elif len(item[0]) == 1:
                pass
            else:

                self.letter_text = self.letter_text.replace(f'{item[0]}',f'<rs type="{type}">{item[0][:1]}*+*{item[0][1:]}</rs>')
                self.letter_text = self.letter_text.replace(f'{item[0]}.',f'<rs type="{type}">{item[0][:1]}*+*{item[0][1:]}</rs>')
                self.letter_text = self.letter_text.replace(f'{item[0]};',f'<rs type="{type}">{item[0][:1]}*+*{item[0][1:]}</rs>')
                self.letter_text = self.letter_text.replace(f'{item[0]}:',f'<rs type="{type}">{item[0][:1]}*+*{item[0][1:]}</rs>')
        
        processing.letter_text = self.letter_text.replace('*+*','')

        print(processing.letter_text)

class LLMTextProcessing:
    def __init__(self, data, processing):
        self.letter_text = processing.letter_text_ner
        self.llm = data.llm
        self.normalization = self.normalize_text()
        self.translation = self.translate_text()
        #self.summary = self.summarize_text()
        self.summary = ""

    def normalize_text(self):
        if self.llm == "gpt4":
            system_prompt = f"""You are a machine build to normalize historical texts into a modern ortography. 
                                You will only correct ortography and not interfere with the text in any other way."""
        
            prompt_person = f"""The following is a letter written in German from the 19th century. It may contain historic ortography ar small errors.
                                Normalize the text to modern ortography. The text is as follows: {self.letter_text}"""
            
            normalization = self.gpt_processing(system_prompt, prompt_person)
            return normalization
            

    def translate_text(self):
        if self.llm == "gpt4":
            system_prompt = f"""You are a machine build to translate historical texts into English. 
                                You will only translate the text and not interfere with the text in any other way."""
        
            prompt_person = f"""The following is a letter written in German from the 19th century. It may contain historic ortography ar small errors.
                                Translate the text to English. The text is as follows: {self.letter_text}"""
            
            translation = self.gpt_processing(system_prompt, prompt_person)
            return translation

    def summarize_text(self):
        if self.llm == "gpt4":
            system_prompt = f"""You are a machine build to summarize historical texts. 
                                You will only summarize the text and not interfere with the text in any other way."""
        
            prompt_person = f"""The following is a letter written in German from the 19th century. It may contain historic ortography ar small errors.
                                Summarize the text in not more than 200 words. The text is as follows: {self.letter_text}"""
            
            summary = self.gpt_processing(system_prompt, prompt_person)
            return summary

    def gpt_processing(self, system_prompt, prompt):
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
        completion = client.chat.completions.create(model='gpt-4o',messages=messages)
        processed_text = completion.choices[0].message.content
        return processed_text
                  

class LLMIdentification:
    def __init__(self, data):
        self.list_of_entities_for_identification = data.list_of_ners_for_identification
        self.ids = data.ids
        self.llm = data.llm
        self.make_list_of_entities_for_identification_unique()

        self.look_up_string_person = self.create_lokup_from_ner("PER")
        self.look_up_string_place = self.create_lokup_from_ner("LOC")
        self.look_up_string_literature = self.create_lokup_from_ner("MISC")

        # create gpt lookup strings with less tokens to reduce costs
        self.persons_register_lookup = self.create_register_lookup(data.list_of_persons)
        self.places_register_lookup = self.create_register_lookup(data.list_of_places)
        self.literature_register_lookup = self.create_register_lookup(data.list_of_literature)

        self.identified_persons = ""
        self.identified_places = ""
        self.identified_literature = ""

        self.system_prompt = f"""You are a machine build to retrieve information and will only return precisely the information you are asked for, 
                                without adding further smalltalk or information. You will also adhere to the format asked."""
        
        self.prompt_person = f"""The following is a list of names of persons mentioned in a letter from the 19th century. 
                            It could refer to medieval figures as well as contemporary persons. Each person is separated by '|'. 
                            Check for each person if it might be referenced in the following register and return the list I 
                            send you with the corresponding id in '()' after each name. Be aware that ther are propably no exact matches: 
                            There might be orthographic differences between the text given in the letter and the register, 
                            or abbreviations such as H. (Herr) or v. (von). Additionally, there might be functional words such as 'Graf' or 
                            'Oberamtman', etc. in the text that are not part of the register. However, 
                            the person might not be in the register at all. If you cannot find a corrsponding match in the register, 
                            just return 'none' instead of the id. It is important that the list keeps being seperated by '|'. 
                            This is the list of names to check: {self.look_up_string_person}. 
                            This is the register in the format 'id-1; name1|id-2; name2|': {self.persons_register_lookup}"""

        self.prompt_places = f"""The following is a list of placenames mentioned in a letter from the 19th century. 
                            Each place is separated by '|'. Check for each place if it might be referenced in 
                            the following register and return the list I send you with the corresponding id in 
                            '()' after each placename. 
                            Be aware that ther are propably no exact matches: There might be orthographic 
                            differences between the text given in the letter and the register, or abbreviations 
                            such as 'Const.' for 'Konstanz' or 'Epp.' for 'Eppishausen. Additionally, 
                            metaphors might beu sed such as 'Villa Epponis' for 'Eppishausen'. However, 
                            the person might not be in the register at all.
                            If you cannot find a corrsponding match in the register, 
                            just return 'none' instead of the id. It is important that the list keeps being seperated by '|'. 
                            This is the list of placenames to check: {self.look_up_string_place}. 
                            This is the register in the format 'id-1; placename1|id-2; placename2|': {self.places_register_lookup}"""

        self.prompt_literature = f"""The following is a list of literature mentioned in a letter from the 19th century. 
                            It could refer to abstract works as well as particular exemplars such as a medieval manuscript. 
                            Each entity is separated by '|'. 
                            Check for each entity if it might be referenced in the following register and return the list I 
                            send you with the corresponding id in '()' after each entity. Be aware that ther are propably no exact matches: 
                            There might be orthographic differences between the text given in the letter and the register, 
                            or abbreviations and short titles such 'Tschudis Geschichte der Schweiz". However, 
                            the entity might not be in the register at all. If you cannot find a corrsponding match in the register, 
                            just return 'none' instead of the id. It is important that the list keeps being seperated by '|'. 
                            This is the list of names to check: {self.look_up_string_literature}. 
                            This is the register in the format 'id-1; name1|id-2; name2|': {self.literature_register_lookup}"""

        self.identification_of_ner()
    
    def create_lokup_from_ner(self, type):
        look_up_string = ""    
        for item in self.list_of_entities_for_identification:
            if item[1] == type:
                look_up_string = look_up_string + item[0] + '|'
        return look_up_string

    def make_list_of_entities_for_identification_unique(self):
        seen = set()
        # Use a list comprehension to filter unique items based on the (first, second) pair
        self.list_of_entities_for_identification = [item for item in self.list_of_entities_for_identification if not (item[0], item[1]) in seen and not seen.add((item[0], item[1]))]
        for item in self.list_of_entities_for_identification:
            item[1] = item[1].replace("ORG", "PER")

    def create_register_lookup(self, register):
        # create new list from register files with only number of id and name to reduce tokens used
        list_for_llm = []
        for item in register:
            list_for_llm.append([item[0].replace('lassberg-place-','').replace('lassberg-correspondent-','').replace('lassberg-literature-',''), item[2]])
        # create string representation from list
        string_for_llm = ''
        for item in list_for_llm:
            string_for_llm += f'{item[0]};{item[1]}|'
        string_for_llm = re.sub('None',' ', string_for_llm)
        string_for_llm = re.sub('\n',' ', string_for_llm)
        string_for_llm = re.sub('\s+',' ', string_for_llm)
        string_for_llm = re.sub('\t','', string_for_llm)
        string_for_llm = re.sub('; ','', string_for_llm)
        
        return string_for_llm    

    def identification_of_ner(self):
        if self.llm == "gpt4":
            self.gpt4_identification("person")
            self.gpt4_identification("place")
            self.gpt4_identification("literature")
        elif self.llm == "llama3":
            self.llama_identification()
        elif self.llm == "mock":
            self.identified_persons = self.mock_identification("persons")
            self.identified_places = self.mock_identification("places")
            self.identified_literature = self.mock_identification("literature")
            print(self.identified_persons)

    def mock_identification(self, type):
        with open(os.path.join(os.getcwd(), '..', 'logs', f'{type}.log'), 'r', encoding='utf8') as f:
            string = f.read()
        return string

    
    def llama_identification(self):
        llm = Ollama(model="llama3", system=self.system_prompt, temperature=0)
        self.identified_persons = llm.invoke(self.prompt_person)
        self.identified_places = llm.invoke(self.prompt_places)
        self.identified_literature = llm.invoke(self.prompt_literature)
        print(self.identified_persons)
        print(self.identified_places)
        print(self.identified_literature)

    def gpt4_identification(self, type):
        if len(self.look_up_string_person) > 0:
            self.gpt4_identify("person")
        if len(self.look_up_string_place) > 0:
            self.gpt4_identify("place")
        if len(self.look_up_string_literature) > 0:
            self.gpt4_identify("literature")

    def gpt4_identify(self, type):
        if type == "person":
            messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": self.prompt_person}]
            completion = client.chat.completions.create(model='gpt-4o',messages=messages)
            self.identified_persons = completion.choices[0].message.content
        elif type == "place":
            messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": self.prompt_places}]
            completion = client.chat.completions.create(model='gpt-4o',messages=messages)
            self.identified_places = completion.choices[0].message.content
        elif type == "literature":
            messages = [{"role": "system", "content": self.system_prompt}, {"role": "user", "content": self.prompt_literature}]
            completion = client.chat.completions.create(model='gpt-4o',messages=messages)
            self.identified_literature = completion.choices[0].message.content
        
        with open(os.path.join(os.getcwd(), '..', 'logs', 'persons.log'), 'w', encoding='utf8') as f:
            f.write(self.identified_persons)
        with open(os.path.join(os.getcwd(), '..', 'logs', 'places.log'), 'w', encoding='utf8') as f:
            f.write(self.identified_places)
        with open(os.path.join(os.getcwd(), '..', 'logs', 'literature.log'), 'w', encoding='utf8') as f:
            f.write(self.identified_literature)


class InsertIdentification:
    def __init__(self, data, identification_results):
        self.letters = data.ids
        self.identification_results = identification_results
        self.identification_results_as_list = self.transform_identification_results()
        
        self.insert_xmlid()

    def transform_identification_results(self):
        combined_list = []
        list_persons = self.identification_results.identified_persons.split("|")
        list_places = self.identification_results.identified_places.split("|")
        list_literature = self.identification_results.identified_literature.split("|")
        combined_lists = list_persons + list_places + list_literature
        for item in combined_lists:
            if item == "":
                pass
            elif "(none)" in item:
                pass
            else:
                try:
                    item = item.split("(")
                    item[0] = item[0].strip()
                    item[1] = item[1].replace(")",'')
                    if "," in item[1]:
                        item[1] = item[1].split(',')[0]  
                    combined_list.append(item)
                except:
                    pass
                
        return combined_list
        

    def insert_xmlid(self):
        namespaces = {'tei': 'http://www.tei-c.org/ns/1.0'}
        for letter in self.letters:
            root = self.get_letter_as_xml(letter)
            rs_elements = root.xpath('.//tei:rs', namespaces=namespaces)
            for rs_element in rs_elements:
                #print(rs_element.text)
                for item in self.identification_results_as_list:
                    if rs_element.text == item[0]:
                        if rs_element.get('type') == "bibl":
                            prefix = "../register/lassberg-literature.xml#lassberg-literature-"
                        elif rs_element.get('type') == "place":
                            prefix = "../register/lassberg-places.xml#lassberg-place-"
                        else:
                            prefix = "../register/lassberg-persons.xml#lassberg-correspondent-"

                        rs_element.set('key', prefix + item[1])
            self.write_letter(root, letter)
                    

    def get_letter_as_xml(self, letter):
        xml_file = os.path.join(os.getcwd(), 'output', 'lassberg-letter-' + letter + '.xml')
        tree = LET.parse(xml_file)
        root = tree.getroot()
        return root

    def write_letter(self, root, letter):
        tree = LET.ElementTree(root)
        xml_file = os.path.join(os.getcwd(), 'output', 'lassberg-letter-' + letter + '.xml')
        tree.write(xml_file, pretty_print=True, encoding='UTF-8')

     
        
class CreateXML:
    """ This class creates the xml file for each letter, inserts processed data and saves it to the folder ../data/letters/lassberg-letter-id.xml.
    """
    def __init__(self, letter_text, id, data, processed_tests):
        self.list_of_persons = data.list_of_persons
        self.list_of_places = data.list_of_places
        self.original_text = letter_text
        
        self.normalized_text = processed_tests.normalization
        self.translated_text = processed_tests.translation
        self.summary_text = processed_tests.summary
        
        self.doc_id = f'lassberg-letter-{id}'
        self.letter_data = self.get_letter_data(data)
        self.xml_template = self.create_letter()
        self.encoded_letter = self.replace_placeholder_in_template()
        self.create_letter()
        self.save_letter()

    def get_letter_data(self, data):
        row = data.letters_data.loc[data.letters_data['ID'] == self.doc_id]
        return row

    def replace_placeholder_in_template(self):
        """ This function replaces the placeholders in the xml template with the data from the register and the processed text.
        """        

        self.xml_template = self.xml_template.replace('{lassberg-letter-XML_ID}',self.doc_id)
        self.xml_template = self.xml_template.replace('{SENT_BY}',self.letter_data['SENT_FROM_NAME'].values[0])
        self.xml_template = self.xml_template.replace('{SENT_TO}',self.letter_data['RECIVED_BY_NAME'].values[0])
        try:
            self.xml_template = self.xml_template.replace('{SENT_DATE}', datetime.strptime(self.letter_data['Datum'].values[0], '%Y-%m-%d').strftime('%d.%m.%Y'))
        except:
            self.xml_template = self.xml_template.replace('{SENT_DATE}','Unbekannt')

        self.xml_template = self.xml_template.replace('{REPOSITORY_PLACE}',self.letter_data['Aufbewahrungsort'].values[0])
        self.xml_template = self.xml_template.replace('{REPOSITORY_INSTITUTION}',self.letter_data['Aufbewahrungsinstitution'].values[0])
        self.xml_template = self.xml_template.replace('{REPOSITORY_SIGNATURE}',self.letter_data['Signatur'].values[0].strip())
        self.xml_template = self.xml_template.replace('{REGISTER_HARRIS}',str(self.letter_data['Nummer_Harris'].values[0]))
        if type(self.letter_data['Journalnummer'].values[0]) == float:
            self.letter_data['Journalnummer'].values[0] = ""
        self.xml_template = self.xml_template.replace('{REGISTER_LASSBERG}',self.letter_data['Journalnummer'].values[0])

        self.xml_template = self.xml_template.replace('{PRINTED_IN}',self.letter_data['published_in'].values[0])
        self.xml_template = self.xml_template.replace('{PRINTED_IN_URL}',self.letter_data['published_in_url'].values[0])
        self.xml_template = self.xml_template.replace('{XML_ID}',self.doc_id)
        try:
            self.xml_template = self.xml_template.replace('{SENT_DATE_ISO}',self.letter_data['Datum'].values[0])
        except:
            self.xml_template = self.xml_template.replace('{SENT_DATE_ISO}','Unbekannt')
        try:
            self.xml_template = self.xml_template.replace('{ORIGINAL_TEXT}', self.original_text)
        except: 
            pass

        try:
            self.xml_template = self.xml_template.replace('{NORMALIZED_TEXT}', self.normalized_text)
        except: 
            pass

        try:
            self.xml_template = self.xml_template.replace('{TRANSLATED_TEXT}', self.translated_text)
        except: 
            pass

        try:
            self.xml_template = self.xml_template.replace('{SUMMARY_TEXT}', self.summary_text)
        except: 
            pass

        self.xml_template = self.xml_template.replace('{today}',datetime.today().strftime('%Y-%m-%d'))
        
        # look up list of persons based on correspondent partners id
        matching_correspondent_to = [sublist for sublist in self.list_of_persons if self.letter_data['RECIVED_BY_ID'].values[0] in sublist]
        matching_correspondent_from = [sublist for sublist in self.list_of_persons if self.letter_data['SENT_FROM_ID'].values[0] in sublist]

        if self.letter_data['SENT_FROM_NAME'].values[0] == 'Joseph von Laßberg':
            self.xml_template = self.xml_template.replace('{PERS_TO_NUMBER}\" ref=\"{GND}\"', f'{self.letter_data["RECIVED_BY_ID"].values[0]}\" ref=\"{matching_correspondent_to[0][1]}\"')
            self.xml_template = self.xml_template.replace('{PERS_FROM_NUMBER}\" ref=\"{GND}\"', f'lassberg-correspondent-0373\" ref=\"https://d-nb.info/gnd/118778862\"')
            self.xml_template = self.xml_template.replace('<placeName key="../register/lassberg-places.xml#lassberg-place-{PLACE_FROM_NUMBER}" ref="{PLACE_FROM_METADATA}">{PLACE_SENT_FROM}</placeName>', f'<placeName key=\"../register/lassberg-places.xml#{ self.letter_data["Absendeort_id"].values[0] }\">{ self.letter_data["Absendeort"].values[0] }</placeName>')
            self.xml_template = self.xml_template.replace('<placeName key="../register/lassberg-places.xml#lassberg-place-{PLACE_TO_NUMBER}" ref="{PLACE_TO_METADATA}">{PLACE_SENT_TO}</placeName>', '')
        
        else:
            self.xml_template = self.xml_template.replace('{PERS_FROM_NUMBER}\" ref=\"{GND}\"', f'{self.letter_data["SENT_FROM_ID"].values[0]}\" ref=\"{matching_correspondent_from[0][1]}\"')
            self.xml_template = self.xml_template.replace('{PERS_TO_NUMBER}\" ref=\"{GND}\"', f'lassberg-correspondent-0373\" ref=\"https://d-nb.info/gnd/118778862\"')
            self.xml_template = self.xml_template.replace('<placeName key="../register/lassberg-places.xml#lassberg-place-{PLACE_FROM_NUMBER}" ref="{PLACE_FROM_METADATA}">{PLACE_SENT_FROM}</placeName>', f'<placeName key=\"../register/lassberg-places.xml#{ self.letter_data["Absendeort_id"].values[0] }\">{ self.letter_data["Absendeort"].values[0] }</placeName>')
            self.xml_template = self.xml_template.replace('<placeName key="../register/lassberg-places.xml#lassberg-place-{PLACE_TO_NUMBER}" ref="{PLACE_TO_METADATA}">{PLACE_SENT_TO}</placeName>', f'')

        encoded_letter = self.xml_template

        return encoded_letter

    def create_letter(self):
        # read in xml template as string
        with open(os.path.join(os.getcwd(), '..', 'data','letter_template.xml'), 'r', encoding='utf8') as f:
            xml_file = f.read()

        return xml_file

    def save_letter(self):
        # save xml file to folder ./output
        with open(os.path.join(os.getcwd(), 'output', f'{self.doc_id}.xml'), 'w', encoding='utf8') as f:
            f.write(self.encoded_letter)

def main():

    data = GetData()
    
    for id in data.ids:

        print(f"Processing letter {id}...")
        
        processing = ProcessText(data.method, id, data.transkribus_id)

        print(f"{processing.letter_text}\n")

        ner = NamedEntityRecognition(processing, id, data)

        processed_tests = LLMTextProcessing(data, processing)

        CreateXML(processing.letter_text, id, data, processed_tests)

        # Process letter
        print(f"Letter {id} processed.\n".center(20, '#'))

    print(f"Starting identification of NER using {data.llm}")
    
    llm_identification = LLMIdentification(data)

    print(f"Finished identification of NER. Starting insertion into XML.")

    InsertIdentification(data, llm_identification)

    print(f"Finished. {len(data.ids)} letters have been processed.")



    





if __name__ == "__main__":
    main()
