import requests
import sys
import os

# LM Studioの標準的なURL
DEFAULT_BASE_URL = "http://10.23.130.252:1234/v1"

def get_wsl_host_ip():
    """WSL2環境の場合、WindowsホストのIPアドレスを取得する"""
    try:
        with open("/etc/resolv.conf", "r") as f:
            for line in f:
                if line.strip().startswith("nameserver"):
                    ip = line.strip().split()[1]
                    if ip != "127.0.0.53": return ip
    except:
        pass
    return None

def check_server(base_url):
    print(f"接続確認中: {base_url} ... ", end="", flush=True)
    
    # 1. モデル一覧の取得 (サーバーが生きているか確認)
    try:
        response = requests.get(f"{base_url}/models", timeout=3)
        if response.status_code == 200:
            data = response.json()
            models = data.get('data', [])
            print("✅ サーバー接続: OK")
            if models:
                print(f"✅ ロード済みモデル: {models[0]['id']}")
            else:
                print("⚠️ サーバーは起動していますが、モデルがロードされていません。")
            return True
        else:
            print(f"❌ サーバーエラー: ステータスコード {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 接続失敗 (Connection Refused)")
        return False
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def check_lmstudio():
    target_url = DEFAULT_BASE_URL
    
    # 1. localhost チェック
    if not check_server(target_url):
        # 2. WSL2判定 & ホストIPチェック
        host_ip = get_wsl_host_ip()
        if host_ip and host_ip != "127.0.0.1":
            print(f"\n[INFO] localhostへの接続に失敗しました。ホストIPと思われるアドレス ({host_ip}) で再試行します...")
            wsl_url = f"http://{host_ip}:1234/v1"
            if check_server(wsl_url):
                target_url = wsl_url
                print(f"\n💡 ヒント: WSL2から接続するためには、以下の環境変数を設定することをお勧めします:")
                print(f'export LMSTUDIO_URL="{target_url}/chat/completions"')
            else:
                print("\n⚠️ ホストIPへの接続も失敗しました。")
                print("1. LM Studioで 'Start Server' が押されているか確認してください。")
                print("2. Windows側のファイアウォール設定を確認してください。")
                return False
        else:
            return False

    # 3. チャット生成テスト
    print(f"\nチャット生成テストを実行中 ({target_url})...")
    payload = {
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"}
        ],
        "temperature": 0.7,
        "max_tokens": 10,
        "stream": False
    }
    
    try:
        response = requests.post(f"{target_url}/chat/completions", json=payload, timeout=10)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"✅ 生成成功: {content}")
            return True
        else:
            print(f"❌ 生成エラー: {response.text}")
            return False
    except Exception as e:
        print(f"❌ 生成テスト中にエラー: {e}")
        return False

if __name__ == "__main__":
    if check_lmstudio():
        print("\n🎉 LM Studio は正常に動作しています！")
    else:
        print("\n🚫 LM Studio の設定を確認してください。")
        sys.exit(1)