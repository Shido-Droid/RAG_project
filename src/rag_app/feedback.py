import json
import os
import datetime
from .config import PROJECT_ROOT
from .utils import log

FEEDBACK_FILE = os.path.join(PROJECT_ROOT, "evaluation_log.jsonl")

def log_feedback(
    question: str, 
    answer: str, 
    rating: str, # "good" or "bad"
    comment: str = "",
    intent: str = "unknown",
    sources: list = []
):
    """
    Log user feedback to evaluation_log.jsonl
    """
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "question": question,
        "intent": intent,
        "answer": answer,
        "rating": rating, # good / bad
        "comment": comment,
        "sources_count": len(sources)
    }
    
    try:
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        log(f"[Feedback] Logged {rating} feedback for intent={intent}")
    except Exception as e:
        log(f"[Feedback] Error logging feedback: {e}")
