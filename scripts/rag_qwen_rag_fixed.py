import requests
from sentence_transformers import SentenceTransformer
import chromadb

# --- Chroma DB セットアップ ---
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

def simple_search(query, n_results=3):
    """
    Chroma DB で検索して文書を取得
    """
    query_emb = embed_model.encode([query])[0]
    results = collection.query(query_embeddings=[query_emb], n_results=n_results)
    return results['documents'][0]

# --- Qwen サーバー設定 ---
QWEN_URL = "http://10.23.130.252:1234/generate"  # LM Studio の Qwen 1.5B
MAX_TOKENS = 128

def generate_with_qwen(prompt):
    """
    LM Studio Qwen サーバーにリクエストしてテキスト生成
    """
    payload = {
        "prompt": prompt,
        "max_new_tokens": MAX_TOKENS
    }
    response = requests.post(QWEN_URL, json=payload)
    response.raise_for_status()
    data = response.json()

    # LM Studio のレスポンス形式に対応
    # 例: {"results":[{"text":"生成テキスト"}]}
    if "results" in data and len(data["results"]) > 0:
        return data["results"][0].get("text", "")
    return ""

if __name__ == "__main__":
    query = "日本で一番高い山は？"
    
    # --- 検索 ---
    docs = simple_search(query)
    print("検索結果:")
    for d in docs:
        print("-", d)
    
    # --- プロンプト作成 ---
    prompt = "以下の文書を参考に質問に答えてください。\n"
    for doc in docs:
        prompt += f"- {doc}\n"
    prompt += f"\n質問: {query}\n回答:"

    # --- Qwen で生成 ---
    try:
        answer = generate_with_qwen(prompt)
        print("\n=== Qwen の回答 ===")
        print(answer)
    except Exception as e:
        print("Qwen サーバーへの接続に失敗:", e)
