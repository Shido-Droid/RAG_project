import time
import re
from typing import List, Dict, Any

from .config import DDGS_MAX_PER_QUERY, DDGS_USE_NEWS
from .utils import log
from .llm import lmstudio_chat

# ddgs import with fallback
try:
    from ddgs import DDGS  # preferred
except Exception:
    try:
        from duckduckgo_search import DDGS  # older package
    except Exception:
        DDGS = None

def ddgs_search_many(queries: List[str], per_query: int = DDGS_MAX_PER_QUERY) -> List[Dict]:
    results = []
    if DDGS is None:
        log("[DDGS] ddgs/duckduckgo not available.")
        return results

    try:
        ddgs: Any = DDGS()
        for i, q in enumerate(queries):
            if i > 0:
                time.sleep(1.0)  # avoid gzip error
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
    """
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
