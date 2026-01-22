
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from rag_app.core import detect_search_intent, process_question

def test_greeting_intent():
    question = "こんにちは"
    print(f"Testing question: '{question}'")
    
    # 1. Check Intent Detection
    intent = detect_search_intent(question)
    print(f"Detected Intent: {intent}")
    
    if intent != "other":
        print("FAIL: Intent should be 'other'")
        return

    # 2. Check Process Question (Should have empty sources)
    print("Running process_question...")
    result = process_question(question)
    
    sources = result.get("sources", [])
    answer = result.get("answer", "")
    
    print(f"Sources count: {len(sources)}")
    print(f"Answer prefix: {answer[:50]}...")
    
    if len(sources) == 0:
        print("SUCCESS: Sources are empty (Search skipped)")
    else:
        print("FAIL: Sources found (Search was NOT skipped)")
        print("Sources:", sources)

if __name__ == "__main__":
    test_greeting_intent()
