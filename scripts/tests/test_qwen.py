import requests

query = "日本で一番高い山は？"
retrieved_docs = ["富士山は高い", "明日は雨の予定"]  # Step2の結果を想定

prompt = f"以下の文書を参考に質問に答えてください:\n{retrieved_docs}\n質問: {query}"

response = requests.post(
    "http://<QWEN_SERVER_IP>:<PORT>/generate",
    json={"prompt": prompt, "max_new_tokens": 128}
)

print("Qwen 14B の回答:")
print(response.json())
