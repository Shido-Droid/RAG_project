import chromadb
import time
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional

from .config import CHROMA_PATH, EMBED_MODEL_NAME
from .utils import log

# Init models (may be slow)
log(f"[DB] Loading embedding model: {EMBED_MODEL_NAME}")
embed_model = SentenceTransformer(EMBED_MODEL_NAME)

log(f"[DB] Connecting to ChromaDB at {CHROMA_PATH}")
client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_or_create_collection("rag_docs_e5")

def search_chroma(query: str, n_results: int = 6) -> List[Dict]:
    try:
        q_emb = embed_model.encode([f"query: {query}"])
        res = collection.query(query_embeddings=[q_emb[0]], n_results=n_results)
        
        documents = res.get("documents")
        docs = documents[0] if documents else []
        
        metadatas = res.get("metadatas")
        metas = metadatas[0] if metadatas else []
        
        # docs/metas が None の場合のガード
        if docs is None: docs = []
        if metas is None: metas = []
        
        results = []
        for d, m in zip(docs, metas):
            results.append({"text": d, "meta": m or {}})
        return results[:n_results]
    except Exception as e:
        log("[Chroma] query error:", e)
        return []

def add_document_to_kb(text: str, source: str, doc_metadata: Optional[Dict[str, Any]] = None):
    if not text:
        return

    if doc_metadata is None:
        doc_metadata = {}

    # Recursive splitting with overlap
    def recursive_split_text(text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        if not text:
            return []
        
        # Split by logical delimiters
        delimiters = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", " "]
        segments = [text]
        
        for d in delimiters:
            new_segments = []
            for s in segments:
                if len(s) > chunk_size:
                    # Split this segment further
                    parts = s.split(d)
                    # Re-attach delimiter (except split by space)
                    if d != " ":
                        parts = [p + d for p in parts[:-1]] + [parts[-1]]
                    new_segments.extend([p for p in parts if p])
                else:
                    new_segments.append(s)
            segments = new_segments
        
        # Recombine into chunks with overlap
        final_chunks = []
        current_chunk = ""
        
        for s in segments:
            if len(current_chunk) + len(s) > chunk_size:
                if current_chunk:
                    final_chunks.append(current_chunk)
                    # Start new chunk with overlap from end of previous
                    overlap_len = min(len(current_chunk), overlap)
                    current_chunk = current_chunk[-overlap_len:] + s
                else:
                    # Segment itself is too large, force split (should be rare due to recursive logic)
                    final_chunks.append(s[:chunk_size])
                    current_chunk = s[chunk_size:]
            else:
                current_chunk += s
        
        if current_chunk:
            final_chunks.append(current_chunk)
            
        return final_chunks

    chunks = recursive_split_text(text, chunk_size=500, overlap=100)
    
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
