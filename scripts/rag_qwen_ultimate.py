# scripts/rag_qwen_ultimate_v2.py
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
import time
import json
import re
import requests
import numpy as np
from typing import List, Dict, Tuple
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
    _HAS_READABILITY = False

# -----------------------
# Config
# -----------------------
LMSTUDIO_URL = os.environ.get("LMSTUDIO_URL", "http://10.23.130.252:1234/v1/chat/completions")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen2.5-7b-instruct")
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
CHROMA_PATH = "./chroma_db"
TOKENS_LIMIT = 6000
CHARS_LIMIT = TOKENS_LIMIT * 4
DDGS_MAX_PER_QUERY = 8
DDGS_USE_NEWS = True
NUM_SEARCH_QUERIES = 4           # reduced
WEB_DOCS_TO_SUMMARIZE = 5        # reduced to speed up
VERBOSE = True
REQUESTS_TIMEOUT = 8            # HTTP timeout
LM_TIMEOUT = 30                 # LM HTTP timeout (seconds)
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/142.0.0.0 Safari/537.36"
# ---------- 上部の Config / 定数に追加・変更（置き換え） ----------
# 既存の定数の近くに追加してください
LM_TIMEOUT = int(os.environ.get("LM_TIMEOUT", "60"))   # デフォルト LM タイムアウト（秒） — 最終パイプ用は長め
LM_SHORT_TIMEOUT = int(os.environ.get("LM_SHORT_TIMEOUT", "12"))  # クエリ生成など短い操作用
LM_RETRIES = int(os.environ.get("LM_RETRIES", "1"))   # リトライ 1 回（合計2回）
# Reduce summarization batch to avoid long waits
WEB_DOCS_TO_SUMMARIZE = 2  # ← 要約するドキュメント数を減らす
NUM_SEARCH_QUERIES = 4    # 初期クエリ数（すでに反映されていればOK）
# ------------------------------------------------------------------

# priority / boost tokens (for restaurant-ish scoring; still used but less dominant)
PRIORITY_DOMAINS = ["tabelog.com", "retty.me", "hotpepper.jp", "jalan.net", "tripadvisor", "yelp", "gurunavi"]
BOOST_KEYWORDS = ["店", "営業時間", "住所", "ランチ", "ディナー", "口コミ", "評価", "レビュー"]

# -----------------------
# Init models (may be slow)
# -----------------------
embed_model = SentenceTransformer(EMBED_MODEL_NAME)
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("rag_docs")

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
def detect_search_intent(question: str) -> str:
    """
    Ask Qwen to classify intent: informational / local_search / news / other
    If LM fails, fallback simple heuristic:
      - contains words like 'どこ', '近く', 'ランチ', '店' -> local_search
      - contains 'いつ', 'なぜ', 'どうやって' -> informational
      - contains 'ニュース', '最新', '発表' -> news
      - else informational
    """
    system = "You are a concise intent classifier for search queries. Respond with a single token: informational / local_search / news / other."
    user = f"ユーザーの質問（日本語）: {question}\n\nReturn one of: informational, local_search, news, other"
    try:
        resp = lmstudio_chat(
            [{"role":"system","content":system},
             {"role":"user","content":user}],
            max_tokens=32,
            temperature=0.0,
            timeout=LM_SHORT_TIMEOUT   # ← 追加
        )

        text = resp['choices'][0]['message']['content'].strip().lower()
        for t in ["informational","local_search","news","other"]:
            if t in text:
                return t
    except Exception as e:
        log("[Intent] LM failed:", e)
    # fallback heuristics
    qlow = question.lower()
    local_tokens = ["近く", "ランチ", "店", "レストラン", "営業時間", "おいしい", "予約"]
    news_tokens = ["ニュース", "発表", "速報", "昨日", "今日"]
    info_tokens = ["なぜ", "どうやって", "いつ", "とは", "教えて", "標高", "定義", "意味"]
    if any(tok in qlow for tok in local_tokens):
        return "local_search"
    if any(tok in qlow for tok in news_tokens):
        return "news"
    if any(tok in qlow for tok in info_tokens):
        return "informational"
    return "informational"

