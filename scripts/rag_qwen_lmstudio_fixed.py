# scripts/rag_qwen_lmstudio_fixed.py
from sentence_transformers import SentenceTransformer
import chromadb
import requests

# Chroma DB セットアップ
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

# 埋め込みモデル
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

# LM Studio サーバー設定
LMSTUDIO_URL = "http://10.23.130.252:1234/v1/chat/completions"  # 適宜修正
MODEL_NAME = "codeqwen1.5-7b-chat"

def simple_search(query, n_results=5):
    query_emb = embed_model.encode([query])[0]
    results = collection.query(
        query_embeddings=[query_emb],
        n_results=n_results,
        include=["documents", "distances"]
    )
    docs = results['documents'][0]
    return docs

def ask_qwen(context, question):
    prompt = f"以下の文書を参考に質問に答えてください:\n{context}\n質問: {question}"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "RAG モードで回答してください。"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 200
    }

    response = requests.post(LMSTUDIO_URL, json=payload)
    try:
        data = response.json()
        answer = data['choices'][0]['message']['content']
        return answer
    except Exception as e:
        print("Qwen サーバーへの接続に失敗:", e)
        print("DEBUG: LM Studio response:", response.text)
        return ""

def main():
    question = input("質問を入力してください: ")
    retrieved_docs = simple_search(question)
    
    print("\n検索結果:")
    for doc in retrieved_docs:
        print("-", doc)
    
    context = "\n".join(retrieved_docs)
    answer = ask_qwen(context, question)
    
    print("\n=== Qwen の回答 ===")
    print(answer)

if __name__ == "__main__":
    main()
