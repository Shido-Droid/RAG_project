import sys
import os

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from rag_app.db import add_document_to_kb
from rag_app.utils import log

spec_file = "SPECIFICATION.md"
abs_path = os.path.abspath(spec_file)

if not os.path.exists(abs_path):
    print(f"Error: {spec_file} not found at {abs_path}")
    sys.exit(1)

with open(abs_path, "r", encoding="utf-8") as f:
    text = f.read()

print(f"Read {len(text)} chars from {spec_file}")

metadata = {
    "title": "RAGアプリケーション システム仕様書",
    "summary": "RAGプロジェクトの詳細な仕様書。システム概要、アーキテクチャ、機能仕様、API仕様、UI仕様などが記載されている。",
    "keywords": ["仕様書", "spec", "version", "RAG", "API", "config"]
}

try:
    add_document_to_kb(text, source=spec_file, doc_metadata=metadata)
    print("Successfully indexed SPECIFICATION.md")
except Exception as e:
    print(f"Failed to index: {e}")
