#!/usr/bin/env python3
"""
RAG Query with OpenRouter - Phase 3 Enhanced
Uses enhanced RAG pipeline with hybrid search and reranking
"""
import os
import sys
import sqlite3
import requests
import httpx
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# Import from our new RAG pipeline
from rag_pipeline import (
    hybrid_search,
    format_context,
    get_cache_key,
    get_cached_response,
    cache_response
)

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "books_hot"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL_DEFAULT = "qwen/qwen3-coder"
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


def get_context_legacy(query: str, top_k: int = 5):
    """Legacy: Retrieve relevant context from Qdrant + SQLite (fallback)"""
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
    
    db = sqlite3.connect("data/library.db")
    db.row_factory = sqlite3.Row
    
    contexts = []
    sources = []
    
    for hit in results:
        payload = hit.payload
        parent_id = payload.get("parent_id")
        
        cursor = db.execute(
            "SELECT content, page_start, page_end FROM chunks WHERE id = ?",
            (parent_id,)
        )
        row = cursor.fetchone()
        
        if row:
            contexts.append(f"[Page {row['page_start']}]: {row['content'][:800]}")
            sources.append(f"Page {row['page_start']} (score: {hit.score:.3f})")
    
    db.close()
    return "\n\n".join(contexts), sources


def get_context(query: str, top_k: int = 5, use_hybrid: bool = True):
    """Retrieve relevant context using enhanced pipeline"""
    try:
        results, method = hybrid_search(query, top_k=top_k, enable_hybrid=use_hybrid)
        context, sources = format_context(results)
        return context, sources, method
    except Exception as e:
        print(f"Warning: Enhanced search failed ({e}), falling back to legacy search")
        context, sources = get_context_legacy(query, top_k)
        return context, sources, "legacy"


def query_llm(question: str, context: str, model: str) -> tuple:
    """Send query to OpenRouter with caching"""
    
    # Check cache first (only for temperature=0 or low temp)
    cache_key = get_cache_key(question, model, 5)
    cached = get_cached_response(cache_key)
    if cached:
        return cached["answer"], cached["cost_info"] + " (cached)", model
    
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
        
        return answer, cost_info, model
        
    except Exception as e:
        return f"Error: {e}", "N/A", model


def main():
    if len(sys.argv) < 2:
        print("Usage: python src/query.py \"your question here\" [--no-hybrid]")
        print("\nOptions:")
        print("  --no-hybrid    Disable hybrid search (use vector only)")
        print("\nExamples:")
        print('  python src/query.py "How do I create a user account?"')
        print('  python src/query.py "How to start a service with systemctl?"')
        sys.exit(1)
    
    # Parse arguments
    args = sys.argv[1:]
    use_hybrid = "--no-hybrid" not in args
    question = " ".join([arg for arg in args if not arg.startswith("--")])
    
    print(f"\n🔍 Searching knowledge base...")
    if use_hybrid:
        print("   (Using hybrid search: BM25 + Vector + Reranking)")
    print("-" * 60)
    
    context, sources, method = get_context(question, top_k=5, use_hybrid=use_hybrid)
    
    if not context:
        print("❌ No relevant documents found in the knowledge base.")
        sys.exit(1)
    
    print(f"✓ Found {len(sources)} relevant passages ({method})")
    print(f"✓ Using model: {MODEL_DEFAULT}")
    
    print(f"\n🤖 Generating answer...")
    print("=" * 60)
    
    answer, cost_info, used_model = query_llm(question, context, MODEL_DEFAULT)
    
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
    print(f"  {cost_info}")


if __name__ == "__main__":
    main()