# -----------------------
# 1) Query generation (intent-aware)
# -----------------------
def qwen_generate_search_queries(question: str, n: int = NUM_SEARCH_QUERIES) -> List[str]:
    intent = detect_search_intent(question)
    log("[Search Intent]", intent)
    # build a system prompt tailored by intent
    if intent == "local_search":
        sys_prompt = ("You are a search-query generator for local business searches (Japanese). Produce short, location-aware queries likely to hit local review/restaurant pages.")
        extra_instruction = "- Prefer terms like 'ランチ', '営業時間', '口コミ', '食べログ', '住所' etc."
    elif intent == "news":
        sys_prompt = ("You are a search-query generator for news-related searches (Japanese). Produce concise queries that would match news articles and official sources.")
        extra_instruction = "- Prefer terms like 'ニュース', '速報', '発表', '原因', '影響'."
    elif intent == "informational":
        sys_prompt = (
        "You are a search-query generator for factual informational search (Japanese). "
        "DO NOT add restaurant, food, travel, or local business related terms unless explicitly asked."
        )
        extra_instruction = "- Use factual terms only (definitions, numbers, official data)."
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

    user = (
        f"ユーザーの質問: {question}\n\n"
        f"出力ルール:\n- {extra_instruction}\n- 出力はJSON配列（日本語の文字列配列）で1行で返してください。\n"
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
    with DDGS() as ddgs:
        for q in queries:
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

def refine_queries_from_hits(hits: List[Dict], n_extra: int = 2) -> List[str]:
    if not hits:
        return []
    top_text = "\n".join([f"{i+1}. {h.get('title','')} - {h.get('body','')}" for i,h in enumerate(hits[:8])])
    prompt = (
        "以下は検索上位のタイトルとスニペットです。これを元にさらに掘るためのキーワードクエリを"
        f"日本語で{n_extra}個生成してください（短く）。\n\n{top_text}"
    )
    try:
        resp = lmstudio_chat([{"role":"system","content":"You are a search optimizer."},{"role":"user","content":prompt}], max_tokens=120, temperature=0.0, timeout=12)
        text = resp['choices'][0]['message']['content']
        lines = [l.strip(" -•\"'") for l in text.splitlines() if l.strip()]
        out = []
        for ln in lines:
            ln2 = re.sub(r'^[0-9]+[).:\-\s]*', '', ln)
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
            return r.text
    except Exception as e:
        log("[fetch_html] error:", url, e)
    return ""

BLACKLIST_DOMAINS = [
    "bing.com",
    "google.com",
    "doubleclick.net",
    "facebook.com",
    "twitter.com",
    "youtube.com",
    "xn--",
]

def extract_text(url: str, html: str = None) -> str:
    """
    Robust extraction:
    -domain blacklist(fast skip) 
    - trafilatura (if available)
    - readability
    - bs4 heavy-clean
    - final minimal fallback (title + first lines)
    """
    if any(bad in url for bad in BLACKLIST_DOMAINS):
        log(f"[extract_text] skipped by blacklist: {url}")
        return ""
    
    if html is None:
        html = fetch_html(url)

    if not html or len(html) < 200:
        log(f"[extract_text] empty HTML for {url}")
        return ""

    # Trafilatura
    if trafilatura is not None:
        try:
            txt = trafilatura.extract(html, include_comments=False, favor_precision=True)
            if txt and len(txt.strip()) > 220:
                return txt.strip()
        except Exception:
            pass

    # Readability
    if _HAS_READABILITY:
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

# -----------------------
# 5) summarization & extraction (LM with small max_tokens + fast fallback)
# -----------------------
# ---------- summarize_and_extract の差し替え（置き換え） ----------
def summarize_and_extract(text: str, title: str, url: str, intent: str) -> Tuple[str, Dict]:
    """
    Webページ本文から短い要約を生成する
    - intent や question には一切依存しない
    - LM失敗時はローカル抽出的要約にフォールバック
    """

    # パラメータ
    max_chars_to_send = 1200
    lm_max_tokens = 160
    lm_timeout = 30

    if intent == "informational":
        # LMを使わず、先頭数行だけ返す（高速）
        paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
        short = paras[0][:600] if paras else text[:600]
        return short, {}

    # --- 抜粋生成（先頭の意味ある行だけ） ---
    lines = [ln.strip() for ln in text.splitlines() if len(ln.strip()) >= 40]
    excerpt = "\n\n".join(lines)[:max_chars_to_send]

    if not excerpt:
        excerpt = text[:600]

    system = (
        "You are a concise Japanese summarizer. "
        "Summarize the article factually in 2-3 sentences."
    )

    user = f"""Title: {title}
URL: {url}

Article excerpt:
{excerpt}
"""

    try:
        resp = lmstudio_chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=lm_max_tokens,
            temperature=0.0,
            timeout=lm_timeout,
        )

        summary = resp["choices"][0]["message"]["content"].strip()

        if len(summary) > 1200:
            summary = summary[:1200] + "..."

        return summary, {"title": title, "url": url}

    except Exception as e:
        log("[Qwen] summarize_and_extract fallback:", e)

        # --- フォールバック：先頭段落 ---
        paras = [p.strip() for p in text.split("\n\n") if len(p.strip()) > 80]
        short = paras[0][:600] if paras else text[:600]

        return short, {"title": title, "url": url}


