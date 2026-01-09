import chromadb
import os
import sys

def main():
    # プロジェクトルートからのパスを想定
    db_path = "./chroma_db"
    
    if not os.path.exists(db_path):
        print(f"エラー: '{db_path}' が見つかりません。")
        print("プロジェクトのルートディレクトリ (RAG_project) で実行してください。")
        return

    print(f"Connecting to ChromaDB at {db_path}...")
    
    try:
        client = chromadb.PersistentClient(path=db_path)
        collection = client.get_collection("rag_docs_e5")
    except Exception as e:
        print(f"DB接続エラー: {e}")
        return

    count = collection.count()
    print(f"\n=== コレクション 'rag_docs' の状態 ===")
    print(f"保存されているドキュメント総数: {count}")

    if count == 0:
        print("データがありません。")
        return

    # 1. 全件のメタデータを取得して一覧表示
    print("\n=== 保存済みドキュメント一覧 (ID / Metadata) ===")
    results = collection.get(include=["metadatas"])
    
    ids = results["ids"]
    metas = results["metadatas"]
    if metas is None:
        metas = []

    # IDでソートして表示（ファイル名などが分かりやすくなるように）
    sorted_indices = sorted(range(len(ids)), key=lambda k: ids[k])

    for i in sorted_indices:
        print(f"ID: {ids[i]:<40} | Metadata: {metas[i]}")

    print("-" * 60)

    # 2. 詳細確認（ID順で最後の3件を表示）
    # PDFなどの新しいデータはIDがファイル名やタイムスタンプを含むため、末尾に来やすい
    print("\n=== 詳細データサンプル (ID順の末尾3件) ===")
    
    target_indices = sorted_indices[-3:]
    target_ids = [ids[i] for i in target_indices]
    
    detailed_results = collection.get(ids=target_ids, include=["documents", "metadatas", "embeddings"])
    
    d_ids = detailed_results["ids"]
    d_docs = detailed_results["documents"]
    d_metas = detailed_results["metadatas"]
    d_embs = detailed_results["embeddings"]
    if d_ids is None:
        d_ids = []
    if d_docs is None:
        d_docs = []
    if d_metas is None:
        d_metas = []

    for i in range(len(d_ids)):
        print("-" * 60)
        print(f"ID       : {d_ids[i]}")
        meta = d_metas[i]
        print(f"Metadata : {meta}")
        
        # 要約の確認
        if meta and "summary" in meta:
            summary = meta["summary"]
            if summary:
                print(f"Summary  : {str(summary)[:100]}...")

        # テキストのプレビュー
        doc_preview = d_docs[i].replace("\n", " ")
        if len(doc_preview) > 100:
            doc_preview = doc_preview[:100] + "..."
        print(f"Text     : {doc_preview}")
        
        # ベクトルの確認
        if d_embs is not None and d_embs[i] is not None:
            emb_len = len(d_embs[i])
            emb_preview = ", ".join([f"{x:.4f}" for x in d_embs[i][:5]])
            print(f"Vector   : {emb_len}次元 [{emb_preview}, ...]")
        else:
            print("Vector   : データなし")
    print("-" * 60)

if __name__ == "__main__":
    main()
