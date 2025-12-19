import os
import sys
import json
import random

# scriptsディレクトリをパスに追加してモジュールをインポートできるようにする
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 既存のRAG設定とLLMクライアントを再利用
try:
    from rag_qwen_ultimate import collection, lmstudio_chat
except ImportError:
    print("エラー: rag_qwen_ultimate.py が見つかりません。scriptsディレクトリ内で実行するか、パスを確認してください。")
    sys.exit(1)

def generate_qa_pairs(num_pairs=5):
    print(f"ChromaDBからドキュメントを取得中...")
    
    # ドキュメント数が非常に多い場合は全件取得は避けるべきですが、
    # テストデータ生成用として簡易的に全件IDを取得します
    try:
        # IDとメタデータのみ先に取得して軽量化
        data = collection.get(include=['metadatas'])
        ids = data['ids']
        metadatas = data['metadatas']
    except Exception as e:
        print(f"ChromaDBへのアクセスに失敗しました: {e}")
        return

    total_docs = len(ids)
    print(f"データベース内のドキュメント総数: {total_docs}")

    if total_docs == 0:
        print("ドキュメントが見つかりません。まずはRAGにドキュメントを登録してください。")
        return

    # 指定数だけランダムにサンプリング
    num_pairs = min(num_pairs, total_docs)
    indices = random.sample(range(total_docs), num_pairs)
    
    # 選択されたIDのドキュメント本文を取得
    selected_ids = [ids[i] for i in indices]
    selected_data = collection.get(ids=selected_ids, include=['documents', 'metadatas'])
    documents = selected_data['documents']
    metadatas = selected_data['metadatas']

    qa_pairs = []

    print(f"{num_pairs}件のテスト用Q&Aを生成します...")

    for i, doc_text in enumerate(documents):
        meta = metadatas[i] if metadatas and metadatas[i] else {}
        source = meta.get('title') or meta.get('url') or "Unknown Source"

        print(f"[{i+1}/{num_pairs}] 生成中 (Source: {source})...")

        # LLMに質問と回答を作成させるプロンプト
        prompt = f"""
以下のテキストは、RAGシステムの検索対象となるドキュメントの一部です。
このテキストの内容を正しく理解しているかテストするための「質問」と、その「正解」を作成してください。

【制約事項】
1. 質問は、このテキストの情報だけで答えられるものにしてください。
2. 「このテキストによると」といった前置きは不要です。自然な質問にしてください。
3. 出力は必ず以下のJSON形式のみにしてください。Markdownのコードブロック(```json)は含めないでください。
{{
  "question": "生成された質問",
  "answer": "テキストに基づいた正解"
}}

【テキスト】
{doc_text[:1500]}
"""
        
        try:
            resp = lmstudio_chat(
                messages=[
                    {"role": "system", "content": "あなたはQAデータセット作成アシスタントです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=512
            )
            
            content = resp["choices"][0]["message"]["content"].strip()
            
            # JSON部分を抽出（Markdownコードブロック対策）
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
            
            # クリーニング
            content = content.strip()
            
            qa = json.loads(content)
            qa['source_text_snippet'] = doc_text[:200] + "..."
            qa['source_meta'] = meta
            
            qa_pairs.append(qa)
            print(f"  -> 質問: {qa['question']}")

        except Exception as e:
            print(f"  -> 生成エラー: {e}")
            continue

    # 結果を保存
    output_file = "test_qa_dataset.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(qa_pairs, f, indent=2, ensure_ascii=False)
    
    print(f"\n完了！ {len(qa_pairs)}件のQ&Aペアを {output_file} に保存しました。")

if __name__ == "__main__":
    # コマンドライン引数で生成数を指定可能に (デフォルト5件)
    num = 5
    if len(sys.argv) > 1:
        try:
            num = int(sys.argv[1])
        except ValueError:
            pass
    generate_qa_pairs(num)