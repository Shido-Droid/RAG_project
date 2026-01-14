# scripts/rag_qwen_ultimate.py
"""
Ultimate RAG v2 (improved)
- Qwen による検索意図判定 + 意図に応じたクエリ生成
- wide -> refine の ddgs 検索
- URL フィルタリング / 優先度
- trafilatura + readability + bs4 の堅牢な抽出
- サマリは max_tokens=160、失敗時フォールバックで短い自動要約
- WEB_DOCS_TO_SUMMARIZE を制限して並列/待ち時間を短縮
- エラーハンドリング強化、verbose ログあり
"""
import os
import sys
import time
import json
import re
import requests
import numpy as np
from typing import List, Dict, Tuple, Any, Optional
from sentence_transformers import SentenceTransformer
import chromadb
from tqdm import tqdm

# ddgs import with fallback
try:
    from ddgs import DDGS  # preferred
except Exception:
    try:
        from duckduckgo_search import DDGS  # older package
    except Exception:
        DDGS = None

# optional libs
try:
    import trafilatura
except Exception:
    trafilatura = None

from bs4 import BeautifulSoup
try:
    from readability import Document as ReadabilityDocument
    _HAS_READABILITY = True
except Exception:
    ReadabilityDocument = None
    _HAS_READABILITY = False

# -----------------------
# Config
# -----------------------
from enum import Enum

class AnswerMode(Enum):
    NO_CONTEXT = "no_context"
    FAST_FACT = "fast_fact"
    CONTEXT_QA = "context_qa"

LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://10.23.130.252:1234/v1/chat/completions")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen2.5-7b-instruct")
EMBED_MODEL_NAME = "intfloat/multilingual-e5-small"
CHROMA_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chroma_db")
TOKENS_LIMIT = 2000
CHARS_LIMIT = TOKENS_LIMIT * 3
DDGS_MAX_PER_QUERY = 8
DDGS_USE_NEWS = True
NUM_SEARCH_QUERIES = 4           # reduced
WEB_DOCS_TO_SUMMARIZE = 2        # reduced to speed up
VERBOSE = True
REQUESTS_TIMEOUT = 8            # HTTP timeout
LM_TIMEOUT = int(os.environ.get("LM_TIMEOUT", "60"))   # デフォルト LM タイムアウト（秒） — 最終パイプ用は長め
LM_SHORT_TIMEOUT = int(os.environ.get("LM_SHORT_TIMEOUT", "12"))  # クエリ生成など短い操作用
LM_RETRIES = int(os.environ.get("LM_RETRIES", "1"))   # リトライ 1 回（合計2回）
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

# -----------------------
# Init models (may be slow)
# -----------------------
embed_model = SentenceTransformer(EMBED_MODEL_NAME)
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("rag_docs_e5")

# -----------------------
# Utils
# -----------------------
def log(*args, **kwargs):
    if VERBOSE:
        print(*args, **kwargs)

def safe_json_load(s: str):
    try:
        return json.loads(s)
    except Exception:
        return None
    
# -----------------------
# FAST PATH utilities
# -----------------------
def try_fast_path(question: str) -> str | None:
    # --- 正規化 ---
    q = question.strip()

    # 全角 → 半角
    trans = str.maketrans({
        "０":"0","１":"1","２":"2","３":"3","４":"4",
        "５":"5","６":"6","７":"7","８":"8","９":"9",
        "＋":"+","－":"-","＊":"*","×":"*","÷":"/",
        "（":"(","）":")"
    })
    q = q.translate(trans)

    # 日本語助詞・疑問符など除去
    q = re.sub(r"[=は？\?を]", "", q)
    q = q.replace(" ", "").replace("　", "")

    # --- 四則演算 ---
    if re.fullmatch(r"[0-9+\-*/().]+", q):
        try:
            return str(eval(q, {"__builtins__": {}}, {}))
        except Exception:
            return None

    # --- 現在時刻 ---
    if any(k in question for k in ["現在の時刻", "今何時", "今の時間", "今の時刻", "現在時刻", "何時です"]):
        import datetime
        now = datetime.datetime.now(
            datetime.timezone(datetime.timedelta(hours=9))
        )
        return f"現在の日本時刻は {now.strftime('%H時%M分')} です。"

    # --- 超常識 ---
    COMMON = {
        "日本の首都": "日本の首都は東京です。",
        "1日は何時間": "1日は24時間です。",
        "1年は何日": "通常の年は365日、うるう年は366日です。",
    }
    for k, v in COMMON.items():
        if k in q:
            return v

    return None


# -----------------------
# LMStudio wrapper
# -----------------------

# ---------- lmstudio_chat の差し替え（置き換え） ----------
def lmstudio_chat(
    messages: List[Dict],
    max_tokens: int = 256,
    temperature: float = 0.2,
    timeout: int = LM_TIMEOUT,
    retries: int = LM_RETRIES
) -> Dict:
    payload = {
        "model": QWEN_MODEL,   # ← 固定やめる
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False
    }
    headers = {"Content-Type": "application/json"}

    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                LMSTUDIO_URL,
                headers=headers,
                data=json.dumps(payload),
                timeout=timeout
            )
            r.raise_for_status()
            time.sleep(0.3)  # ★ qwen2.5 安定化（重要）
            return r.json()
        except requests.exceptions.Timeout as e:
            last_exc = e
            if attempt < retries:
                log(f"[lmstudio_chat] Timeout retry {attempt+1}/{retries}")
                continue
            raise RuntimeError("LM timeout") from e
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"[lmstudio_chat] HTTP error: {e}") from e

    raise RuntimeError(f"[lmstudio_chat] failed: {last_exc}")


    # should not reach here
    raise RuntimeError(f"[lmstudio_chat] Unknown failure: {last_exc}")
