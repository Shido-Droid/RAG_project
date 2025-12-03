from sentence_transformers import SentenceTransformer
import chromadb
from ddgs import DDGS   # ← 正しい
import requests
import json

# -----------------------------
# Chroma DB セットアップ
# -----------------------------
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

# -----------------------------
# Chroma検索（重複除去）
# -----------------------------
def search_chroma(query, n_results=3):
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=n_results)
    docs = results['documents'][0]
    unique_docs = list(dict.fromkeys(docs))
    return unique_docs[:n_results]

# -----------------------------
# DuckDuckGo検索（ddgs 新パッケージ対応）
# -----------------------------
def search_duckduckgo(query, max_results=3):
    results = []
    seen = set()

    # ddgs の正しい使い方
    with DDGS() as ddgs:
        for r in ddgs.text(query, region="jp-jp", safesearch="off", timelimit="d", max_results=20):
            text = r.get("body", "")
            if text and text not in seen:
                seen.add(text)
                results.append(text)

            if len(results) >= max_results:
                break

    return results

# -----------------------------
# Qwen問い合わせ
# -----------------------------
def query_qwen(prompt, context, lmstudio_url="http://10.23.130.252:1234/v1/chat/completions"):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {prompt}"}
    ]
    data = {
        "model": "codeqwen1.5-7b-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 200,
        "stream": False
    }
    response = requests.post(lmstudio_url, headers={"Content-Type": "application/json"}, data=json.dumps(data))
    res_json = response.json()
    return res_json['choices'][0]['message']['content']


# -----------------------------
# メイン処理
# -----------------------------
if __name__ == "__main__":
    question = input("質問を入力してください: ")

    # Chroma
    chroma_results = search_chroma(question, n_results=3)
    print("Chroma DB検索結果:")
    for r in chroma_results:
        print("-", r)

    # DuckDuckGo
    duck_results = search_duckduckgo(question, max_results=3)
    print("\nDuckDuckGo検索結果（上位3件）:")
    for r in duck_results:
        print("-", r)

    # LLM へ渡す
    context_text = "\n".join(chroma_results + duck_results)

    try:
        answer = query_qwen(question, context_text)
        print("\n=== Qwen の回答 ===")
        print(answer)
    except Exception as e:
        print("Qwen サーバーへの接続に失敗:", e)
