
import sys
import os
import time

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from rag_app.core import process_question

def test_parallel():
    query = "Google Gemini 最新バージョン"
    print(f"Testing query: '{query}'")
    
    start = time.time()
    try:
        res = process_question(query)
        dur = time.time() - start
        
        print(f"Duration: {dur:.2f}s")
        print(f"Answer len: {len(res.get('answer',''))}")
        print(f"Sources: {len(res.get('sources', []))}")
        
        if res.get('sources'):
            print("First source:", res['sources'][0])
            
    except Exception as e:
        print(f"FAILED with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_parallel()
