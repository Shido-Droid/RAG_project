import chromadb
import pprint
import os

# ChromaDBクライアントの初期化
try:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "chroma_db")
    client = chromadb.PersistentClient(path=db_path)
except Exception as e:
    print(f"ChromaDBクライアントの初期化中にエラーが発生しました: {e}")
    exit()

# コレクション名
COLLECTION_NAME = "rag_docs_e5"

try:
    # コレクションを取得
    print(f"コレクション '{COLLECTION_NAME}' を確認中...")
    collection = client.get_collection(COLLECTION_NAME)
    
    count = collection.count()
    print(f"登録ドキュメント数: {count}")
    
    if count > 0:
        print("\n=== サンプルデータ (Top 5) ===")
        # データ取得 (ID, Metadata, Document)
        data = collection.get(limit=5)
        
        for i in range(len(data['ids'])):
            print(f"\n[ID]: {data['ids'][i]}")
            print(f"[Meta]: {data['metadatas'][i]}")
            doc_text = data['documents'][i] or ""
            print(f"[Text]: {doc_text[:100].replace(chr(10), ' ')}...")
    else:
        print("ドキュメントが登録されていません。")

except ValueError:
    print(f"コレクション '{COLLECTION_NAME}' が見つかりません。")
    print(f"存在するコレクション: {[c.name for c in client.list_collections()]}")

except Exception as e:
    print(f"エラーが発生しました: {e}")