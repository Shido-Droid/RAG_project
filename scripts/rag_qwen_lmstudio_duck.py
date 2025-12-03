import requests
from sentence_transformers import SentenceTransformer
import chromadb

# Chroma DB の準備
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

# DuckDuckGo 検索
def duckduckgo_search(query, max_results=3):
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

    if 'AbstractText' in data and data['AbstractText']:
        results.append(data['AbstractText'])
    for topic in data.get('RelatedTopics', [])[:max_results]:
        if 'Text' in topic:
            results.append(topic['Text'])
    return results

# Chroma DB から検索
def chroma_search(query, n_results=3):
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=n_results)
    return results['documents'][0]

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

    # 文脈を統合
    context = "\n".join(chroma_docs + web_docs)

    prompt = f"次の文脈に基づいて答えてください:\n{context}\n\n質問: {query}"
    answer = query_qwen(prompt)

    print("\n検索結果:")
    for doc in chroma_docs + web_docs:
        print("-", doc)
    print("\n=== Qwen の回答 ===")
    print(answer)
