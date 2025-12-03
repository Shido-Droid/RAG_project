# scripts/rag_qwen_rag_improved.py
import requests
from test_search import embed_model, client

def get_top_documents(query, top_k=5):
    """Chroma DB から上位 top_k 件の文書を取得"""
    collection = client.get_or_create_collection("rag_docs")
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=top_k)
    docs = results['documents'][0]
    return docs

def query_qwen(question, context, server_url="http://10.23.130.252:1234"):
    """LM Studio 上の Qwen に質問 + 文書コンテキストを渡して回答を取得"""
    payload = {
        "model": "codeqwen1.5-7b-chat",
        "messages": [
            {"role": "system", "content": f"以下の文書を参考に質問に答えてください:\n{context}"},
            {"role": "user", "content": question}
        ],
        "temperature": 0.3,
        "max_tokens": 256,
        "stream": False
    }

    try:
        response = requests.post(f"{server_url}/v1/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()
        answer = data['choices'][0]['message']['content']
        return answer
    except Exception as e:
        return f"Qwen サーバーへの接続に失敗: {e}"

def main():
    question = input("質問を入力してください: ")
    docs = get_top_documents(question, top_k=5)
    print("\n検索結果:")
    for doc in docs:
        print("-", doc)
    
    context = "\n".join(docs)
    answer = query_qwen(question, context)
    print("\n=== Qwen の回答 ===")
    print(answer)

if __name__ == "__main__":
    main()
