from langchain_community.document_loaders import JSONLoader
from langchain.embeddings.sentence_transformer import SentenceTransformerEmbeddings
from langchain_community.vectorstores import Chroma

#embedding_function = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

loader = JSONLoader(file_path="./prize.json", jq_schema=".prizes[]", text_content=False)
documents = loader.load()
print(documents)
#db = Chroma.from_documents(documents, embedding_function)
#query = "What year did albert einstein win the nobel prize?"
#docs = db.similarity_search(query)
#print(docs[0].page_content)