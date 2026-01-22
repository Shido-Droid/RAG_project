import sys
import os

# Ensure src is in python path
sys.path.append(os.path.join(os.getcwd(), "src"))

from rag_app.core import detect_search_intent

test_queries = [
    "ドキュメント内検索をしてほしい",
    "このドキュメントについて",
    "RAGの仕様書を見せて",
    "アップロードしたファイルの内容",
    "ドキュメント検索",
    "資料を要約して"
]

print("--- Intent Detection Test ---")
for q in test_queries:
    intent = detect_search_intent(q)
    print(f"Query: '{q}' -> Intent: {intent}")