# -----------------------
# 6) Chroma search
# -----------------------
def search_chroma(query: str, n_results: int = 6) -> List[str]:
    try:
        q_emb = embed_model.encode([query])
        res = collection.query(query_embeddings=[q_emb[0]], n_results=n_results)
        docs = res.get("documents", [[]])[0]
        unique_docs = list(dict.fromkeys(docs))
        return unique_docs[:n_results]
    except Exception as e:
        log("[Chroma] query error:", e)
        return []

# -----------------------
# 7) context builder
# -----------------------
def build_context_and_truncate(chroma_docs: List[str], web_summaries: List[Tuple[str,str,str]], char_limit: int = CHARS_LIMIT) -> str:
    parts = []
    total = 0
    for d in chroma_docs:
        if not d:
            continue
        chunk = f"Document: {d}\n"
        if total + len(chunk) > char_limit:
            break
        parts.append(chunk)
        total += len(chunk)
    for title, summ, url in web_summaries:
        chunk = f"Source: {title}\nURL: {url}\n{summ}\n"
        if total + len(chunk) > char_limit:
            remaining = char_limit - total - len(f"Source: {title}\n")
            if remaining <= 0:
                break
            parts.append(f"Source: {title}\n{summ[:remaining]}...\n")
            total = char_limit
            break
        parts.append(chunk)
        total += len(chunk)
    return "\n".join(parts)