# ------------------------------------------------------------------

# -----------------------
# 0) Intent detection helper
# -----------------------
def detect_search_intent(question: str, history: List[Dict] = []) -> str:
    """
    Ask Qwen to classify intent: informational / local_search / news / other
    If LM fails, fallback simple heuristic:
      - contains words like 'どこ', '近く', 'ランチ', '店' -> local_search
      - contains 'いつ', 'なぜ', 'どうやって' -> informational
      - contains 'ニュース', '最新', '発表' -> news
      - else informational
    """
    # 1. Fast heuristics (Prioritize document/local keywords)
    qlow = question.lower()
    doc_tokens = ["このドキュメント", "この文書", "アップロード", "ファイル", "資料", "pdf", "要約", "抽出", "セクション", "章"]
    for tok in doc_tokens:
        if tok in qlow:
            log(f"[Intent] Heuristic match: '{tok}' -> document_qa")
            return "document_qa"

    system = (
    "Classify intent: informational / spec / factual / local_search / news / weather / document_qa / other"
    )

    history_text = ""
    if history:
        history_text = "会話履歴:\n" + "\n".join([f"- {h['role']}: {h['content']}" for h in history]) + "\n\n"

    user = f"{history_text}ユーザーの質問（日本語）: {question}\n\nReturn one of: informational, local_search, news, weather, document_qa, other"
    try:
        resp = lmstudio_chat(
            [{"role":"system","content":system},
             {"role":"user","content":user}],
            max_tokens=32,
            temperature=0.0,
            timeout=LM_SHORT_TIMEOUT   # ← 追加
        )

        text = resp['choices'][0]['message']['content'].strip().lower()
        for t in ["informational","local_search","news","weather","document_qa","other"]:
            if t in text:
                return t
    except Exception as e:
        log("[Intent] LM failed:", e)
    # fallback heuristics
    local_tokens = ["近く", "ランチ", "店", "レストラン", "営業時間", "おいしい", "予約"]
    news_tokens = ["ニュース", "発表", "速報", "昨日", "今日"]
    info_tokens = ["なぜ", "どうやって", "いつ", "とは", "教えて", "標高", "定義", "意味"]
    spec_tokens = ["バージョン", "仕様", "対応", "api", "model", "release"]
    weather_tokens = ["天気", "予報", "気温", "雨", "晴れ", "台風", "気象"]

    if any(tok in qlow for tok in weather_tokens):
        return "weather"
    if any(tok in qlow for tok in local_tokens):
        return "local_search"
    if any(tok in qlow for tok in news_tokens):
        return "news"
    if any(tok in qlow for tok in info_tokens):
        return "informational"
    if any(tok in qlow for tok in spec_tokens):
        return "spec"
    return "informational"

