import time
import json
import re
import numpy as np
from typing import List, Dict, Tuple, Any, Optional

from .config import (
    NUM_SEARCH_QUERIES, DDGS_MAX_PER_QUERY, CHARS_LIMIT, 
    LM_SHORT_TIMEOUT, LM_TIMEOUT, AnswerMode
)
from .utils import log, safe_json_load, try_fast_path
from .llm import lmstudio_chat
from .scraper import extract_text, score_text_for_restaurant, score_text_for_spec
from .search import ddgs_search_many, refine_queries_from_hits
from .db import search_chroma, embed_model

# -----------------------
# Intent detection
# -----------------------
def detect_search_intent(question: str, history: List[Dict] = []) -> str:
    # 1. Fast heuristics
    qlow = question.lower()
    doc_tokens = ["このドキュメント", "この文書", "アップロード", "ファイル", "資料", "pdf", "要約", "抽出", "セクション", "章"]
    for tok in doc_tokens:
        if tok in qlow:
            log(f"[Intent] Heuristic match: '{tok}' -> document_qa")
            return "document_qa"

    system = "Classify intent: informational / spec / factual / local_search / news / weather / document_qa / other"
    
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
            timeout=LM_SHORT_TIMEOUT
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
# Query generation
# -----------------------
def qwen_generate_search_queries(question: str, intent: str, history: List[Dict] = [], n: int = NUM_SEARCH_QUERIES) -> List[str]:
    log("[Search Intent]", intent)
    if intent == "local_search":
        sys_prompt = "You are a search-query generator for local business searches (Japanese)."
        extra_instruction = "- Prefer terms like 'ランチ', '営業時間', '口コミ', '食べログ', '住所' etc."
    elif intent == "news":
        sys_prompt = "You are a search-query generator for news-related searches (Japanese)."
        extra_instruction = "- Prefer terms like 'ニュース', '速報', '発表', '原因', '影響'."
    elif intent == "weather":
        sys_prompt = "You are a search-query generator for weather forecasts (Japanese)."
        extra_instruction = "- Prefer terms like '天気', '1時間ごと', '週間予報', '気象庁'."
    elif intent == "informational":
        sys_prompt = "You are a search-query generator for factual informational search (Japanese)."
        extra_instruction = "- Use factual terms. Expand acronyms if ambiguous."
    else:
        sys_prompt = "You are a search-query generator for general informational search (Japanese)."
        extra_instruction = "- Use neutral factual keywords only."

    history_text = ""
    if history:
        history_text = "会話履歴:\n" + "\n".join([f"- {h['role']}: {h['content']}" for h in history]) + "\n\n"

    user = (
        f"{history_text}ユーザーの質問: {question}\n\n"
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

    base = question.strip()
    if intent == "local_search":
        variants = [f"{base} ランチ", f"{base} 営業時間", f"{base} 口コミ", f"{base} 食べログ"]
    elif intent == "news":
        variants = [f"{base} ニュース", f"{base} 速報", f"{base} 発表"]
    elif intent == "weather":
        variants = [f"{base} 天気", f"{base} 予報", f"{base} 気象庁"]
    else:
        variants = [base, base + " とは", base + " 意味", base + " データ"]
    
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
# Context Helpers
# -----------------------
def collect_candidates(chroma_docs, scored_web, min_chars: int = 50):
    candidates = []
    for item in chroma_docs:
        text = item.get("text", "").strip()
        if len(text) < min_chars:
            continue
        meta = item.get("meta", {})
        title = meta.get("title") or meta.get("source") or "Local Document"
        candidates.append({
            "source": "chroma",
            "text": text,
            "meta": {"title": title, "url": meta.get("source")}
        })

    for item in scored_web:
        text = (item.get("text") or "").strip()
        if len(text) < min_chars:
            continue
        candidates.append({
            "source": "web",
            "text": text,
            "meta": {"title": item.get("title"), "url": item.get("url")}
        })
    return candidates

def rerank_candidates(question, candidates, top_k=8):
    if not candidates:
        return []
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
# Final Answer Pipeline
# -----------------------
def final_answer_pipeline(question: str, context: str, history: List[Dict] = [], intent: str = "informational", difficulty: str = "normal") -> str:
    if intent == "weather":
        system = (
            "あなたは天気予報のアシスタントです。\n"
            "【検索された文脈】にある気象データ（気温、降水確率、風速など）を整理して伝えてください。\n"
        )
    else:
        base_system = (
            "あなたは与えられた情報のみに基づいて回答するアシスタントです。\n"
            "日本語で回答してください。\n"
            "以下の【検索された文脈】に含まれている情報だけを使って、質問に答えてください。\n"
            "もし文脈の中に答えが全くない場合は、「提供された情報からは分かりません」とだけ答えてください。\n"
            "【重要】回答の可読性を高めるため、以下のルールを守ってください：\n"
            "1. 適切な見出し（###など）を使い、情報を構造化してください。\n"
            "2. 箇条書きを積極的に使い、長文を避けてください。\n"
            "3. 重要なキーワードは**太字**にしてください。\n"
            "4. 回答に専門用語を含める場合は、必ずその用語を `[[専門用語]]` のように二重角括弧で囲ってください。"
        )
        if difficulty == "easy":
            system = base_system + "\n\n【回答スタイル: 初学者向け】\n専門用語はなるべく避け、初心者にもわかりやすい言葉で、丁寧に噛み砕いて説明してください。"
        elif difficulty == "professional":
            system = base_system + "\n\n【回答スタイル: 専門的】\n専門用語を適切に使用し、簡潔かつ論理的に、実務的・専門的な観点から詳細に回答してください。"
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
            "回答に含まれる重要な専門用語、システム名、機能名などは、必ず `[[用語]]` のように二重角括弧で囲ってください。"
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

# -----------------------
# Other Analysis Tools
# -----------------------
def analyze_document_content(text: str) -> Dict[str, Any]:
    if not text:
        return {}
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
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
        return safe_json_load(content) or {}
    except Exception as e:
        log(f"[Analyze] Error: {e}")
        return {}

def explain_term(term: str) -> str:
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

# -----------------------
# Main Process
# -----------------------
def process_question(question: str, history: List[Dict] = [], difficulty: str = "normal") -> dict:
    fast = try_fast_path(question)
    if fast is not None:
        return {"answer": fast, "sources": []}
    start_time = time.time()

    intent = detect_search_intent(question, history)
    log(f"[Intent] {intent}")

    log("=== STEP 1: Chroma 検索 ===")
    chroma_docs = search_chroma(question, n_results=10)

    if intent == "document_qa":
        log("=== STEP 2 & 3: Web search skipped (document_qa) ===")
        queries = []
        hits = []
    else:
        log("=== STEP 2: 検索クエリ生成 ===")
        queries = qwen_generate_search_queries(question, intent, history, n=NUM_SEARCH_QUERIES)
        log("Generated queries:", queries)

        log("=== STEP 3: ddgs wide search ===")
        hits = ddgs_search_many(queries, per_query=DDGS_MAX_PER_QUERY)

        if intent == "informational":
            hits = hits[:5]
        elif intent in ("local_search", "news", "recommendation", "weather"):
            hits = hits[:10]

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

    # STEP 5: unique + fetch + score
    unique_hits = []
    seen = set()
    for h in hits:
        key = h.get("href") or (h.get("title","") + h.get("body",""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique_hits.append(h)

    scored = []
    for h in unique_hits:
        url = h.get("href","")
        title = h.get("title","")
        text = extract_text(url)

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
    
    # STEP 6: summarize (collect/rerank)
    candidates = collect_candidates(chroma_docs, scored)
    ranked_candidates = rerank_candidates(question, candidates, top_k=20)
    ranked_candidates = dedupe_by_similarity(ranked_candidates)

    sources = []
    seen_urls = set()
    for c in ranked_candidates:
        url = c["meta"].get("url")
        title = c["meta"].get("title")
        if url and url not in seen_urls:
            sources.append({"title": title, "url": url})
            seen_urls.add(url)

    log("=== STEP 7: context build ===")
    context = build_context_from_candidates(ranked_candidates)

    # STEP 8: final answer
    answer = final_answer_pipeline(question, context, history, intent=intent, difficulty=difficulty)

    log(f"\nTotal time: {time.time() - start_time:.1f}s")
    return {"answer": answer, "sources": sources}
