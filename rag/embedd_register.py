import os, xmltodict, json, subprocess

from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate


class embedd_registers:
    def __init__(self, embedding_model, vectorstore):
        self.embeddings = embedding_model
        self.vectorstore = vectorstore
        self.register_dir = os.path.join(os.getcwd(),"..","data","register")
        self.dict = self.create_dict_from_data()

    def create_dict(self, type):
        with open(os.path.join(self.register_dir,f'lassberg-{type}.xml'), 'r', encoding='utf8') as file:
            file_contents = file.read()
        o = xmltodict.parse(file_contents)
        if type == 'persons':
            elements = o['TEI']['text']['body']['div']['listPerson']['person']
            element_type = 'person'
        elif type == 'places':
            elements = o['TEI']['text']['body']['listPlace']['place']
            element_type = 'place'
        elif type == 'literature':
            elements = o['TEI']['text']['body']['listBibl']['bibl']
            element_type = 'literature'
        for element in elements:
            element['element_type'] = element_type
        print(elements[0])
        return elements

    def create_dict_from_data(self):
        dict = self.create_dict('persons') + self.create_dict('places') + self.create_dict('literature')
        cleaned_dict = []
        for element in dict:
            cleaned_element = {}
            try:
                element['persName'].pop('@type', None)
                element['persName'] = element['persName']['#text']
                element['birth'] = element['birth']['@when']
                element['ref'] = element['ref']['@target']
            
            except Exception as e:
                print("Error")
                print(e)

            try:
                text = element['idno'].pop('#text')
                element['idno'] = text
            
            except Exception as e:
                print("Error")
                print(e)

            try:
                text = element['placeName'].pop('#text')
                element['placeName'] = text
                text = element['desc'].pop('#text')
                element['desc'] = text
            
            except Exception as e:
                print("Error")
                print(e)

            for key, value in element.items():
                if isinstance(value, str):
                    cleaned_value = ' '.join(value.split())
                    cleaned_element[key] = cleaned_value
                else:
                    cleaned_element[key] = value
            cleaned_dict.append(cleaned_element)
            
        
        cleaned_dict = {"register_items": cleaned_dict}

        return cleaned_dict



    def pull_model_to_ollama(model_name):
        command = ["ollama", "pull", model_name]
        try:
            # Execute the command
            result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            # Print the standard output and error
            print("Output:\n", result.stdout)
            print("Error (if any):\n", result.stderr)
            if result.stderr:
                return False
            else:
                return True
        except subprocess.CalledProcessError as e:
            # Handle errors in the command execution
            print(f"An error occurred while pulling the model '{model_name}':")
            print("Return code:", e.returncode)
            print("Output:\n", e.output)
            print("Error:\n", e.stderr)

    def load_embeddings(self):
        try:
        # find all the llama3 models here - https://ollama.com/library/llama3:8b
        # we  are using the default connection and parameters for ollama emeddings
            self.embeddings = OllamaEmbeddings(model=self.embeddings)
        except:
            # if facing an error loading the model, we are trying to download the 
            # model
            model_check = self.pull_model_to_ollama(self.embeddings)
            # if True - retry to load embeddings
            if model_check:
                self.embeddings = OllamaEmbeddings(model=self.embeddings)
            # if False - raise error mentioning unsupported Ollama model
            else:
                print("Unsupported Ollama model, please check the model name")  

    def embed_and_store(self, register_data):
    # we are going to use the ollama embeddings with Chroma vector store only
        if self.vectorstore=='chroma':
            try:
                # default methodis get_or_create collection, so if the name already
                # exists this will append and not overwrite that content
                self.vectorstore = Chroma(collection_name="lassberg-register", 
                                        embedding_function=self.embeddings,
                                        persist_directory="./db")
            except Exception as e:
                print(e)

        # iterating through the prepared documents
        for element in register_data:
            # fetching the metadata and replicating for the document list length
            self.vectorstore.add_texts(texts = element)
        print("The documents have been embedded and stored in the vector database")

    
    

    
if __name__=='__main__':
    agent = embedd_registers("llama3", "chroma")
    register_data = agent.dict
    json.dump(register_data, open("register_data.json", "w"))
    agent.load_embeddings()
    agent.embed_and_store(register_data)











