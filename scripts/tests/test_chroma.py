from sentence_transformers import SentenceTransformer
import chromadb

embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

docs = ["今日は天気がいい", "明日は雨の予定", "富士山は高い"]
embeddings = embed_model.encode(docs)

for i, emb in enumerate(embeddings):
    collection.add(
        ids=[str(i)],
        embeddings=[emb.tolist()],
        metadatas=[{"text": docs[i]}],
        documents=[docs[i]]
    )

print("文書登録完了")
