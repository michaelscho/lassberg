from openai import OpenAI
from sentence_transformers import SentenceTransformer
import chromadb
import rag_config

client = OpenAI(api_key=rag_config.API_KEY)
MODEL_NAME = "all-mpnet-base-v2"
JSON_FOLDER = "./json"
CHROMA_DB_DIR = "./chroma"
COLLECTION_NAME = "lassberg-letters"
model = SentenceTransformer(MODEL_NAME)
# Setup ChromaDB
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_DIR)
collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)

def query(question, top_k=5):
    # Step 1: Embed the question
    q_embedding = model.encode(question).tolist()

    # Step 2: Query ChromaDB
    results = collection.query(
        query_embeddings=[q_embedding],
        n_results=top_k,
        include=["documents", "metadatas"]
    )

    # Step 3: Extract retrieved data
    retrieved_docs = results["documents"][0]
    metadatas = results["metadatas"][0]
    ids = results["ids"][0]

    # Build context string for GPT
    context_chunks = []
    for doc, meta, doc_id in zip(retrieved_docs, metadatas, ids):
        meta_info = f"(ID: {doc_id}, Sender: {meta.get('sender')}, Receiver: {meta.get('receiver')}, Date: {meta.get('date')})"
        context_chunks.append(f"{meta_info}\n{doc}")

    context = "\n---\n".join(context_chunks)

    # Step 4: Compose prompt
    prompt = f"""Answer the question based on the following historical letter excerpts:
    {context}

    **Please indicate the document id in parenthesis**
    ---
    Question: {question}
    Answer:"""

    # Step 5: Get GPT answer
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )

    answer = response.choices[0].message.content

    # Step 6: Return structured result
    return {
        "question": question,
        "answer": answer,
        "documents": [
            {
                "id": doc_id,
                "text": doc,
                "metadata": meta
            }
            for doc_id, doc, meta in zip(ids, retrieved_docs, metadatas)
        ]
    }


result = query(input("Enter your question: "))

print("\n📚 Retrieved Chunks:")
for doc in result["documents"]:
    print(f"\nID: {doc['id']}")
    print(f"Metadata: {doc['metadata']}")
    print(f"Text:\n{doc['text']}")

print("\n📜 Answer:")
print(result["answer"])