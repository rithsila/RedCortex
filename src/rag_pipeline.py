#!/usr/bin/env python3
"""
Enhanced RAG Pipeline with:
- Hybrid Search (Vector + BM25)
- Cross-encoder Reranking
- Query Caching
"""
import os
import sys
import sqlite3
import hashlib
import json
import time
import pickle
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import httpx
import requests
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from rank_bm25 import BM25Okapi
from utils.query_logger import QueryLogger

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "books_hot"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")

# Initialize query logger
query_logger = QueryLogger()
MODEL_DEFAULT = "qwen/qwen3-coder"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Cache configuration
CACHE_DIR = "data/cache"
CACHE_TTL = 24 * 3600  # 24 hours in seconds


def get_embedding(text: str) -> list[float]:
    """Get embedding from Ollama using direct HTTP API"""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={
                    "model": EMBED_MODEL,
                    "prompt": text[:1500]
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
    except Exception as e:
        raise Exception(f"Embedding error: {e}")


def ensure_cache_dir():
    """Ensure cache directory exists"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)


def get_cache_key(query: str, model: str, top_k: int) -> str:
    """Generate deterministic cache key"""
    content = f"{model}:{query}:{top_k}"
    return hashlib.sha256(content.encode()).hexdigest()


def get_cached_response(cache_key: str) -> Optional[Dict]:
    """Get cached response if exists and not expired"""
    ensure_cache_dir()
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    if not os.path.exists(cache_file):
        return None
    
    try:
        with open(cache_file, 'r') as f:
            cached = json.load(f)
        
        # Check if cache is still valid
        if time.time() - cached.get("timestamp", 0) < CACHE_TTL:
            return cached.get("data")
    except Exception:
        pass
    
    return None


def cache_response(cache_key: str, data: Dict):
    """Cache response with timestamp"""
    ensure_cache_dir()
    cache_file = os.path.join(CACHE_DIR, f"{cache_key}.json")
    
    try:
        with open(cache_file, 'w') as f:
            json.dump({
                "timestamp": time.time(),
                "data": data
            }, f)
    except Exception as e:
        print(f"Warning: Failed to cache response: {e}")


@dataclass
class SearchResult:
    """Unified search result structure"""
    chunk_id: int
    content: str
    page_start: int
    page_end: int
    book_id: int
    score: float
    source: str  # 'vector', 'bm25', or 'hybrid'


def reciprocal_rank_fusion(
    vector_results: List[SearchResult],
    keyword_results: List[SearchResult],
    k: float = 60.0
) -> List[SearchResult]:
    """
    Combine vector and keyword search results using Reciprocal Rank Fusion.
    RRF score = 1 / (k + rank) for each result list.
    """
    scores: Dict[int, float] = {}
    result_map: Dict[int, SearchResult] = {}
    
    # Process vector results (rank starts at 1)
    for rank, result in enumerate(vector_results, 1):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0) + 1.0 / (k + rank)
        result_map[result.chunk_id] = result
    
    # Process keyword results
    for rank, result in enumerate(keyword_results, 1):
        scores[result.chunk_id] = scores.get(result.chunk_id, 0) + 1.0 / (k + rank)
        if result.chunk_id not in result_map:
            result_map[result.chunk_id] = result
    
    # Sort by RRF score
    sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    
    fused_results = []
    for chunk_id in sorted_ids:
        result = result_map[chunk_id]
        result.score = scores[chunk_id]
        result.source = "hybrid"
        fused_results.append(result)
    
    return fused_results


def build_bm25_index(db: sqlite3.Connection) -> Tuple[BM25Okapi, List[Dict]]:
    """Build BM25 index from all chunks in the database"""
    cursor = db.execute("""
        SELECT id, content, page_start, page_end, book_id 
        FROM chunks 
        WHERE is_hot = 1
    """)
    
    chunks = []
    tokenized_corpus = []
    
    for row in cursor.fetchall():
        chunk = {
            "id": row[0],
            "content": row[1],
            "page_start": row[2],
            "page_end": row[3],
            "book_id": row[4]
        }
        chunks.append(chunk)
        # Simple tokenization
        tokens = row[1].lower().split()
        tokenized_corpus.append(tokens)
    
    if not tokenized_corpus:
        return None, []
    
    bm25 = BM25Okapi(tokenized_corpus)
    return bm25, chunks


def vector_search(
    query: str, 
    top_k: int = 20,
    db: sqlite3.Connection = None
) -> List[SearchResult]:
    """Perform vector search using Qdrant"""
    query_vec = get_embedding(query)
    
    qdrant = QdrantClient(
        url=os.getenv("QDRANT_URL"),
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    results = qdrant.query_points(
        collection_name=COLLECTION_NAME,
        query=query_vec,
        limit=top_k,
        with_payload=True
    ).points
    
    search_results = []
    for hit in results:
        payload = hit.payload
        parent_id = payload.get("parent_id")
        
        if db:
            cursor = db.execute(
                "SELECT content, page_start, page_end, book_id FROM chunks WHERE id = ?",
                (parent_id,)
            )
            row = cursor.fetchone()
            if row:
                search_results.append(SearchResult(
                    chunk_id=parent_id,
                    content=row[0],
                    page_start=row[1],
                    page_end=row[2],
                    book_id=row[3],
                    score=hit.score,
                    source="vector"
                ))
    
    return search_results


def keyword_search(
    query: str,
    bm25: BM25Okapi,
    chunks: List[Dict],
    top_k: int = 20
) -> List[SearchResult]:
    """Perform BM25 keyword search"""
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    
    # Get top-k indices
    top_indices = np.argsort(scores)[::-1][:top_k]
    
    search_results = []
    for idx in top_indices:
        if scores[idx] > 0:
            chunk = chunks[idx]
            search_results.append(SearchResult(
                chunk_id=chunk["id"],
                content=chunk["content"],
                page_start=chunk["page_start"],
                page_end=chunk["page_end"],
                book_id=chunk["book_id"],
                score=float(scores[idx]),
                source="bm25"
            ))
    
    return search_results


def rerank_results(
    query: str,
    results: List[SearchResult],
    top_k: int = 5
) -> List[SearchResult]:
    """
    Rerank results using cross-encoder.
    For now, uses a simple heuristic-based reranking as fallback.
    In production, use sentence-transformers cross-encoder.
    """
    try:
        # Try to import and use cross-encoder
        from sentence_transformers import CrossEncoder
        
        model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        
        pairs = [(query, result.content[:512]) for result in results]
        scores = model.predict(pairs)
        
        # Update scores and sort
        for i, result in enumerate(results):
            result.score = float(scores[i])
        
        return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]
        
    except Exception:
        # Fallback: Simple heuristic reranking
        query_terms = set(query.lower().split())
        
        for result in results:
            content_lower = result.content.lower()
            # Boost score based on term overlap
            term_matches = sum(1 for term in query_terms if term in content_lower)
            boost = term_matches / len(query_terms) if query_terms else 0
            result.score = result.score * (1 + boost)
        
        return sorted(results, key=lambda x: x.score, reverse=True)[:top_k]


def hybrid_search(
    query: str,
    top_k: int = 5,
    enable_hybrid: bool = True
) -> Tuple[List[SearchResult], str]:
    """
    Perform hybrid search with optional BM25 and reranking.
    Returns (results, search_method_used).
    """
    db = sqlite3.connect("data/library.db")
    
    try:
        # Always do vector search
        vector_results = vector_search(query, top_k=20, db=db)
        
        if not enable_hybrid:
            reranked = rerank_results(query, vector_results, top_k)
            return reranked, "vector+rerank"
        
        # Try BM25 search
        bm25, chunks = build_bm25_index(db)
        
        if bm25 and chunks:
            keyword_results = keyword_search(query, bm25, chunks, top_k=20)
            
            # Fuse results
            fused = reciprocal_rank_fusion(vector_results, keyword_results)
            
            # Rerank top results
            reranked = rerank_results(query, fused, top_k)
            return reranked, "hybrid+rerank"
        else:
            reranked = rerank_results(query, vector_results, top_k)
            return reranked, "vector+rerank"
            
    finally:
        db.close()


def format_context(results: List[SearchResult]) -> Tuple[str, List[str]]:
    """Format search results into context string and sources"""
    contexts = []
    sources = []
    
    for result in results:
        context_text = f"[Page {result.page_start}]: {result.content[:800]}"
        contexts.append(context_text)
        sources.append(f"Page {result.page_start} (score: {result.score:.3f}, source: {result.source})")
    
    return "\n\n".join(contexts), sources


def query_llm(question: str, context: str, model: str, search_method: str = "unknown", sources_count: int = 0) -> Tuple[str, str, str]:
    """Send query to OpenRouter with caching and logging"""
    
    start_time = time.time()
    cache_key = get_cache_key(question, model, 5)
    cached = get_cached_response(cache_key)
    
    if cached:
        # Log cached query
        latency_ms = int((time.time() - start_time) * 1000)
        query_logger.log_query(
            query=question,
            answer=cached["answer"],
            model_used=model,
            search_method=search_method,
            latency_ms=latency_ms,
            sources_count=sources_count,
            cache_hit=True,
            tokens_used=None,
            cost_usd=0.0  # No cost for cached queries
        )
        return cached["answer"], cached["cost_info"], cached["model"] + " (cached)"
    
    system_prompt = """You are a helpful technical assistant with access to Red Hat Enterprise Linux documentation.
Answer the user's question based ONLY on the provided context.
If the context doesn't contain the answer, say "I don't have enough information in my knowledge base to answer this."
Always cite the page numbers you used to formulate your answer.
Be concise and technical."""

    user_prompt = f"""Context from Red Hat System Administration I (RHEL 9.0):
---
{context}
---

Question: {question}

Provide a clear, technical answer citing page numbers."""

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "max_tokens": 1000
    }
    
    try:
        response = requests.post(OPENROUTER_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        
        answer = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        cost_info = f"Tokens: {usage.get('total_tokens', 'N/A')}"
        
        # Cache the response
        cache_response(cache_key, {
            "answer": answer,
            "cost_info": cost_info,
            "model": model
        })
        
        # Log successful query
        latency_ms = int((time.time() - start_time) * 1000)
        tokens = usage.get('total_tokens') if usage else None
        # Estimate cost: $0.75 per 1M tokens for qwen/qwen3-coder
        cost_usd = (tokens * 0.75 / 1000000) if tokens else None
        
        query_logger.log_query(
            query=question,
            answer=answer,
            model_used=model,
            search_method=search_method,
            latency_ms=latency_ms,
            sources_count=sources_count,
            cache_hit=False,
            tokens_used=tokens,
            cost_usd=cost_usd
        )
        
        return answer, cost_info, model
        
    except Exception as e:
        # Log error
        latency_ms = int((time.time() - start_time) * 1000)
        query_logger.log_query(
            query=question,
            answer="",
            model_used=model,
            search_method=search_method,
            latency_ms=latency_ms,
            sources_count=sources_count,
            cache_hit=False,
            error=str(e)
        )
        return f"Error: {e}", "N/A", model


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/rag_pipeline.py \"your question here\" [--hybrid]")
        print("\nOptions:")
        print("  --hybrid    Enable hybrid search (BM25 + Vector)")
        print("\nExamples:")
        print('  python src/rag_pipeline.py "How do I create a user account?"')
        print('  python src/rag_pipeline.py "How to start a service with systemctl?" --hybrid')
        sys.exit(1)
    
    question = " ".join([arg for arg in sys.argv[1:] if not arg.startswith("--")])
    enable_hybrid = "--hybrid" in sys.argv
    
    print(f"\n🔍 Searching knowledge base...")
    if enable_hybrid:
        print("   (Hybrid search enabled: BM25 + Vector)")
    print("-" * 60)
    
    start_time = time.time()
    results, method = hybrid_search(question, top_k=5, enable_hybrid=enable_hybrid)
    search_time = time.time() - start_time
    
    if not results:
        print("❌ No relevant documents found in the knowledge base.")
        sys.exit(1)
    
    print(f"✓ Found {len(results)} relevant passages ({method})")
    print(f"✓ Search time: {search_time:.2f}s")
    print(f"✓ Using model: {MODEL_DEFAULT}")
    
    context, sources = format_context(results)
    
    print(f"\n🤖 Generating answer...")
    print("=" * 60)
    
    start_time = time.time()
    answer, cost_info, used_model = query_llm(question, context, MODEL_DEFAULT, method, len(sources))
    llm_time = time.time() - start_time
    
    print(f"\n📚 SOURCES:")
    print("-" * 60)
    for src in sources:
        print(f"  • {src}")
    
    print(f"\n💡 ANSWER:")
    print("-" * 60)
    print(answer)
    
    print(f"\n📊 METADATA:")
    print("-" * 60)
    print(f"  Model: {used_model}")
    print(f"  Search method: {method}")
    print(f"  Search time: {search_time:.2f}s")
    print(f"  LLM time: {llm_time:.2f}s")
    print(f"  {cost_info}")


if __name__ == "__main__":
    main()