# -----------------------
# 1) Query generation (intent-aware)
# -----------------------
def qwen_generate_search_queries(question: str, intent: str, history: List[Dict] = [], n: int = NUM_SEARCH_QUERIES) -> List[str]:
    log("[Search Intent]", intent)
    # build a system prompt tailored by intent
    if intent == "local_search":
        sys_prompt = ("You are a search-query generator for local business searches (Japanese). Produce short, location-aware queries likely to hit local review/restaurant pages.")
        extra_instruction = "- Prefer terms like 'ランチ', '営業時間', '口コミ', '食べログ', '住所' etc."
    elif intent == "news":
        sys_prompt = ("You are a search-query generator for news-related searches (Japanese). Produce concise queries that would match news articles and official sources.")
        extra_instruction = "- Prefer terms like 'ニュース', '速報', '発表', '原因', '影響'."
    elif intent == "weather":
        sys_prompt = ("You are a search-query generator for weather forecasts (Japanese). Produce queries to get accurate weather info.")
        extra_instruction = "- Prefer terms like '天気', '1時間ごと', '週間予報', '気象庁'."
    elif intent == "informational":
        sys_prompt = (
        "You are a search-query generator for factual informational search (Japanese). "
        "If the query is an acronym or ambiguous, add context (e.g. 'AI', 'IT', '意味') or expand it. "
        "DO NOT add restaurant, food, travel, or local business related terms unless explicitly asked."
        )
        extra_instruction = "- Use factual terms. Expand acronyms if ambiguous."
    elif intent == "recommendation":
        sys_prompt = (
        "You are a search-query generator for movie recommendations (Japanese). "
        "Generate queries about currently showing movies, rankings, and reviews. "
        "DO NOT include restaurants or food-related terms."
        )
        extra_instruction = "- Prefer terms like '公開中 映画', '映画 ランキング', 'レビュー', '評価'."
    else:
        # intent == "other" 用（安全側に倒す）
        sys_prompt = (
            "You are a search-query generator for general informational search (Japanese). "
            "Avoid restaurant, food, travel, and local business terms."
        )
        extra_instruction = "- Use neutral factual keywords only."

    history_text = ""
    if history:
        history_text = "会話履歴:\n" + "\n".join([f"- {h['role']}: {h['content']}" for h in history]) + "\n\n"

    user = (
        f"{history_text}ユーザーの質問: {question}\n\n"
        f"出力ルール:\n- {extra_instruction}\n- 出力はJSON配列（日本語の文字列配列）で1行で返してください。\n"
        f"出力ルール:\n- {extra_instruction}\n"
        f"- Generate {n} different queries.\n"
        f"- 出力はJSON配列（日本語の文字列配列）で1行で返してください。\n"
        f"- 例: [\"富士山 標高\", \"富士山 高さ 公式\"]"
    )

    messages = [{"role":"system","content":sys_prompt},{"role":"user","content":user}]
    try:
        resp = lmstudio_chat(messages=messages, max_tokens=160, temperature=0.0, timeout=LM_SHORT_TIMEOUT)
        text = resp['choices'][0]['message']['content']
        parsed = safe_json_load(text)
        if isinstance(parsed, list) and parsed:
            qs = [q.strip() for q in parsed if isinstance(q, str) and q.strip()]
            return qs[:n]
        # fallback: try line extraction
        lines = [l.strip(" -•\"'") for l in text.splitlines() if l.strip()]
        qs = []
        for ln in lines:
            ln2 = re.sub(r'^[0-9]+[).:\-\s]*', '', ln)
            if ln2:
                qs.append(ln2)
            if len(qs) >= n:
                break
        if qs:
            return qs[:n]
    except Exception as e:
        log("[Qwen] query-gen error (LM):", e)

    # LM failed => fallback heuristics depending on intent
    base = question.strip()
    if intent == "local_search":
        variants = [f"{base} ランチ", f"{base} 営業時間", f"{base} 口コミ", f"{base} 食べログ"]
    elif intent == "news":
        variants = [f"{base} ニュース", f"{base} 速報", f"{base} 発表"]
    elif intent == "weather":
        variants = [f"{base} 天気", f"{base} 予報", f"{base} 気象庁"]
    else:
        variants = [base, base + " とは", base + " 意味", base + " データ"]
    # ensure length n
    out = []
    for v in variants:
        if v not in out:
            out.append(v)
        if len(out) >= n:
            break
    while len(out) < n:
        out.append(base)
    return out[:n]

# -----------------------
# 2) ddgs search (wide -> refine)
# -----------------------
def ddgs_search_many(queries: List[str], per_query: int = DDGS_MAX_PER_QUERY) -> List[Dict]:
    results = []
    if DDGS is None:
        log("[DDGS] ddgs/duckduckgo not available.")
        return results

    try:
        ddgs: Any = DDGS()
        for i, q in enumerate(queries):
            if i > 0:
                time.sleep(1.0)  # 連続リクエストによるgzipエラー回避のため待機
            log("[DDGS] Searching:", q)
            try:
                for r in ddgs.text(q, region="jp-jp", safesearch="off", timelimit=None, max_results=per_query):
                    if r.get("href"):
                        results.append({"title": r.get("title",""), "body": r.get("body",""), "href": r.get("href",""), "query": q})
                if DDGS_USE_NEWS:
                    try:
                        for r in ddgs.news(q, region="jp-jp", max_results=4):
                            if r.get("href"):
                                results.append({"title": r.get("title",""), "body": r.get("body",""), "href": r.get("href",""), "query": q})
                    except Exception:
                        pass
            except Exception as e:
                log("[DDGS] search error:", q, e)
    except Exception as e:
        log("[DDGS] init/search error:", e)

    # dedupe
    uniq = {}
    for r in results:
        href = r.get("href") or ""
        key = href or (r.get("title","")+r.get("body",""))
        if key not in uniq:
            uniq[key] = r
    out = list(uniq.values())
    log(f"[DDGS] Found {len(out)} unique hits")
    return out

def refine_queries_from_hits(
    hits: List[Dict],
    n_extra: int = 2,
    *,
    intent: str | None = None,
) -> List[str]:
    """
    Generate additional search queries from top search hits.
    - intent が local_search / weather 系の場合は refine しない
    """

    # ---- intent ガード（最重要）----
    if intent in ("local_search", "weather", "time", "calculator"):
        return []

    if not hits:
        return []

    top_text = "\n".join(
        [
            f"{i+1}. {h.get('title','')} - {h.get('body','')}"
            for i, h in enumerate(hits[:8])
        ]
    )

    prompt = (
        "以下は検索上位のタイトルとスニペットです。"
        "これを元にさらに掘るためのキーワードクエリを"
        f"日本語で{n_extra}個生成してください（短く）。\n\n{top_text}"
    )

    try:
        resp = lmstudio_chat(
            [
                {"role": "system", "content": "You are a search optimizer."},
                {"role": "user", "content": prompt},
            ],
            max_tokens=120,
            temperature=0.0,
            timeout=12,
        )

        text = resp["choices"][0]["message"]["content"]

        lines = [l.strip(" -•\"'") for l in text.splitlines() if l.strip()]
        out: List[str] = []

        for ln in lines:
            ln2 = re.sub(r"^[0-9]+[).:\-\s]*", "", ln)
            if ln2:
                out.append(ln2)
            if len(out) >= n_extra:
                break

        return out

    except Exception as e:
        log("[Qwen] refine-queries error:", e)
        return []

