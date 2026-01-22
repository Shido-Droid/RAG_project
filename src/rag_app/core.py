import time
import json
import re
import numpy as np
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Tuple, Any, Optional

from .config import (
    NUM_SEARCH_QUERIES, DDGS_MAX_PER_QUERY, CHARS_LIMIT, 
    LM_SHORT_TIMEOUT, LM_TIMEOUT, AnswerMode,
    HYBRID_ALPHA_DEFAULT, HYBRID_ALPHA_BY_INTENT,
    RERANK_CHUNK_SIZE, RERANK_CHUNK_OVERLAP, RERANK_TOP_K,
    RERANK_MAX_WEB_SOURCES
)
from .utils import log, safe_json_load, try_fast_path
from .llm import lmstudio_chat, generate_system_prompt
from .scraper import (
    extract_text, 
    score_text_for_restaurant, 
    score_text_for_spec,
    score_text_for_news,
    score_text_for_weather,
    score_text_for_informational
)
from .search import ddgs_search_many, refine_queries_from_hits
from .db import search_chroma, get_embed_model

# -----------------------
# Intent detection
# -----------------------
def detect_search_intent(question: str, history: List[Dict] = []) -> str:
    # 1. Fast heuristics
    qlow = question.lower()
    doc_tokens = ["このドキュメント", "この文書", "アップロード", "ファイル", "資料", "pdf", "要約", "抽出", "セクション", "章", "ドキュメント内検索", "ドキュメント検索"]
    for tok in doc_tokens:
        if tok in qlow:
            log(f"[Intent] Heuristic match: '{tok}' -> document_qa")
            return "document_qa"

    system = (
        "Classify intent into one of: informational / local_search / news / weather / document_qa / other\n\n"
        "Definitions:\n"
        "- document_qa: Questions explicitly about the *uploaded file content* (e.g., 'summarize this doc', 'what does section 3 say?'). If the user asks about a general topic that MIGHT be in the doc but doesn't explicitly reference 'this document', classify as 'informational'.\n"
        "- informational: General knowledge questions, definitions, technical terms, or facts (e.g., 'who is X?', 'release date of Y', 'what is RAG?').\n"
        "- news/weather: Questions about current events or weather.\n"
        "- local_search: Questions about shops, restaurants, places.\n"
        "- other: Greetings, chitchat."
    )
    
    history_text = ""
    if history:
        history_text = "Conversation History:\n" + "\n".join([f"- {h['role']}: {h['content']}" for h in history]) + "\n\n"

    user = f"{history_text}User Question: {question}\n\nReturn ONLY the label."
    try:
        resp = lmstudio_chat(
            [{"role":"system","content":system},
             {"role":"user","content":user}],
            max_tokens=32,
            temperature=0.0,
            timeout=LM_SHORT_TIMEOUT
        )
        text = resp.strip().lower()
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
    chat_tokens = ["こんにちは", "こんばんは", "おはよう", "ありがとう", "初めまして", "ようこそ", "調子はどう", "誰ですか", "名前は"]

    if any(tok in qlow for tok in chat_tokens):
        return "other"
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
        extra_instruction = "- Use factual terms. Expand acronyms if ambiguous. If the term refers to a famous AI model (e.g., Gemini), add 'Google' or 'AI' to disambiguate (e.g. 'Google Gemini')."
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
        text = resp
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
def collect_candidates(chroma_docs: List[Dict], scored_web: List[Dict], intent: str = "informational"):
    """
    Collect and chunk candidates for reranking.
    """
    candidates = []
    
    # 1. Local Docs
    for item in chroma_docs:
        text = item.get("text", "").strip()
        if not text: continue
        meta = item.get("meta", {})
        title = meta.get("title") or meta.get("source") or "Local Document"
        
        # Local docs authority: lower it for neutral informational searches to let vector relevance/web info compete
        # For informational, we want web to win if it's more relevant.
        h_score = 1.0 if intent == "informational" else 4.0
        
        candidates.append({
            "source": "chroma",
            "text": text,
            "h_score": h_score / 5.0, # normalize to 0-1
            "meta": {"title": title, "url": meta.get("source")}
        })

    # 2. Web Hits (Chunking)
    for item in scored_web:
        full_text = (item.get("text") or "").strip()
        if not full_text: continue
        
        # Heuristic score from scraper (already 0-5.0 approx)
        h_score_raw = item.get("score", 1.0)
        h_score = min(h_score_raw / 5.0, 1.0) # normalize
        
        # Chunking for finer reranking
        chunks = []
        if len(full_text) > RERANK_CHUNK_SIZE * 1.5:
            start = 0
            while start < len(full_text):
                end = start + RERANK_CHUNK_SIZE
                chunk = full_text[start:end]
                if len(chunk) > 100:
                    chunks.append(chunk)
                start += (RERANK_CHUNK_SIZE - RERANK_CHUNK_OVERLAP)
        else:
            chunks = [full_text]
            
        for chunk in chunks:
            candidates.append({
                "source": "web",
                "text": chunk,
                "h_score": h_score,
                "meta": {"title": item.get("title"), "url": item.get("url")}
            })
            
    return candidates

