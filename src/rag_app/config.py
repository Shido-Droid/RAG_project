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

# Hybrid Scoring & Reranking
HYBRID_ALPHA_DEFAULT = 0.4  # Weight for heuristic score (0.0 - 1.0)
HYBRID_ALPHA_BY_INTENT = {
    "local_search": 0.6,    # Heuristic (domain/features) is very important
    "news": 0.5,           # Balance heuristic (recency) and vector
    "weather": 0.7,        # Authority is paramount
    "spec": 0.4,          # Technical details need vector match but authority helps
    "informational": 0.3, # Vector relevance is king
    "document_qa": 0.2,   # Mostly vector relevance
}

# Reranking Chunk Parameters
RERANK_CHUNK_SIZE = 800
RERANK_CHUNK_OVERLAP = 200
RERANK_TOP_K = 20     # Number of candidates to keep for final context
RERANK_MAX_WEB_SOURCES = 5 # Limit number of web sites to chunk for reranking

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
RESTAURANT_KEYWORDS = BOOST_KEYWORDS

SPEC_KEYWORDS = [
    "version", "バージョン", "release", "changelog",
    "api", "model", "仕様", "対応", "更新",
    "parameter", "argument", "return", "type",
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

# Domain Authority Scores (1.0 - 5.0)
DOMAIN_AUTHORITY = {
    "news": {
        "nhk.or.jp": 5.0,
        "asahi.com": 4.5,
        "mainichi.jp": 4.5,
        "yomiuri.co.jp": 4.5,
        "nikkei.com": 4.5,
        "kyodo.co.jp": 4.0,
        "jiji.com": 4.0,
        "sankei.com": 4.0,
        "tokyo-np.co.jp": 4.0,
    },
    "weather": {
        "jma.go.jp": 5.0,
        "tenki.jp": 4.0,
        "weathernews.jp": 4.0,
        "weather.yahoo.co.jp": 3.5,
    },
    "spec": {
        "github.com": 4.5,
        "google.com": 5.0,
        "ai.google.dev": 5.0,
        "developers.google.com": 5.0,
        "microsoft.com": 4.5,
        "mozilla.org": 4.5,
        "developer.mozilla.org": 4.5,
        "w3.org": 5.0,
        "openai.com": 5.0,
        "docs.openai.com": 5.0,
        "python.org": 4.5,
        "nodejs.org": 4.5,
        "reactjs.org": 4.5,
    },
    "informational": {
        "wikipedia.org": 4.0,
        "go.jp": 4.5,
        "ac.jp": 4.0,
        "ed.jp": 4.0,
    },
    "local_search": {
        "tabelog.com": 4.5,
        "gurunavi.com": 4.0,
        "retty.me": 4.0,
        "google.com/maps": 4.5,
        "hotpepper.jp": 3.5,
    },
}

# Intent-specific Keywords
NEWS_KEYWORDS = [
    "速報", "発表", "記者会見", "報道", "ニュース",
    "取材", "インタビュー", "声明", "公表", "明らか",
]

WEATHER_KEYWORDS = [
    "気温", "降水確率", "天気", "予報", "晴れ", "曇り", "雨",
    "℃", "%", "風速", "湿度", "気圧", "週間", "今日", "明日",
]

INFORMATIONAL_KEYWORDS = [
    "定義", "意味", "とは", "概要", "説明", "解説",
    "歴史", "由来", "特徴", "仕組み", "原理",
]