# -----------------------
# 3) fetching & extraction
# -----------------------
def fetch_html(url: str) -> str:
    if not url:
        return ""
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=REQUESTS_TIMEOUT)
        if r.status_code == 200 and r.content:
            # ★ charset を強制 UTF-8
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
    except Exception as e:
        log("[fetch_html] error:", url, e)
    return ""


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

from urllib.parse import urlparse

def extract_text(url: str, html: Optional[str] = None) -> str:
    """
    Robust extraction:
    - domain blacklist(fast skip) 
    - BUT keep offical Whitelist
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # whitelist 優先
    if not any(w in domain for w in WHITELIST_DOMAINS):
        if any(b in domain for b in BLACKLIST_DOMAINS):
            log(f"[extract_text] skipped by blacklist: {url}")
            return ""
        if "xn--" in domain and not domain.endswith(".jp"):
            log(f"[extract_text] skipped suspicious punycode: {url}")
            return ""


    if html is None:
        html = fetch_html(url)

    if not html or len(html) < 200:
        log(f"[extract_text] empty HTML for {url}")
        return ""

    # Sanitize HTML to prevent lxml errors with null bytes/control chars
    html = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', html)

    # Trafilatura
    if trafilatura is not None:
        try:
            txt = trafilatura.extract(html, include_comments=False, favor_precision=True)
            if txt and len(txt.strip()) > 220:
                return txt.strip()
        except Exception:
            pass

    # Readability
    if _HAS_READABILITY and ReadabilityDocument:
        try:
            doc = ReadabilityDocument(html)
            summary = doc.summary()
            soup = BeautifulSoup(summary, "html.parser")
            text = soup.get_text("\n", strip=True)
            if text and len(text) > 140:
                return text
        except Exception:
            pass

    # BeautifulSoup heavy cleaning
    try:
        soup = BeautifulSoup(html, "html.parser")
        for bad in soup(["script","style","noscript","header","footer","nav","aside","form","iframe","svg"]):
            bad.decompose()
        body = soup.body or soup
        raw = body.get_text("\n", strip=True)
        lines = []
        for ln in raw.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if len(ln) < 30:
                continue
            if any(x in ln for x in ["利用規約","Cookie","Privacy","プライバシー"]):
                continue
            lines.append(ln)
        if lines:
            text = "\n\n".join(lines)
            return text[:30000]
    except Exception:
        pass

    # Final minimal fallback: title + first 15 meaningful lines
    try:
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.get_text().strip() if soup.title else ""
        alltxt = soup.get_text("\n", strip=True)
        lines = [l.strip() for l in alltxt.splitlines() if l.strip() and len(l.strip()) >= 30]
        body = "\n".join(lines[:15])
        if title or body:
            return f"{title}\n{body}"
    except Exception:
        pass

    return ""

# -----------------------
# 4) scoring (kept but less aggressive)
# -----------------------
def score_text_for_restaurant(text: str, title: str = "", url: str = "") -> float:
    score = 0.0
    lower = (title + "\n" + (text or "")).lower()
    for dom in PRIORITY_DOMAINS:
        if dom in (url or "").lower() or dom in lower:
            score += 2.5
    for k in BOOST_KEYWORDS:
        cnt = lower.count(k.lower())
        if cnt:
            score += min(2.0, 0.4 * cnt)
    if re.search(r"\d{2,4}-\d{1,4}", lower) or "〒" in lower:
        score += 1.0
    if len(text) > 800:
        score += 1.0
    elif len(text) > 300:
        score += 0.4
    return score

def score_text_for_spec(text: str, title: str = "", url: str = "") -> float:
    score = 0.0
    t = (title + " " + text).lower()

    # 公式・一次情報を強く評価
    if any(k in url for k in ["google.com", "ai.google.dev"]):
        score += 3.0

    # spec系キーワード
    spec_keywords = [
        "version", "バージョン", "release", "changelog",
        "api", "model", "仕様", "対応", "更新"
    ]
    score += sum(0.3 for k in spec_keywords if k in t)

    # 数字・バージョン表記
    if any(ch.isdigit() for ch in text):
        score += 0.5

    # 日付があると加点
    if any(k in t for k in ["2024", "2025", "月", "日"]):
        score += 0.5

    return score

# -----------------------
# 5) summarization & extraction (LM with small max_tokens + fast fallback)
# -----------------------


# -----------------------
# 6) Chroma search
# -----------------------
def search_chroma(query: str, n_results: int = 6) -> List[Dict]:
    try:
        q_emb = embed_model.encode([f"query: {query}"])
        res = collection.query(query_embeddings=[q_emb[0]], n_results=n_results)
        
        documents = res.get("documents")
        docs = documents[0] if documents else []
        
        metadatas = res.get("metadatas")
        metas = metadatas[0] if metadatas else []
        
        # docs/metas が None の場合のガード (Chromaのバージョンによる挙動差異吸収)
        if docs is None: docs = []
        if metas is None: metas = []
        
        results = []
        for d, m in zip(docs, metas):
            results.append({"text": d, "meta": m or {}})
        return results[:n_results]
    except Exception as e:
        log("[Chroma] query error:", e)
        return []

# -----------------------
# 7) context builder
# -----------------------

def collect_candidates(chroma_docs, scored_web, min_chars: int = 50):
    """
    Chroma + Web を統合して候補を作る
    - text が min_chars 未満のものは除外
    """
    candidates = []

    # ---- Chroma docs ----
    for item in chroma_docs:
        text = item.get("text", "").strip()
        if len(text) < min_chars:
            continue

        meta = item.get("meta", {})
        # メタデータからタイトルやソースを取得
        title = meta.get("title") or meta.get("source") or "Local Document"

        candidates.append({
            "source": "chroma",
            "text": text,
            "meta": {"title": title, "url": meta.get("source")}
        })

    # ---- Web docs ----
    for item in scored_web:
        text = (item.get("text") or "").strip()
        if len(text) < min_chars:
            continue

        candidates.append({
            "source": "web",
            "text": text,
            "meta": {
                "title": item.get("title"),
                "url": item.get("url")
            }
        })

    return candidates

    
def rerank_candidates(question, candidates, top_k=8):
    q_emb = embed_model.encode([f"query: {question}"])[0]
    ranked = []

    for c in candidates:
        if "emb" not in c:
            c["emb"] = embed_model.encode([f"passage: {c['text'][:800]}"])[0]
            
        emb = c["emb"]
        score = float(
            np.dot(q_emb, emb) / 
            (np.linalg.norm(q_emb) * np.linalg.norm(emb) + 1e-8)
        )
        ranked.append((score, c))

    ranked.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in ranked[:top_k]]
    
def dedupe_by_similarity(candidates, threshold=0.92):
    """
    embedding 類似度が高すぎる文書を除外する
    - rerank_candidates 後の candidates を想定
    - c["emb"] が既に存在する前提
    """
    deduped = []

    for c in candidates:
        keep = True
        for o in deduped:
            sim = float(
                np.dot(c["emb"], o["emb"]) /
                (np.linalg.norm(c["emb"]) * np.linalg.norm(o["emb"]) + 1e-8)
            )
            if sim >= threshold:
                keep = False
                break

        if keep:
            deduped.append(c)

    return deduped


    
def build_context_from_candidates(candidates, char_limit=CHARS_LIMIT):
    buf = []
    total = 0

    for c in candidates:
        if c["source"] == "web":
            header = f"[Web]\nTitle: {c['meta'].get('title')}\nURL: {c['meta'].get('url')}\n"
        else:
            header = f"[Document: {c['meta'].get('title')}]\n"

        body = c["text"].strip()
        chunk = header + body + "\n\n"

        if total + len(chunk) > char_limit:
            break

        buf.append(chunk)
        total += len(chunk)

    return "".join(buf)

# -----------------------
# 8) final answer pipeline
# -----------------------
# ---------- final_answer_pipeline の LM 呼び出しタイムアウト調整（置き換え） ---------

def final_answer_pipeline(question: str, context: str, history: List[Dict] = [], intent: str = "informational", difficulty: str = "normal") -> str:
    """
    Final answer generation for RAG (non-silent version)
    - Extract answers explicitly stated in context
    - If partially answerable, answer only that part
    - If nothing relevant exists, say so
    """

    if intent == "weather":
        system = (
            "あなたは天気予報のアシスタントです。\n"
            "【検索された文脈】にある気象データ（気温、降水確率、風速など）を整理して伝えてください。\n"
            "天候（晴れ・雨など）の明示的な記述がなくても、数値データがあればそれを回答してください。\n"
            "文脈に日付や時刻が含まれている場合は、それも明記してください。"
        )
    else:
        base_system = (
            "あなたは与えられた情報のみに基づいて回答するアシスタントです。\n"
            "日本語で回答してください。\n"
            "以下の【検索された文脈】に含まれている情報だけを使って、質問に答えてください。\n"
            "もし文脈の中に答えが全くない場合は、「提供された情報からは分かりません」とだけ答えてください。\n"
            "回答できた場合は、「提供された情報からは分かりません」という文言を絶対に含めないでください。\n"
            "決して自分の知識を使って回答を捏造したり、文脈にない情報を追加したりしないでください。\n"
            "もし文脈の中に「[Section: ...]」や「[Page X]」のような情報が含まれている場合は、回答の文末に「(参照: Section '...', Page X)」のように付記してください。\n"
            "【重要】回答に専門用語を含める場合は、必ずその用語を `[[専門用語]]` のように二重角括弧で囲ってください。例: 「このシステムは[[RAG]]に基づいています。」"

        )
        
        if difficulty == "easy":
            system = base_system + "\n\n【回答スタイル: 初学者向け】\n専門用語はなるべく避け、初心者にもわかりやすい言葉で、丁寧に噛み砕いて説明してください。ただし、重要な固有名詞や用語は必ず `[[ ]]` で囲ってください。"
        elif difficulty == "professional":
            system = base_system + "\n\n【回答スタイル: 専門的】\n専門用語を適切に使用し、簡潔かつ論理的に、実務的・専門的な観点から詳細に回答してください。重要な用語は必ず `[[ ]]` で囲ってください。"
        else:
            system = base_system

    def _try_generate(ctx):
        history_text = ""
        if history:
            history_text = "Conversation History:\n" + "\n".join([f"{h['role']}: {h['content']}" for h in history]) + "\n\n"

        user = (
            f"{history_text}【検索された文脈】:\n{ctx}\n\n"
            f"【質問】:\n{question}\n\n"
            "【指示】:\n"
            "回答に含まれる重要な専門用語、システム名、機能名などは、必ず `[[用語]]` のように二重角括弧で囲ってください。\n"
            "例: 「[[無限大キャンパス]]では[[履修登録]]が可能です。」"
        )
        return lmstudio_chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=512,
            temperature=0.0,
            timeout=LM_TIMEOUT,
        )

    try:
        resp = _try_generate(context)
        content = resp["choices"][0]["message"]["content"].strip()

        # Post-processing: 回答が生成されているのに「分かりません」が含まれている場合、削除する
        failure_phrase = "提供された情報からは分かりません"
        if failure_phrase in content and len(content) > 50:
            content = content.replace(failure_phrase, "")

        return content.strip()

    except Exception as e:
        log("[Qwen] final_answer_pipeline error:", e)
        if "400" in str(e):
            log("[Qwen] 400 Error detected. Retrying with shorter context...")
            try:
                resp = _try_generate(context[:len(context)//2])
                return resp["choices"][0]["message"]["content"].strip()
            except Exception as e2:
                log("[Qwen] Retry failed:", e2)
        return "回答生成中にエラーが発生しました。"


def build_recommendation_answer(web_summaries, question):
    """
    recommendation 用（LMあり）
    - タイトルと要約を統合して回答生成
    - 重複を避けるためにタイトルを含む場合は要約のみを含める
    """
    context = "\n".join(
        f"- {title}: {summary}"
        for title, summary, _ in web_summaries[:3]
    )

    prompt = f"""
