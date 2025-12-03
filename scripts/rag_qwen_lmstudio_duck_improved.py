import requests
from sentence_transformers import SentenceTransformer
import chromadb
from collections import OrderedDict

# Chroma DB の準備
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

# DuckDuckGo 検索
def duckduckgo_search(query, max_results=5):
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_html": 1,
        "skip_disambig": 1
    }
    res = requests.get(url, params=params)
    data = res.json()
    results = []

    # AbstractText を優先
    if 'AbstractText' in data and data['AbstractText']:
        results.append(data['AbstractText'])

    # RelatedTopics から追加
    for topic in data.get('RelatedTopics', []):
        if 'Text' in topic:
            results.append(topic['Text'])
        if len(results) >= max_results:
            break

    # 重複排除
    results = list(OrderedDict.fromkeys(results))
    return results[:max_results]

# Chroma DB から検索
def chroma_search(query, n_results=5):
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=n_results)
    docs = results['documents'][0]
    # 重複排除
    docs = list(OrderedDict.fromkeys(docs))
    return docs[:n_results]

# Qwen サーバーに送信
def query_qwen(prompt):
    url = "http://10.23.130.252:1234/v1/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "codeqwen1.5-7b-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": False
    }
    res = requests.post(url, json=data, headers=headers)
    res_json = res.json()
    try:
        return res_json['choices'][0]['message']['content']
    except Exception as e:
        return f"Qwen サーバーへの接続に失敗: {e}"

# メイン
if __name__ == "__main__":
    query = input("質問を入力してください: ")

    chroma_docs = chroma_search(query)
    web_docs = duckduckgo_search(query)

    # 文脈を統合（Chroma 優先、Web 補助）
    context_docs = chroma_docs + [doc for doc in web_docs if doc not in chroma_docs]

    # 上位3件のみ使用
    context = "\n".join(context_docs[:3])

    prompt = f"次の文脈に基づいて答えてください:\n{context}\n\n質問: {query}"
    answer = query_qwen(prompt)

    print("\n検索結果（上位3件）:")
    for doc in context_docs[:3]:
        print("-", doc)
    print("\n=== Qwen の回答 ===")
    print(answer)
