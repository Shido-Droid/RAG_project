from sentence_transformers import SentenceTransformer
import chromadb
import requests

# ─────────────────────────────
# Step1: Chroma のセットアップ
# ─────────────────────────────
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# Chroma PersistentClient を使用
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

# ─────────────────────────────
# Step2: 検索クエリ
# ─────────────────────────────
query = "日本で一番高い山は？"
query_emb = embed_model.encode([query])

# 類似文書を上位2件取得
results = collection.query(
    query_embeddings=[query_emb[0]],
    n_results=2
)

retrieved_docs = results['documents'][0]
print("検索で取得した文書:")
for doc in retrieved_docs:
    print("-", doc)

# ─────────────────────────────
# Step3: Qwen 7B へ送信
# ─────────────────────────────
prompt = f"以下の文書を参考に質問に答えてください:\n{retrieved_docs}\n質問: {query}"

# Qwen 7B サーバー情報
QWEN_SERVER_IP = "10.23.130.24"  # サーバーの IP
PORT = 8000                       # サーバーのポート

url = f"http://{QWEN_SERVER_IP}:{PORT}/generate"

try:
    response = requests.post(
        url,
        json={
            "prompt": prompt,
            "max_new_tokens": 128
        }
    )
    print("\nQwen 7B の回答:")
    print(response.json())
except Exception as e:
    print("Qwen 7B サーバーへの接続に失敗:", e)