以下の情報を元に、質問に簡潔かつ正確に答えてください。

【質問】
{question}

【参考情報】
{context}

・推測はしない
・不明な場合は「公式に明示されていない」と書く
・最新情報があれば日付を明記する
"""

    resp = lmstudio_chat(
        [
            {"role": "system", "content": "You are a precise technical assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=512,
        temperature=0.0,
    )

    return resp["choices"][0]["message"]["content"].strip()




# =========================
# Question analysis helpers
# =========================
def decide_answer_mode(intent: str, context: str, web_list) -> AnswerMode:
    # context が完全に空 → 何も答えられない
    if not context or len(context.strip()) < 100:
        return AnswerMode.NO_CONTEXT

    # informational は FAST_FACT 固定
    if intent == "informational":
        return AnswerMode.FAST_FACT

    # それ以外は context QA（spec / factual / news / local）
    return AnswerMode.CONTEXT_QA


def extract_keywords_ja(question: str) -> list[str]:
    q = question.replace("？", "").replace("?", "")
    stop = {"は", "と", "の", "が", "を", "に", "です", "何"}

    keywords = []

    # 意味系ワードを優先
    for w in ["違い", "比較", "意味", "理由", "特徴", "方法", "種類"]:
        if w in q:
            keywords.append(w)

    # 名詞っぽい文字も拾う（超簡易）
    for ch in q:
        if ch not in stop and ch not in keywords:
            keywords.append(ch)

    return keywords



# =========================
# Answer builders
# =========================

def build_informational_answer(web_summaries, question):
    """
    informational 用（LMなし）
    - タイトルが質問語と無関係なものを除外
    """
    keywords = extract_keywords_ja(question)
    lines = []

    for title, summary, url in web_summaries:
        # タイトルが空なら除外
        if not title:
            continue

        # 🔍 質問キーワードを1つも含まないタイトルは除外
        if not any(k in title for k in keywords):
            continue

        lines.append(summary.strip())

        # 最大2件まで
        if len(lines) >= 2:
            break

    # 保険：1件も残らなかった場合
    if not lines and web_summaries:
        lines.append(web_summaries[0][1].strip())

    return "\n".join(lines)

def build_spec_answer(web_summaries, question):
    """
    spec / factual 用（LMあり）
    ・複数ソースを統合
    ・バージョン / 型番 / 日付を明示
    """
    context = "\n".join(
        f"- {title}: {summary}"
        for title, summary, _ in web_summaries[:3]
    )

    prompt = f"""
