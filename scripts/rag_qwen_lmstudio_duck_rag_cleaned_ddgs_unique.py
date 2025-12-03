# scripts/rag_qwen_lmstudio_duck_rag_cleaned_ddgs_unique.py
from sentence_transformers import SentenceTransformer
import chromadb
from duckduckgo_search import DDGS
import requests
import json

# Chroma DBセットアップ
embed_model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("rag_docs")

def remove_duplicate_docs():
    """Chroma DB の重複文書を削除"""
    docs = collection.get()["documents"]
    ids = collection.get()["ids"]
    seen = set()
    keep_ids = []
    for i, doc in enumerate(docs):
        if doc not in seen:
            seen.add(doc)
            keep_ids.append(ids[i])
    if len(keep_ids) < len(ids):
        collection.delete(where={"id": {"$nin": keep_ids}})

def search_chroma(query, n_results=3):
    query_emb = embed_model.encode([query])
    results = collection.query(query_embeddings=[query_emb[0]], n_results=n_results)
    # 重複除去
    unique_docs = list(dict.fromkeys(results['documents'][0]))
    return unique_docs

def search_duckduckgo(query, max_results=3):
    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, region='wt-wt', safesearch='Off', timelimit='d', max_results=max_results):
            results.append(r['body'])
    # 重複除去
    return list(dict.fromkeys(results))[:max_results]

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
