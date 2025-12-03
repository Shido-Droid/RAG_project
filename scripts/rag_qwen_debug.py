import requests

QWEN_URL = "http://10.23.130.252:1234/generate"

prompt = "日本で一番高い山は？"

payload = {
    "prompt": prompt,
    "max_new_tokens": 128
}

try:
    response = requests.post(QWEN_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    print("DEBUG: LM Studio response:", data)
except Exception as e:
    print("Qwen サーバーへの接続に失敗:", e)
