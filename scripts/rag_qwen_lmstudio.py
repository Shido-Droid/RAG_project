import requests
from sentence_transformers import SentenceTransformer
import chromadb

# --- Chroma DB セットアップ ---
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

# --- LM Studio Qwen サーバー ---
LMSTUDIO_URL = "http://10.23.130.252:1234/v1/chat/complections"
MODEL_NAME = "codeqwen1.5-7b-chat"

# --- 検索関数 ---
def search_docs(query, n_results=3):
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=n_results)
    docs = results["documents"][0]
    return docs

# --- Qwen 1.5B に質問する関数 ---
def ask_qwen(user_prompt):
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": False
    }

    try:
        response = requests.post(LMSTUDIO_URL, json=payload)
        response.raise_for_status()
        data = response.json()
        # LM Studio のレスポンスから回答を抽出
        answer = data["choices"][0]["message"]["content"]
        return answer
    except Exception as e:
        return f"Qwen サーバーへの接続に失敗: {e}"

# --- メイン ---
def main():
    query = input("質問を入力してください: ")
    docs = search_docs(query)

    print("\n検索結果:")
    for doc in docs:
        print("-", doc)

    # 検索結果をまとめて Qwen に送信
    context_text = "\n".join(docs)
    user_prompt = f"以下の文書を参考に質問に答えてください:\n{context_text}\n\n質問: {query}"

    answer = ask_qwen(user_prompt)
    print("\n=== Qwen の回答 ===")
    print(answer)

if __name__ == "__main__":
    main()
