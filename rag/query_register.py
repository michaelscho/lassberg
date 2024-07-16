import json
from langchain.llms import Ollama
from langchain.prompts import ChatPromptTemplate
from langchain.embeddings import OllamaEmbeddings
from langchain.vectorstores import Chroma

class LocalLlama3Chatbot:
    def __init__(self, model_name, vector_dir, embedding_model):
        self.model_name = model_name
        self.vector_dir = vector_dir
        self.embedding_model = embedding_model

    def load_base_assets(self):
        self.llm = Ollama(model=self.model_name)
        self.embedding = OllamaEmbeddings(model=self.embedding_model)
        self.db = Chroma(collection_name="lassberg-register", embedding_function=self.embedding, persist_directory=self.vector_dir)

    def fetch_metadata(self, user_query):
        user_query = f'Extract metadata for the name: {user_query}'
        response = self.llm.invoke(user_query)
        print("Response from fetching data" + response)
        try:
            metadata = json.loads(response)
            return metadata
        except json.JSONDecodeError:
            raise ValueError("Failed to decode metadata from LLM response")

    def model_call(self, user_query, metadata):
        name = metadata['name']
        xml_id = metadata['xml_id']
        search_filter = {'persName': {'#text': name}}
        context = self.db.retrieve(search_filter, k=1)  # Assuming retrieve is the correct method to fetch context
        print(context)
        answer = self.llm.invoke(f"Context: {context} Query: {user_query}")
        return answer

if __name__ == '__main__':
    chatbot = LocalLlama3Chatbot('llama3', './db', 'llama3')
    chatbot.load_base_assets()
    while True:
        query = input("Query (type 'exit' to stop): ")
        if query.lower() == 'exit':
            break
        metadata = chatbot.fetch_metadata(query)
        output = chatbot.model_call(query, metadata)
        print("Output: ", output)
    print("End of Conversation")
