import requests
import re
from urllib.parse import urlparse
from typing import Optional
from bs4 import BeautifulSoup

from .config import (
    USER_AGENT, REQUESTS_TIMEOUT, VERBOSE, 
    PRIORITY_DOMAINS, BOOST_KEYWORDS, 
    BLACKLIST_DOMAINS, WHITELIST_DOMAINS
)
from .utils import log

# optional libs
try:
    import trafilatura
except Exception:
    trafilatura = None

try:
    from readability import Document as ReadabilityDocument
    _HAS_READABILITY = True
except Exception:
    ReadabilityDocument = None
    _HAS_READABILITY = False

def fetch_html(url: str) -> str:
    if not url:
        return ""
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=REQUESTS_TIMEOUT)
        if r.status_code == 200 and r.content:
            r.encoding = r.apparent_encoding or "utf-8"
            return r.text
    except Exception as e:
        log("[fetch_html] error:", url, e)
    return ""

def extract_text(url: str, html: Optional[str] = None) -> str:
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

    # Sanitize HTML
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

    # Final minimal fallback
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

    if any(k in url for k in ["google.com", "ai.google.dev"]):
        score += 3.0

    spec_keywords = [
        "version", "バージョン", "release", "changelog",
        "api", "model", "仕様", "対応", "更新"
    ]
    score += sum(0.3 for k in spec_keywords if k in t)

    if any(ch.isdigit() for ch in text):
        score += 0.5

    if any(k in t for k in ["2024", "2025", "月", "日"]):
        score += 0.5

    return score
