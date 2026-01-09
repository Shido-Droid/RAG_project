import requests
import json
import sys
import os

BASE_URL = "http://localhost:8000"

def test_upload(file_path):
    url = f"{BASE_URL}/api/upload"
    print(f"Uploading {file_path} to {url}...")
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return False

    try:
        with open(file_path, 'rb') as f:
            # ファイル名はパスから取得、MIMEタイプは簡易的にPDFとする（サーバー側で拡張子判定されるため）
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            response = requests.post(url, files=files)
        
        response.raise_for_status()
        result = response.json()
        print(f"Upload success: {result}")
        return True
    except Exception as e:
        print(f"Upload failed: {e}")
        return False

def test_ask(question):
    url = f"{BASE_URL}/api/ask"
    headers = {"Content-Type": "application/json"}
    data = {"question": question}
    
    print(f"\nAsking: {question}")
    
    try:
        response = requests.post(url, headers=headers, json=data, stream=True)
        response.raise_for_status()
        
        print("=== Answer ===")
        full_answer = ""
        sources = []
        
        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8'))
                    if data['type'] == 'answer':
                        print(data['content'], end='', flush=True)
                        full_answer += data['content']
                    elif data['type'] == 'sources':
                        sources = data['content']
                except json.JSONDecodeError:
                    pass
        
        print("\n\n=== Sources ===")
        for s in sources:
            print(f"- {s.get('title', 'No Title')}: {s.get('url', 'No URL')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # 引数がある場合
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # ファイルが存在すればアップロードテスト
        if os.path.isfile(arg):
            if test_upload(arg):
                test_ask("このドキュメントの概要を教えてください")
        # ファイルでなければ、引数をそのまま質問文として送信
        else:
            question = " ".join(sys.argv[1:])
            test_ask(question)
    else:
        test_ask("今日の東京の天気は？")