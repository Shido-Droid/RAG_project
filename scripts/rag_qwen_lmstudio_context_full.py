# scripts/rag_qwen_lmstudio_context_full.py
import requests
from sentence_transformers import SentenceTransformer
import chromadb

def main():
    # 1. Embedding モデルと Chroma DB 初期化
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection("rag_docs")

    # 2. ユーザー入力
    user_question = input("質問を入力してください: ")

    # 3. 質問のベクトル化
    query_emb = embed_model.encode([user_question])

    # 4. Chroma DB 検索
    results = collection.query(query_embeddings=[query_emb[0]], n_results=5)
    documents = results['documents'][0]

    print("\n検索結果:")
    for doc in documents:
        print("-", doc)

    # 5. 文書をまとめる
    context_text = "\n".join([f"{i+1}. {doc}" for i, doc in enumerate(documents)])

    # 6. Qwen へ送るプロンプト作成
    prompt = f"""
次の情報を参考に質問に答えてください:

{context_text}

質問: {user_question}
回答:
"""

    # 7. LM Studio（Qwen 1.5-7B）へ送信
    try:
        response = requests.post(
            "http://10.23.130.252:1234/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "codeqwen1.5-7b-chat",
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 256
            },
        )
        data = response.json()
        answer = data['choices'][0]['message']['content']
        print("\n=== Qwen の回答 ===")
        print(answer)

    except Exception as e:
        print("Qwen サーバーへの接続に失敗:", e)

if __name__ == "__main__":
    main()