# -----------------------
# 8) final answer pipeline
# -----------------------
# ---------- final_answer_pipeline の LM 呼び出しタイムアウト調整（置き換え） ----------
def final_answer_pipeline(question: str, context: str) -> str:
    """
    Final answer generation for RAG.
    - Use ONLY the provided context
    - For factual / informational questions, do not speculate
    - If context is insufficient, explicitly say so
    """

    system = (
        "You are a factual QA assistant. "
        "Answer strictly based on the provided context in Japanese. "
        "If the answer cannot be determined from the context, reply exactly: INSUFFICIENT_CONTEXT"
    )

    user = f"""Context:
{context}

Question:
{question}

Rules:
- Use only the context above
- Do NOT add assumptions or external knowledge
- If the answer is not clearly stated, reply INSUFFICIENT_CONTEXT
"""

    try:
        resp = lmstudio_chat(
            [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=256,
            temperature=0.0,
            timeout=LM_TIMEOUT,
        )

        text = resp["choices"][0]["message"]["content"].strip()

        if text == "INSUFFICIENT_CONTEXT":
            return "該当する情報が文脈内に見つかりませんでした。"

        return text

    except Exception as e:
        log("[Qwen] final_answer_pipeline error:", e)
        return "回答生成中にエラーが発生しました。"

# =========================
# Answer builders
# =========================

def build_informational_answer(web_summaries, question):
    """
    informational 用（LMなし）
    - タイトルが質問語と無関係なものを除外
    """
    keywords = set(question.replace("？", "").replace("?", "").split())
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




def build_recommendation_answer(web_summaries):
    ...

# -----------------------
# Main flow
# -----------------------
def main():
    question = input("質問を入力してください: ").strip()
    if not question:
        print("質問が空です。")
        return

    start_time = time.time()
    log("=== STEP 1: Chroma 検索（拡張） ===")
    chroma_docs = search_chroma(question, n_results=6)
    for i,d in enumerate(chroma_docs,1):
        log(f"[Chroma #{i}] {str(d)[:200].replace(chr(10),' ')}")

    log("=== STEP 2: Qwen による強化検索クエリ生成 ===")
    queries = qwen_generate_search_queries(question, n=NUM_SEARCH_QUERIES)
    log("Generated queries:", queries)

    log("=== STEP 3: Wide ddgs 検索 ===")
    hits = ddgs_search_many(queries, per_query=DDGS_MAX_PER_QUERY)
    intent = detect_search_intent(question)

    # 🔥 informational は件数を強制制限（超高速化）
    if intent == "informational":
        hits = hits[:3]

    # recommendation / local / news は多めに保持
    elif intent in ("recommendation", "local_search", "news"):
        hits = hits[:10]


    log("=== STEP 4: Refine queries from top hits and re-search ===")

    intent = detect_search_intent(question)

    # --- refine queries（必要な intent のみ） ---
    if intent not in ("local_search", "news", "recommendation"):
        extra = []
    else:
        extra = refine_queries_from_hits(hits, n_extra=2)

        if extra:
            log("Refined queries:", extra)
            more_hits = ddgs_search_many(extra, per_query=6)

            before_keys = {h.get("href") or (h.get("title")+h.get("body")) for h in hits}
            for h in more_hits:
                key = h.get("href") or (h.get("title")+h.get("body"))
                if key not in before_keys:
                    hits.append(h)

    # --- unique filtering ---
    unique_hits = []
    seen = set()
    for h in hits:
        key = h.get("href") or (h.get("title","") + h.get("body",""))
        if not key or key in seen:
            continue
        seen.add(key)
        href = h.get("href","")
        if href.startswith(("https://www.bing.com/aclick", "https://www.google.com/url")):
            continue
        unique_hits.append(h)

    log(f"[Total unique hits] {len(unique_hits)}")

    # --- fetch & score ---
    scored = []
    for h in unique_hits:
        url = h.get("href","")
        title = h.get("title","")
        text = extract_text(url)

        if not text:
            continue

        score = score_text_for_restaurant(text, title=title, url=url)
        scored.append({"title": title, "url": url, "text": text, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    log(f"[Web] scored items: {len(scored)}")

    # --- summarize / extract ---
    web_summaries = []

    if intent == "informational":
        # 🧠 LMなし・爆速
        for item in scored[:2]:
            web_summaries.append(
                (
                    item["title"],
                    item["text"][:600],
                    item["url"]
                )
            )

    else:
        top_for_summary = scored[:WEB_DOCS_TO_SUMMARIZE]

        for item in tqdm(top_for_summary, desc="summarize"):
            summary, meta = summarize_and_extract(
                item["text"],
                item["title"] or item["url"],
                item["url"],
                intent
            )
            web_summaries.append((item["title"], summary, item["url"]))


    # embedding re-rank of summaries
    log("=== STEP 5: Re-rank by embedding similarity ===")
    q_emb = embed_model.encode([question])[0]
    re_ranked = []
    for title, summary, url in web_summaries:
        emb = embed_model.encode([summary])[0] if summary else np.zeros(384)
        denom = (np.linalg.norm(q_emb) * (np.linalg.norm(emb) + 1e-9))
        cosine = float(np.dot(q_emb, emb) / denom) if denom > 0 else 0.0
        # final combined score uses length heuristic (avoid tiny summaries)
        length_boost = min(1.0, max(0.0, len(summary) / 500.0))
        combined = cosine * 2.5 + length_boost
        re_ranked.append((combined, title, summary, url, cosine))
    re_ranked.sort(key=lambda x: x[0], reverse=True)
    final_web_list = [(t,s,u) for (_,t,s,u,_) in re_ranked]

    log("=== STEP 6: Build context and truncate ===")
    context = build_context_and_truncate(chroma_docs, final_web_list, char_limit=CHARS_LIMIT)
    log(f"[Context chars] {len(context)} / limit {CHARS_LIMIT}")

    log("=== STEP 7: Final Qwen pipeline (3-step) ===")
    intent = detect_search_intent(question)

    if intent == "informational":
        # LMを使わず、要約を結合して返す
        answer = build_informational_answer(web_summaries, question)
    elif intent == "recommendation":
        answer = build_recommendation_answer(web_summaries)
    else:
        answer = final_answer_pipeline(question, context)



    # outputs
    print("\n=== Chroma (抜粋) ===")
    for d in chroma_docs:
        print("-", str(d)[:400].replace("\n"," "))

    print("\n=== Web summaries (抜粋) ===")
    for idx, item in enumerate(re_ranked, 1):
        if not isinstance(item, (list, tuple)) or len(item) < 5:
            print(f"{idx}. Unexpected item: {item}")
            continue
        combined, title, summary, url, cosine = item
        print(f"{idx}. {title} ({url}) combined={combined:.3f} cosine={cosine:.3f}")
        print("   ", (summary or "")[:300].replace("\n", " "), "...")

    print("\n=== 最終回答 ===")
    print(answer)

    log(f"\nTotal time: {time.time() - start_time:.1f}s")

if __name__ == "__main__":
    main()
