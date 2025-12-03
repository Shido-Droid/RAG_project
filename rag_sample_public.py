# rag_sample_public.py
from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np

# ======================================
# 1. Embedding モデルロード（公開モデルを使用）
# ======================================
print("Embedding モデルをロード中...")
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("モデルロード完了！")

# ======================================
# 2. Chroma クライアント & コレクション作成
# ======================================
client = chromadb.PersistentClient(path="./chroma_db")  # 永続化ディレクトリ
collection = client.create_collection("rag_docs")
print("Chroma コレクション作成完了！")

# ======================================
# 3. テスト文書をベクトル化 & Chroma に登録
# ======================================
docs = [
    "今日は天気がいいですね。",
    "明日は雨が降る予定です。",
    "富士山は日本で一番高い山です。"
]

print(f"{len(docs)} 件の文書をベクトル化します...")
embeddings = embed_model.encode(docs)
print("ベクトル化完了！")

for i, emb in enumerate(embeddings):
    collection.add(
        ids=[str(i)],
        embeddings=[emb.tolist()],
        metadatas=[{"text": docs[i]}],
        documents=[docs[i]]
    )
print("Chroma に文書登録完了！")

# ======================================
# 4. Chroma で類似検索
# ======================================
query_text = "日本で一番高い山は？"
query_emb = embed_model.encode([query_text])

results = collection.query(
    query_embeddings=[query_emb[0]],
    n_results=2
)

print("検索結果:")
for doc, meta in zip(results['documents'][0], results['metadatas'][0]):
    print("-", doc)
