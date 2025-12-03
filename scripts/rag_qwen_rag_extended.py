from test_search import embed_model, client
import requests

collection = client.get_or_create_collection("rag_docs")

def retrieve(query, top_k=5):
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=top_k)
    return results['documents'][0]

def ask_qwen(prompt):
    url = "http://10.23.130.252:1234/v1/chat/completions"  # LM Studio Qwen サーバー
    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "codeqwen1.5-7b-chat",
        "messages": [
            {"role": "system", "content": "Use the retrieved documents to answer accurately."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 256,
        "stream": False
    }
    response = requests.post(url, json=payload).json()
    return response['choices'][0]['message']['content']

if __name__ == "__main__":
    query = input("質問を入力してください: ")
    docs = retrieve(query)
    print("\n検索結果:")
    for doc in docs:
        print("-", doc)

    context = "\n".join(docs)
    answer = ask_qwen(f"以下の文書を参考にして質問に答えてください:\n{context}\n\n質問: {query}")
    print("\n=== Qwen の回答 ===")
    print(answer)
