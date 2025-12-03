from sentence_transformers import SentenceTransformer
import chromadb

# 埋め込みモデルと Chroma クライアント
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

def simple_search(query: str, top_k: int = 5):
    """
    Chroma DB からクエリに類似した文書を取得
    類似度（距離）順にソートして返す
    """
    query_emb = embed_model.encode([query])[0]

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=top_k,
        include=["documents", "distances"]
    )

    # documents と distances を取得
    docs = results['documents'][0]
    distances = results['distances'][0]

    # 距離が小さい順にソート
    sorted_docs = [doc for _, doc in sorted(zip(distances, docs))]

    return sorted_docs

# テスト実行
if __name__ == "__main__":
    query = "日本で一番高い山は？"
    results = simple_search(query)
    print("検索結果:")
    for doc in results:
        print("-", doc)
