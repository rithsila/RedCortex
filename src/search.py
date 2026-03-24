#!/usr/bin/env python3
"""Search the indexed books with hybrid search support"""
import os
import sys
import sqlite3
import httpx
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Import from our new RAG pipeline
try:
    from rag_pipeline import (
        hybrid_search,
        format_context,
        vector_search,
        build_bm25_index,
        keyword_search
    )
    RAG_PIPELINE_AVAILABLE = True
except ImportError:
    RAG_PIPELINE_AVAILABLE = False

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "books_hot"
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")


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


def search_legacy(query: str, top_k: int = 5):
    """Legacy vector-only search"""
    print(f"\n🔍 Query: \"{query}\"")
    print("   (Vector search only)")
    print("=" * 60)
    
    # 1. Get embedding
    print("Getting embedding...")
    query_vec = get_embedding(query)
    
    # 2. Search Qdrant
    print("Searching Qdrant...")
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
    
    # 3. Fetch from SQLite
    db = sqlite3.connect("data/library.db")
    db.row_factory = sqlite3.Row
    
    print(f"\n📚 Top {len(results)} results:\n")
    
    for i, hit in enumerate(results, 1):
        score = hit.score
        payload = hit.payload
        parent_id = payload.get("parent_id")
        
        cursor = db.execute(
            "SELECT content, page_start, page_end FROM chunks WHERE id = ?",
            (parent_id,)
        )
        row = cursor.fetchone()
        
        if row:
            content = row["content"]
            page = row["page_start"]
            
            print(f"\n{i}. Score: {score:.4f} | Page: {page}")
            print("-" * 60)
            preview = content[:500].replace("\n", " ")
            print(f"{preview}...")
        else:
            print(f"\n{i}. Score: {score:.4f} | (Content not found)")
            print(f"   Summary: {payload.get('summary', 'N/A')}")
    
    db.close()


def search_hybrid(query: str, top_k: int = 5):
    """Search using hybrid approach with detailed output"""
    print(f"\n🔍 Query: \"{query}\"")
    print("   (Hybrid search: BM25 + Vector + Reranking)")
    print("=" * 60)
    
    if not RAG_PIPELINE_AVAILABLE:
        print("Warning: RAG pipeline not available, falling back to legacy search")
        search_legacy(query, top_k)
        return
    
    # Perform hybrid search
    print("Searching...")
    results, method = hybrid_search(query, top_k=top_k, enable_hybrid=True)
    
    if not results:
        print("\n❌ No results found.")
        return
    
    print(f"\n📚 Top {len(results)} results ({method}):\n")
    
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result.score:.4f} | Page: {result.page_start} | Source: {result.source}")
        print("-" * 60)
        preview = result.content[:500].replace("\n", " ")
        print(f"{preview}...")


def search_comparison(query: str, top_k: int = 5):
    """Compare vector vs hybrid search results"""
    print(f"\n🔍 Query: \"{query}\"")
    print("   (Comparing search methods)")
    print("=" * 60)
    
    if not RAG_PIPELINE_AVAILABLE:
        print("Warning: RAG pipeline not available")
        return
    
    db = sqlite3.connect("data/library.db")
    
    # Vector search only
    print("\n📊 VECTOR SEARCH RESULTS:")
    print("-" * 60)
    vector_results = vector_search(query, top_k=top_k, db=db)
    for i, result in enumerate(vector_results[:5], 1):
        preview = result.content[:200].replace("\n", " ")
        print(f"{i}. Score: {result.score:.4f} | Page: {result.page_start} | {preview}...")
    
    # BM25 search only
    print("\n📊 KEYWORD (BM25) SEARCH RESULTS:")
    print("-" * 60)
    bm25, chunks = build_bm25_index(db)
    if bm25:
        keyword_results = keyword_search(query, bm25, chunks, top_k=top_k)
        for i, result in enumerate(keyword_results[:5], 1):
            preview = result.content[:200].replace("\n", " ")
            print(f"{i}. Score: {result.score:.4f} | Page: {result.page_start} | {preview}...")
    else:
        print("(No BM25 index available)")
    
    # Hybrid search
    print("\n📊 HYBRID SEARCH RESULTS (RRF + Reranking):")
    print("-" * 60)
    from rag_pipeline import reciprocal_rank_fusion, rerank_results
    
    if bm25:
        fused = reciprocal_rank_fusion(vector_results, keyword_results)
        reranked = rerank_results(query, fused, top_k)
        for i, result in enumerate(reranked, 1):
            preview = result.content[:200].replace("\n", " ")
            print(f"{i}. Score: {result.score:.4f} | Page: {result.page_start} | Source: {result.source} | {preview}...")
    
    db.close()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Check for flags
        if "--compare" in sys.argv:
            query = " ".join([arg for arg in sys.argv[1:] if not arg.startswith("--")])
            search_comparison(query)
        elif "--legacy" in sys.argv:
            query = " ".join([arg for arg in sys.argv[1:] if not arg.startswith("--")])
            search_legacy(query)
        else:
            query = " ".join([arg for arg in sys.argv[1:] if not arg.startswith("--")])
            search_hybrid(query)
    else:
        query = "How to configure firewalld rich rules?"
        search_hybrid(query)
