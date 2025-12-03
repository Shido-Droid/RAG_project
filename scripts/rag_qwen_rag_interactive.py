from test_search import embed_model, client
import requests

def simple_search(query, n_results=5):
    collection = client.get_or_create_collection("rag_docs")
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=n_results)

    # 検索結果をユニーク化
    docs = []
    seen = set()
    for doc in results['documents'][0]:
        if doc not in seen:
            seen.add(doc)
            docs.append(doc)
    return docs

def ask_qwen(prompt, context_docs, chat_history=None, server_url="http://10.23.130.252:1234"):
    # 文書をまとめて context として渡す（長すぎる場合は先頭512文字まで）
    context_text = "\n".join([doc[:512] for doc in context_docs])
    
    # システムメッセージで文脈を維持
    messages = [{"role": "system", "content": "以下の文書を参考にして質問に答えてください:\n" + context_text}]
    
    # 過去のやり取りを追加
    if chat_history:
        messages.extend(chat_history)
    
    # 現在の質問を追加
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": "codeqwen1.5-7b-chat",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 256,
        "stream": False
    }

    response = requests.post(f"{server_url}/v1/chat/completions", json=payload)
    data = response.json()

    try:
        answer = data['choices'][0]['message']['content']
    except KeyError:
        answer = f"Qwen サーバーへの接続に失敗: {data}"
    return answer

if __name__ == "__main__":
    chat_history = []
    while True:
        query = input("\n質問を入力してください（終了するには exit と入力）: ")
        if query.lower() == "exit":
            break

        docs = simple_search(query)
        print("\n検索結果:")
        for d in docs:
            print("-", d)

        answer = ask_qwen(query, docs, chat_history)
        print("\n=== Qwen の回答 ===")
        print(answer)

        # 質問と回答を履歴に追加
        chat_history.append({"role": "user", "content": query})
        chat_history.append({"role": "assistant", "content": answer})
