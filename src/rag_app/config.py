import os
from enum import Enum

# Config
class AnswerMode(Enum):
    NO_CONTEXT = "no_context"
    FAST_FACT = "fast_fact"
    CONTEXT_QA = "context_qa"

LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://10.23.130.252:1234/v1/chat/completions")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen2.5-7b-instruct")
EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"

# Adjust path based on file location: src/rag_app/config.py -> ... -> RAG_project
# os.path.dirname(__file__) -> src/rag_app
# os.path.dirname(...) -> src
# os.path.dirname(...) -> RAG_project
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_PATH = os.path.join(PROJECT_ROOT, "chroma_db")

TOKENS_LIMIT = 1000
CHARS_LIMIT = TOKENS_LIMIT * 3
DDGS_MAX_PER_QUERY = 4
DDGS_USE_NEWS = True
NUM_SEARCH_QUERIES = 2
WEB_DOCS_TO_SUMMARIZE = 2
VERBOSE = True
REQUESTS_TIMEOUT = 8
LM_TIMEOUT = int(os.environ.get("LM_TIMEOUT", "60"))
LM_SHORT_TIMEOUT = int(os.environ.get("LM_SHORT_TIMEOUT", "12"))
LM_RETRIES = int(os.environ.get("LM_RETRIES", "1"))

PRIORITY_DOMAINS = [
    "tabelog.com",
    "retty.me",
    "gnavi.co.jp",
    "hotpepper.jp",
]

BOOST_KEYWORDS = [
    "営業時間",
    "ランチ",
    "口コミ",
    "評価",
    "住所",
    "電話",
]
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"

# Domain Lists
BLACKLIST_DOMAINS = [
    "doubleclick.net",
    "facebook.com",
    "twitter.com",
    "x.com",
    "youtube.com",
    "bing.com",
    "tiktok.com",
    "instagram.com",
]

WHITELIST_DOMAINS = [
    "ai.google.dev",
    "developers.google.com",
    "cloud.google.com",
    "gemini.google.com",
    "openai.com",
    "docs.openai.com",
]