以下の情報を元に、質問に簡潔かつ正確に答えてください。

【質問】
{question}

【参考情報】
{context}

・推測はしない
・不明な場合は「公式に明示されていない」と書く
・最新情報があれば日付を明記する
"""

    resp = lmstudio_chat(
        [
            {"role": "system", "content": "You are a precise technical assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=512,
        temperature=0.0,
    )

    return resp["choices"][0]["message"]["content"].strip()


# -----------------------
# Main flow
# -----------------------
def process_question(question: str, history: List[Dict] = [], difficulty: str = "normal") -> dict:
    # ===== FAST PATH =====
    fast = try_fast_path(question)
    if fast is not None:
        return {"answer": fast, "sources": []}
    start_time = time.time()

    # =====================
    # STEP 0: intent（1回だけ）
    # =====================
    intent = detect_search_intent(question, history)
    log(f"[Intent] {intent}")

    # =====================
    # STEP 1: Chroma
    # =====================
    log("=== STEP 1: Chroma 検索 ===")
    chroma_docs = search_chroma(question, n_results=10)
    for i, d in enumerate(chroma_docs, 1):
        log(f"[Chroma #{i}] {str(d.get('text'))[:100].replace(chr(10),' ')}... (Meta: {d.get('meta')})")

    # =====================
    # STEP 2: Search queries
    # =====================
    if intent == "document_qa":
        log("=== STEP 2 & 3: Web search skipped (document_qa) ===")
        queries = []
        hits = []
    else:
        log("=== STEP 2: 検索クエリ生成 ===")
        queries = qwen_generate_search_queries(question, intent, history, n=NUM_SEARCH_QUERIES)
        log("Generated queries:", queries)

        # =====================
        # STEP 3: ddgs wide
        # =====================
        log("=== STEP 3: ddgs wide search ===")
        hits = ddgs_search_many(queries, per_query=DDGS_MAX_PER_QUERY)

        # intent による件数制御
        if intent == "informational":
            hits = hits[:5]
        elif intent in ("local_search", "news", "recommendation", "weather"):
            hits = hits[:10]

    # =====================""" 
    # STEP 4: refine（必要な場合のみ）
    # =====================
    log("=== STEP 4: refine search ===")
    if intent in ("local_search", "news", "recommendation"):
        extra = refine_queries_from_hits(hits, n_extra=2, intent=intent)
        if extra:
            log("Refined queries:", extra)
            more_hits = ddgs_search_many(extra, per_query=6)

            seen = {h.get("href") for h in hits if h.get("href")}
            for h in more_hits:
                if h.get("href") and h["href"] not in seen:
                    hits.append(h)

    # =====================
    # STEP 5: unique + fetch + score
    # =====================
    unique_hits = []
    seen = set()
    for h in hits:
        key = h.get("href") or (h.get("title","") + h.get("body",""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique_hits.append(h)

    log(f"[Total unique hits] {len(unique_hits)}")

    scored = []
    for h in unique_hits:
        url = h.get("href","")
        title = h.get("title","")
        text = extract_text(url)

        # スクレイピング失敗時のフォールバック: 検索スニペットを利用
        if not text or len(text) < 50:
            snippet = h.get("body", "")
            if snippet and len(snippet) > 30:
                text = f"{snippet}\n(Note: Full content fetch failed, using search snippet.)"

        if not text:
            continue

        if intent in ("spec", "factual", "informational", "weather"):
            score = score_text_for_spec(text, title=title, url=url)
        else:
            score = score_text_for_restaurant(text, title=title, url=url)

        scored.append({
            "title": title,
            "url": url,
            "text": text,
            "score": score
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    log(f"[Web] scored items: {len(scored)}")


    # =====================
    # STEP 6: summarize
    # =====================
    candidates = collect_candidates(chroma_docs, scored)
    ranked_candidates = rerank_candidates(question, candidates, top_k=20)
    ranked_candidates = dedupe_by_similarity(ranked_candidates)

    # 参照元の抽出 (Webソースのみ)
    sources = []
    seen_urls = set()
    for c in ranked_candidates:
        url = c["meta"].get("url")
        title = c["meta"].get("title")
        if url and url not in seen_urls:
            sources.append({"title": title, "url": url})
            seen_urls.add(url)

    # =====================
    # STEP 7: context build（唯一）
    # =====================
    log("=== STEP 7: context build ===")

    context = build_context_from_candidates(ranked_candidates)

    log(f"[Context chars] {len(context)}")

    log("[Final Context Preview]")
    log("-----")
    log(context[:500])
    log("-----")

    # =====================
    # STEP 8: final answer
    # =====================
    answer = final_answer_pipeline(question, context, history, intent=intent, difficulty=difficulty)

    log(f"\nTotal time: {time.time() - start_time:.1f}s")
    return {"answer": answer, "sources": sources}

def analyze_document_content(text: str) -> Dict[str, Any]:
    """ドキュメントの内容を分析し、要約・タイトル・キーワードを抽出する"""
    if not text:
        return {}
    
    # 先頭3500文字程度を分析対象にする
    excerpt = text[:3500]
    
    system = "You are a helpful assistant. Analyze the text and extract summary, title, and keywords."
    user = (
        f"Text:\n{excerpt}\n\n"
        "Please output the result in the following JSON format (Japanese):\n"
        "{\n"
        '  "summary": "Concise summary using bullet points",\n'
        '  "title": "A short descriptive title",\n'
        '  "keywords": ["keyword1", "keyword2", "keyword3"]\n'
        "}"
    )
    
    try:
        resp = lmstudio_chat(
            [{"role": "system", "content": system},
             {"role": "user", "content": user}],
            max_tokens=350,
            temperature=0.2
        )
        content = resp["choices"][0]["message"]["content"].strip()
        # JSONブロックの除去
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        return safe_json_load(content) or {}
    except Exception as e:
        log(f"[Analyze] Error: {e}")
        return {}

def add_document_to_kb(text: str, source: str, doc_metadata: Optional[Dict[str, Any]] = None):
    if not text:
        return

    if doc_metadata is None:
        doc_metadata = {}

    # Simple chunking
    chunk_size = 600
    chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
    
    ids = [f"{source}_part{i}_{int(time.time())}" for i in range(len(chunks))]
    
    # メタデータの構築
    title = doc_metadata.get("title") or source
    if isinstance(title, list):
        title = " ".join([str(t) for t in title])
    elif not isinstance(title, str):
        title = str(title)

    summary = doc_metadata.get("summary", "")
    if isinstance(summary, list):
        summary = "\n".join([str(s) for s in summary])
    elif not isinstance(summary, str):
        summary = str(summary)

    keywords = doc_metadata.get("keywords", [])
    if isinstance(keywords, list):
        keywords_str = ", ".join(keywords)
    else:
        keywords_str = str(keywords)

    base_meta = {
        "source": source,
        "title": title,
        "summary": summary,
        "keywords": keywords_str
    }
    metadatas: List[Any] = [base_meta.copy() for _ in chunks]
    
    # Embedding
    embeddings = embed_model.encode([f"passage: {c}" for c in chunks])
    
    collection.add(
        ids=ids,
        documents=chunks,
        embeddings=embeddings.tolist(),
        metadatas=metadatas
    )
    log(f"[DB] Added {len(chunks)} chunks from {source}")

def clear_knowledge_base():
    try:
        all_ids = collection.get()['ids']
        if all_ids:
            collection.delete(ids=all_ids)
        log("[DB] Knowledge base cleared.")
    except Exception as e:
        log(f"[DB] clear_knowledge_base error: {e}")
        raise e

def get_all_documents() -> List[Dict[str, Any]]:
    """DB内の全ドキュメントのソース一覧を取得"""
    try:
        # メタデータのみ取得して軽量化
        data = collection.get(include=['metadatas'])
        metadatas = data.get('metadatas')
        if metadatas is None:
            metadatas = []
        
        # ソース名でユニーク化
        docs_map = {}
        for m in metadatas:
            if m and 'source' in m:
                src = m['source']
                # 既に登録済みでも、情報量が多い（summaryがある）メタデータを優先して保持する
                if src not in docs_map or (m.get('summary') and not docs_map[src].get('summary')):
                    docs_map[src] = m
        
        # リスト化
        result = []
        for src, m in docs_map.items():
            result.append({
                "source": src,
                "title": m.get("title", src),
                "summary": m.get("summary", ""),
                "keywords": m.get("keywords", "")
            })
            
        return sorted(result, key=lambda x: x['source'])
    except Exception as e:
        log("[DB] get_all_documents error:", e)
        return []

def document_exists(source: str) -> bool:
    """指定されたソースのドキュメントが存在するか確認"""
    try:
        # limit=1 で存在確認
        result = collection.get(where={"source": source}, limit=1)
        return len(result['ids']) > 0
    except Exception as e:
        log(f"[DB] document_exists error: {e}")
        return False

def delete_document_from_kb(source: str) -> bool:
    """指定されたソースのドキュメントを削除"""
    try:
        collection.delete(where={"source": source})
        log(f"[DB] Deleted document: {source}")
        return True
    except Exception as e:
        log(f"[DB] delete_document_from_kb error: {e}")
        return False

def update_document_title(source: str, new_title: str) -> bool:
    """指定されたソースのドキュメントのタイトルを更新"""
    try:
        # Get all chunks for this source
        result = collection.get(where={"source": source})
        ids = result['ids']
        metadatas = result['metadatas']
        
        if not ids:
            return False
            
        if metadatas is None:
            metadatas = []

        # Update title in all metadatas
        new_metadatas = []
        for meta in metadatas:
            if meta is None:
                m: Dict[str, Any] = {}
            else:
                m = dict(meta)
            m['title'] = new_title
            new_metadatas.append(m)
            
        collection.update(ids=ids, metadatas=new_metadatas)
        log(f"[DB] Updated title for {source} to '{new_title}'")
        return True
    except Exception as e:
        log(f"[DB] update_document_title error: {e}")
        return False

def explain_term(term: str) -> str:
    """専門用語の解説を生成する"""
    system = "You are a helpful teacher. Explain the technical term concisely for a student in Japanese."
    user = f"Term: {term}\n\nExplanation:"
    try:
        resp = lmstudio_chat(
            [{"role": "system", "content": system},
             {"role": "user", "content": user}],
            max_tokens=200,
            temperature=0.2,
            timeout=LM_SHORT_TIMEOUT
        )
        return resp["choices"][0]["message"]["content"].strip()
    except Exception as e:
        log(f"[Explain] Error: {e}")
        return "解説を取得できませんでした。"

def main():
    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:]).strip()
        print(f"質問(CLI): {question}")
    else:
        question = input("質問を入力してください: ").strip()
    if not question:
        print("質問が空です。")
        return

    result = process_question(question)
    print("\n=== 最終回答 ===")
    print(result["answer"])
    if result["sources"]:
        print("\n[参照元]")
        for s in result["sources"]:
            print(f"- {s['title']}: {s['url']}")


if __name__ == "__main__":
    main()