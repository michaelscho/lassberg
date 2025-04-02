from langchain.graphs import Neo4jGraph
from langchain.chains import GraphCypherQAChain
from langchain.chat_models import ChatOpenAI
from langchain_community.llms import Ollama
import os
import rag_config


# Set to False to use Ollama (LLaMA3.1)
USE_OPENAI = True

# Neo4j Configuration
graph = Neo4jGraph(
    url="bolt://localhost:7687",
    username=rag_config.NEO4J_USER,
    password=rag_config.NEO4J_PW
)

# print out db-schema
print("Graph Schema:")
print(graph.schema)

# LLM Setup

if USE_OPENAI:
    os.environ["OPENAI_API_KEY"] = rag_config.API_KEY
    llm = ChatOpenAI(model="gpt-4", temperature=0)
    print("Using OpenAI GPT-4")
else:
    llm = Ollama(model="llama3.1", temperature=0.1)
    print("Using LLaMA 3.1 via Ollama")

# LangChain Chain
chain = GraphCypherQAChain.from_llm(llm, graph=graph, verbose=True)

# Query
question = input("Enter query: ")
response = chain.run(question)

print("Answer: ")
print(response)
