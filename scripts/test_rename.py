import requests
import os
import sys

BASE_URL = "http://localhost:8000"
TEST_FILENAME = "test_rename_check.txt"

def cleanup_remote(filename):
    """サーバー上のファイルを削除して初期状態にする"""
    url = f"{BASE_URL}/api/delete_document"
    try:
        # 削除APIを叩く（ファイルが存在しなくてもエラーで止まらないようにする）
        requests.post(url, json={"filename": filename})
    except Exception:
        pass

def create_local_file():
    """テスト用のローカルファイルを作成"""
    with open(TEST_FILENAME, "w", encoding="utf-8") as f:
        f.write("これはリネーム機能のテスト用ファイルです。\n重複アップロード時にファイル名が変更されるか確認します。")
    print(f"[Setup] Created local file: {TEST_FILENAME}")

def remove_local_file():
    """テスト用のローカルファイルを削除"""
    if os.path.exists(TEST_FILENAME):
        os.remove(TEST_FILENAME)
        print(f"[Cleanup] Removed local file: {TEST_FILENAME}")

def upload_and_check(expected_name):
    """ファイルをアップロードして、期待されるファイル名で保存されたか確認"""
    url = f"{BASE_URL}/api/upload"
    try:
        with open(TEST_FILENAME, "rb") as f:
            files = {"file": (TEST_FILENAME, f, "text/plain")}
            # autorename=True はデフォルト
            resp = requests.post(url, files=files)
        
        if resp.status_code == 200:
            data = resp.json()
            msg = data.get("message", "")
            print(f"   Response: {msg}")
            
            # サーバーのメッセージ "Imported {filename} ..." をチェック
            if f"Imported {expected_name}" in msg:
                print(f"   ✅ Success: Saved as '{expected_name}'")
                return True
            else:
                print(f"   ❌ Fail: Expected '{expected_name}' but got something else.")
                return False
        else:
            print(f"   ❌ Error: HTTP {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def main():
    print("=== リネーム機能テスト開始 ===")
    
    # 1. 事前クリーンアップ (DBからテスト用ファイルを削除)
    base, ext = os.path.splitext(TEST_FILENAME)
    targets = [TEST_FILENAME, f"{base}_v2{ext}", f"{base}_v3{ext}"]
    print("Cleaning up old test data on server...")
    for t in targets:
        cleanup_remote(t)

    # 2. テスト実行
    create_local_file()
    try:
        print("\n[1st Upload] (Expect: Original name)")
        upload_and_check(TEST_FILENAME)

        print("\n[2nd Upload] (Expect: _v2)")
        upload_and_check(f"{base}_v2{ext}")

        print("\n[3rd Upload] (Expect: _v3)")
        upload_and_check(f"{base}_v3{ext}")

    finally:
        remove_local_file()
        print("\n=== テスト終了 ===")

if __name__ == "__main__":
    main()