import sys
import os

sys.path.append(os.path.join(os.getcwd(), "src"))

from rag_app.core import process_question

# Simple fake document about a fictional topic to ensure it uses local docs
import chromadb

def setup_test_doc():
    print("--- Setting up test doc ---")
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        # Just ensure collection exists or add something if possible, 
        # but process_question reads from existing. 
        # We rely on existing docs or the fact that document_qa intent works without error.
        # If necessary we can mock search_chroma.
        pass
    except Exception as e:
        print("Chroma setup warn:", e)

def test_qa():
    print("--- E2E QA Test ---")
    
    # query 1: Intent check specific
    q1 = "ドキュメント内検索で、仕様書のバージョンを教えて"
    print(f"\nAsking: {q1}")
    result = process_question(q1)
    print("Answer:", result["answer"])
    print("Sources:", result["sources"])

    # query 2: general
    q2 = "富士山の標高は？"
    print(f"\nAsking: {q2}")
    result = process_question(q2)
    print("Answer:", result["answer"])
    print("Sources:", [s.get('url') for s in result['sources']])

if __name__ == "__main__":
    test_qa()
