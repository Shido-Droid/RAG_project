import requests
from duckduckgo_search import ddg_answers
from sentence_transformers import SentenceTransformer
import chromadb

# Chroma DB セットアップ
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

# Qwen LM Studio サーバー設定
LMSTUDIO_URL = "http://localhost:1234/v1/chat/completions"
MODEL_NAME = "codeqwen1.5-7b-chat"

def search_chroma(query, top_k=3):
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=top_k)
    docs = results['documents'][0] if results['documents'] else []
    return docs

def search_duckduckgo(query, top_k=3):
    results = ddg(query, max_results=top_k)
    docs = [r['body'] if r.get('body') else r['title'] for r in results]
    return docs

def ask_qwen(context_docs, question):
    context_text = "\n".join(context_docs)
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": f"以下の文書を参考に質問に答えてください:\n{context_text}\n\n質問: {question}"}
    ]
    response = requests.post(LMSTUDIO_URL, json={
        "model": MODEL_NAME,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 256,
        "stream": False
    }).json()
    return response['choices'][0]['message']['content']

def main():
    question = input("質問を入力してください: ")
    chroma_docs = search_chroma(question)
    duck_docs = search_duckduckgo(question)
    
    # Chroma DB + DuckDuckGo 結果を結合
    context_docs = chroma_docs + duck_docs
    
    print("検索結果（上位3件ずつ）:")
    for doc in context_docs[:6]:
        print("-", doc)

    answer = ask_qwen(context_docs, question)
    print("\n=== Qwen の回答 ===")
    print(answer)

if __name__ == "__main__":
    main()