def rerank_candidates(question: str, candidates: List[Dict], intent: str = "informational", top_k: int = RERANK_TOP_K):
    if not candidates:
        return []
    
    alpha = HYBRID_ALPHA_BY_INTENT.get(intent, HYBRID_ALPHA_DEFAULT)
    log(f"[Rerank] Using hybrid alpha={alpha} for intent={intent}")
    
    model = get_embed_model()
    q_emb = model.encode([f"query: {question}"])[0]
    scored_candidates = []

    # Batch encode for efficiency if many candidates
    texts_to_embed = [f"passage: {c['text']}" for c in candidates if "emb" not in c]
    if texts_to_embed:
        embs = model.encode(texts_to_embed)
        idx = 0
        for c in candidates:
            if "emb" not in c:
                c["emb"] = embs[idx]
                idx += 1

    for c in candidates:
        emb = c["emb"]
        # Vector Similarity (0-1 approx)
        v_score = float(
            np.dot(q_emb, emb) / 
            (np.linalg.norm(q_emb) * np.linalg.norm(emb) + 1e-8)
        )
        
        # Hybrid Score
        h_score = c.get("h_score", 0.2)
        final_score = alpha * h_score + (1.0 - alpha) * v_score
        scored_candidates.append((final_score, c))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    
    return [c for _, c in scored_candidates[:top_k]]

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
            "あなたは学生の学習を支援する、知識豊富で親切な先生です。\n"
            "常に丁寧で、励ますような口調（「〜ですね」「〜ですよ」など）で日本語で話してください。\n"
            "【振る舞いのルール】\n"
            "1. **文脈がある場合**: 提供された【検索された文脈】（ドキュメントやWeb検索結果）に基づいて、学生に分かりやすく教えてください。\n"
            "2. **文脈がない場合（雑談など）**: 挨拶や雑談（「こんにちは」「ありがとう」など）に対しては、検索結果がなくてもあなたの知識や社交性を使って自然に返答してください。「情報がありません」と冷たく突き放してはいけません。\n"
            "3. **知識の補完と誤字訂正**: 質問に誤字（例：米津弦師）があっても、文脈中の正しい名称（例：米津玄師）を拾って柔軟に対応してください。\n"
            "4. **情報の限界**: 明らかに文脈にもあなたの知識にもない専門的な事実については、正直に「手元の資料には載っていないようです」と伝えてください。\n"
            "5. **情報の整合性**: 検索結果には、派生モデルやサードパーティのプレスリリースが含まれる場合があります。主語（「誰が」「何を」作ったか）を取り違えないよう注意してください。情報が矛盾する場合は、より信頼できると思われる情報源（公式ドキュメントや主要なWikiなど）を優先し、不確実な場合は併記してください。\n"
            "6. **言語の統一（重要）**: 【検索された文脈】が外国語（中国語や英語）であっても、必ず**自然な日本語**に翻訳・要約して回答してください。原文の漢字（例：基座、储备、量化）をそのまま使わず、適切な日本語（例：ベースモデル、蓄積、量子化）に直してください。\n\n"
            "【回答の可読性】\n"
            "- 適切な見出し（###など）や箇条書きを使って整理してください。\n"
            "- 重要なキーワードは**太字**にしてください。\n"
            "- 専門用語には `[[用語]]` のように二重角括弧をつけてください。"
        )
        if difficulty == "easy":
            system = base_system + "\n\n【回答スタイル: 初学者向け】\n専門用語はなるべく避け、初心者にもわかりやすい言葉で、比喩などを使いながら優しく教えてあげてください。"
        elif difficulty == "professional":
            system = base_system + "\n\n【回答スタイル: 専門的】\n先生として、より高度で実践的な視点から論理的に解説してください。"
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
        content = resp.strip()

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
                return resp.strip()
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
        content = resp.strip()
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
        return resp.strip()
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

    
    if intent == "other":
        log("=== Search skipped (conversational/other) ===")
        queries = []
        hits = []
        chroma_docs = []
    else:
        log("=== STEP 2: 検索クエリ生成 ===")
        queries = qwen_generate_search_queries(question, intent, history, n=NUM_SEARCH_QUERIES)
        log("Generated queries:", queries)

        log("=== STEP 3: 検索実行 (Chroma + Web) ===")
        # Chroma 検索: 元の質問と生成されたクエリの両方を使用
        all_search_terms = [question] + queries
        chroma_docs = []
        seen_ids = set()
        for q_term in all_search_terms:
            results = search_chroma(q_term, n_results=5)
            for r in results:
                # メタデータ内の ID または テキストのハッシュで重複排除
                # ここでは簡易的にソースとテキストの組み合わせで判定
                key = (r['meta'].get('source'), r['text'][:100])
                if key not in seen_ids:
                    seen_ids.add(key)
                    chroma_docs.append(r)
        
        if intent == "document_qa":
            log("=== Web search skipped (document_qa) ===")
            hits = []
        else:
            log("=== ddgs wide search ===")
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
    
    # Helper for parallel fetch
    def _fetch_content(h):
        u = h.get("href", "")
        return (h, extract_text(u))

    log(f"=== Parallel Fetch (max_workers=10) for {len(unique_hits)} hits ===")
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(_fetch_content, h) for h in unique_hits]
        
        for future in as_completed(futures):
            try:
                h, text = future.result()
                url = h.get("href","")
                title = h.get("title","")

                if not text or len(text) < 50:
                    snippet = h.get("body", "")
                    if snippet and len(snippet) > 30:
                        text = f"{snippet}\n(Note: Full content fetch failed, using search snippet.)"

                if not text:
                    continue

                # Intent-specific scoring
                if intent == "news":
                    score = score_text_for_news(text, title=title, url=url)
                elif intent == "weather":
                    score = score_text_for_weather(text, title=title, url=url)
                elif intent == "local_search":
                    score = score_text_for_restaurant(text, title=title, url=url)
                elif intent == "spec":
                    score = score_text_for_spec(text, title=title, url=url)
                elif intent == "informational":
                    score = score_text_for_informational(text, title=title, url=url)
                elif intent == "document_qa":
                    # For document_qa, use informational scoring as fallback
                    score = score_text_for_informational(text, title=title, url=url)
                else:
                    # Default to informational scoring
                    score = score_text_for_informational(text, title=title, url=url)

                scored.append({
                    "title": title,
                    "url": url,
                    "text": text,
                    "score": score
                })
            except Exception as e:
                log(f"[Parallel Fetch] Error processing hit: {e}")

    scored.sort(key=lambda x: x["score"], reverse=True)
    
    # Pre-filter: only chunk the top-N web sources based on heuristic score
    scored_top = [s for s in scored if s.get("score", 0) > 0.5] # Remove extremely low quality only
    scored_top = scored_top[:RERANK_MAX_WEB_SOURCES]
    log(f"[Performance] Pre-filtering: {len(scored)} -> {len(scored_top)} sources for chunking.")
    
    # STEP 6: summarize (collect/rerank)
    candidates = collect_candidates(chroma_docs, scored_top, intent=intent)
    ranked_candidates = rerank_candidates(question, candidates, intent=intent, top_k=RERANK_TOP_K)
    ranked_candidates = dedupe_by_similarity(ranked_candidates)

    log("=== STEP 7: context build ===")
    context = build_context_from_candidates(ranked_candidates)

    # STEP 8: final answer
    # STEP 8: final answer
    answer = final_answer_pipeline(question, context, history, intent=intent, difficulty=difficulty)

    sources = []
    seen_urls = set()
    for c in ranked_candidates:
        meta = c.get("meta", {})
        url = meta.get("url")
        if url:
            if url not in seen_urls:
                sources.append(meta)
                seen_urls.add(url)
        elif meta: # Local docs might not have URL but have title
             sources.append(meta)

    log(f"\nTotal time: {time.time() - start_time:.1f}s")
    return {"answer": answer, "sources": sources}

# Alias for cleaner naming in external scripts
execute_rag_pipeline = process_question
