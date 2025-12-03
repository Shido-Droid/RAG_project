from sentence_transformers import SentenceTransformer
import chromadb

# 埋め込みモデル
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Chroma クライアント
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

def simple_search(query, n_results=3):
    """
    query: 検索クエリ
    n_results: 返す件数
    """
    # クエリをベクトル化
    query_emb = embed_model.encode([query])[0]
    
    # Chroma に検索
    results = collection.query(query_embeddings=[query_emb], n_results=n_results)
    
    # 文書を取得
    return results['documents'][0]

if __name__ == "__main__":
    query = "日本で一番高い山は？"
    results = simple_search(query)
    
    print("検索結果:")
    for r in results:
        print("-", r)
