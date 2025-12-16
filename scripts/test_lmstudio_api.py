import requests
import json

URL = "http://10.23.130.252:1234/v1/chat/completions"  # ← これ！

payload = {
    "model": "qwen2.5-7b-instruct",
    "messages": [
        {"role": "user", "content": "こんにちは、元気？"}
    ],
    "temperature": 0.7
}

headers = {"Content-Type": "application/json"}

try:
    res = requests.post(URL, data=json.dumps(payload), headers=headers, timeout=10)
    print("Status:", res.status_code)
    print("Response:", res.json())
except Exception as e:
    print("ERROR:", e)
