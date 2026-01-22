import requests
import re
from urllib.parse import urlparse
from typing import Optional
from bs4 import BeautifulSoup

from .config import (
    USER_AGENT, REQUESTS_TIMEOUT, VERBOSE, 
    PRIORITY_DOMAINS, BOOST_KEYWORDS, 
    BLACKLIST_DOMAINS, WHITELIST_DOMAINS,
    DOMAIN_AUTHORITY, NEWS_KEYWORDS, WEATHER_KEYWORDS, INFORMATIONAL_KEYWORDS,
    RESTAURANT_KEYWORDS, SPEC_KEYWORDS
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
        # Skip Trafilatura for weather sites (tenki.jp, etc) as it often strips data tables
        is_weather_site = any(wd in domain for wd in ["tenki.jp", "weather", "kishou", "jma.go.jp"])
        if not is_weather_site:
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
            if len(ln) < 10:  # Relaxed from 30 for weather/price data
                # Keep short lines if they look like weather or data
                if not any(k in ln for k in ["℃", "%", "円", "晴", "雨", "曇", "雪", "/", ":"]):
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
    """
    Score text for restaurant intent.
    Prioritizes: domain authority, restaurant-specific details (hours, price, location).
    """
    # 1. Domain Authority (0-5.0, weight: 0.3)
    domain_score = get_domain_authority(url, "local_search")
    
    # 2. Content Quality (0-3.0, weight: 0.2)
    quality_score = get_content_quality_score(text, optimal_min=200, optimal_max=1500)
    
    # 3. Relevance - Restaurant Keywords (0-3.0, weight: 0.2)
    relevance_score = count_keyword_density(text + " " + title, RESTAURANT_KEYWORDS)
    
    # 4. Features (0-2.0, weight: 0.3)
    feature_score = 0.0
    combined = (title + "\n" + text).lower()
    
    # Hours existence
    if re.search(r"\d{1,2}:\d{2}", combined) or "営業時間" in combined:
        feature_score += 0.5
        
    # Price info
    if re.search(r"円", combined) or re.search(r"¥", combined):
        feature_score += 0.5
        
    # Location info
    if re.search(r"\d{3}-\d{4}", combined) or "〒" in combined or "住所" in combined:
        feature_score += 0.5
        
    # Reviews/Menu mention
    if "口コミ" in combined or "メニュー" in combined:
        feature_score += 0.5
        
    feature_score = min(feature_score, 2.0)
    
    # Final weighted score
    final_score = (
        domain_score * 0.3 +
        quality_score * 0.2 +
        relevance_score * 0.2 +
        feature_score * 0.3
    )
    return final_score

def score_text_for_spec(text: str, title: str = "", url: str = "") -> float:
    """
    Score text for technical specification/API intent.
    Prioritizes: official docs (domain), version info, code-like structure.
    """
    # 1. Domain Authority (0-5.0, weight: 0.4)
    domain_score = get_domain_authority(url, "spec")
    
    # 2. Content Quality (0-3.0, weight: 0.2)
    quality_score = get_content_quality_score(text, optimal_min=500, optimal_max=5000)
    
    # 3. Relevance - Spec Keywords (0-3.0, weight: 0.2)
    relevance_score = count_keyword_density(text + " " + title, SPEC_KEYWORDS)
    
    # 4. Features (0-2.0, weight: 0.2)
    feature_score = 0.0
    combined = (title + " " + text).lower()
    
    # Versioning
    if re.search(r"v\d+(\.\d+)*", combined) or "version" in combined:
        feature_score += 0.5
        
    # Date/Recency in context of release
    if re.search(r"202[4-6]", combined):
        feature_score += 0.5
        
    # Code blocks or API endpoint structure /method/
    if "```" in text or re.search(r"GET|POST|PUT|DELETE", text):
        feature_score += 0.5
        
    # Structure (bullet points for params)
    if text.count("- ") > 5:
        feature_score += 0.5

    feature_score = min(feature_score, 2.0)

    # Final weighted score
    final_score = (
        domain_score * 0.4 +
        quality_score * 0.2 +
        relevance_score * 0.2 +
        feature_score * 0.2
    )
    return final_score

# -----------------------
# Helper Functions
# -----------------------
def get_domain_authority(url: str, intent: str) -> float:
    """
    Get domain authority score based on URL and intent.
    Returns a score between 1.0 (default) and 5.0 (highest authority).
    """
    if not url:
        return 1.0
    
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Remove 'www.' prefix
    if domain.startswith("www."):
        domain = domain[4:]
    
    # Get intent-specific domain authority
    intent_domains = DOMAIN_AUTHORITY.get(intent, {})
    
    # Check for exact match
    if domain in intent_domains:
        return intent_domains[domain]
    
    # Check for partial match (e.g., "maps.google.com" matches "google.com")
    for auth_domain, score in intent_domains.items():
        if auth_domain in domain:
            return score
    
    # Default score
    return 1.0

def count_keyword_density(text: str, keywords: list) -> float:
    """
    Count keyword density in text.
    Returns a score based on how many keywords are found.
    """
    if not text:
        return 0.0
    
    text_lower = text.lower()
    count = sum(1 for keyword in keywords if keyword in text_lower)
    
    # Normalize by text length (per 1000 chars)
    density = (count / max(len(text), 1)) * 1000
    return min(density, 3.0)  # Cap at 3.0

def get_content_quality_score(text: str, optimal_min: int = 300, optimal_max: int = 2000) -> float:
    """
    Evaluate content quality based on length and structure.
    """
    if not text:
        return 0.0
    
    score = 0.0
    text_len = len(text)
    
    # Length score (optimal range: 300-2000 chars)
    if optimal_min <= text_len <= optimal_max:
        score += 2.0
    elif text_len > optimal_max:
        score += 1.5
    elif text_len > 150:
        score += 1.0
    else:
        score += 0.3
    
    # Paragraph structure (multiple line breaks indicate structure)
    paragraph_count = text.count('\n\n')
    if paragraph_count >= 3:
        score += 0.5
    elif paragraph_count >= 1:
        score += 0.3
    
    # Numeric data presence
    if re.search(r'\d+', text):
        score += 0.5
    
    return min(score, 3.0)  # Cap at 3.0

# -----------------------
# Intent-Specific Scoring Functions
# -----------------------
def score_text_for_news(text: str, title: str = "", url: str = "") -> float:
    """
    Score text for news intent.
    Prioritizes: domain authority, freshness, news keywords, content quality.
    """
    # 1. Domain Authority (0-5.0, weight: 0.4)
    domain_score = get_domain_authority(url, "news")
    
    # 2. Content Quality (0-3.0, weight: 0.3)
    quality_score = get_content_quality_score(text, optimal_min=300, optimal_max=2000)
    
    # 3. Relevance - News Keywords (0-3.0, weight: 0.2)
    relevance_score = count_keyword_density(text + " " + title, NEWS_KEYWORDS)
    
    # 4. Freshness (0-2.0, weight: 0.1)
    freshness_score = 0.0
    combined = (text + " " + title).lower()
    
    # Recent year mentions
    if "2026" in combined:
        freshness_score += 1.0
    elif "2025" in combined:
        freshness_score += 0.8
    elif "2024" in combined:
        freshness_score += 0.5
    
    # Time indicators
    time_indicators = ["今日", "本日", "昨日", "速報", "最新"]
    if any(indicator in combined for indicator in time_indicators):
        freshness_score += 0.5
    
    # Date format (YYYY年MM月DD日)
    if re.search(r'20\d{2}年\d{1,2}月\d{1,2}日', combined):
        freshness_score += 0.5
    
    freshness_score = min(freshness_score, 2.0)
    
    # Final weighted score
    final_score = (
        domain_score * 0.4 +
        quality_score * 0.2 +
        relevance_score * 0.2 +
        freshness_score * 0.2
    )
    
    return final_score

def score_text_for_weather(text: str, title: str = "", url: str = "") -> float:
    """
    Score text for weather intent.
    Prioritizes: domain authority, weather data presence, freshness.
    """
    # 1. Domain Authority (0-5.0, weight: 0.5) - Higher weight for weather
    domain_score = get_domain_authority(url, "weather")
    
    # 2. Content Quality (0-3.0, weight: 0.2)
    quality_score = get_content_quality_score(text, optimal_min=200, optimal_max=1500)
    
    # 3. Relevance - Weather Keywords (0-3.0, weight: 0.2)
    relevance_score = count_keyword_density(text + " " + title, WEATHER_KEYWORDS)
    
    # 4. Weather Data Presence (0-2.0, weight: 0.1)
    data_score = 0.0
    combined = text + " " + title
    
    # Temperature data
    if re.search(r'\d+℃', combined) or re.search(r'\d+度', combined):
        data_score += 0.5
    
    # Precipitation probability
    if re.search(r'\d+%', combined) or "降水確率" in combined:
        data_score += 0.5
    
    # Time-based forecast
    time_keywords = ["今日", "明日", "週間", "時間ごと", "3時間"]
    if any(kw in combined for kw in time_keywords):
        data_score += 0.5
    
    # Location info
    if re.search(r'[都道府県市区町村]', combined):
        data_score += 0.5
    
    data_score = min(data_score, 2.0)
    
    # Final weighted score
    final_score = (
        domain_score * 0.45 +
        quality_score * 0.2 +
        relevance_score * 0.15 +
        data_score * 0.2
    )
    
    return final_score

def score_text_for_informational(text: str, title: str = "", url: str = "") -> float:
    """
    Score text for informational intent.
    Prioritizes: domain authority, content quality, explanatory keywords.
    """
    # 1. Domain Authority (0-5.0, weight: 0.3)
    domain_score = get_domain_authority(url, "informational")
    
    # 2. Content Quality (0-3.0, weight: 0.4) - Higher weight for informational
    quality_score = get_content_quality_score(text, optimal_min=400, optimal_max=3000)
    
    # 3. Relevance - Informational Keywords (0-3.0, weight: 0.2)
    relevance_score = count_keyword_density(text + " " + title, INFORMATIONAL_KEYWORDS)
    
    # 4. Structure & References (0-2.0, weight: 0.1)
    structure_score = 0.0
    combined = text + " " + title
    
    # Headings/sections
    if re.search(r'[第章節]', combined):
        structure_score += 0.5
    
    # Lists/bullet points
    if combined.count('・') >= 3 or combined.count('、') >= 5:
        structure_score += 0.5
    
    # References/citations
    citation_keywords = ["参考", "出典", "引用", "文献", "source"]
    if any(kw in combined.lower() for kw in citation_keywords):
        structure_score += 0.5
    
    # Educational content indicators
    edu_keywords = ["例えば", "具体的", "つまり", "すなわち"]
    if any(kw in combined for kw in edu_keywords):
        structure_score += 0.5
    
    structure_score = min(structure_score, 2.0)
    
    # Final weighted score
    final_score = (
        domain_score * 0.3 +
        quality_score * 0.3 +
        relevance_score * 0.2 +
        structure_score * 0.2
    )
    
    return final_score

