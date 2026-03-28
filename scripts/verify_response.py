#!/usr/bin/env python3
"""
Verify RAG response accuracy by showing source content.
Usage: python scripts/verify_response.py "Your question here"
"""
import sys
import os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, 'src')

from rag_pipeline import hybrid_search

def verify_query(query: str):
    """Verify a query by showing sources and their content."""
    print(f"🔍 VERIFYING: {query}")
    print("=" * 70)
    
    results, method = hybrid_search(query, top_k=5)
    
    print(f"\n📊 SEARCH METRICS:")
    print(f"   Method: {method}")
    print(f"   Sources found: {len(results)}")
    print(f"   Avg score: {sum(r.score for r in results) / len(results):.2f}")
    
    print(f"\n📚 SOURCE VERIFICATION:")
    print("-" * 70)
    
    for i, r in enumerate(results, 1):
        # Accuracy indicator
        if r.score >= 8.0:
            accuracy = "🟢 HIGH"
        elif r.score >= 6.0:
            accuracy = "🟡 MEDIUM"
        else:
            accuracy = "🔴 LOW"
            
        print(f"\n[{i}] Page {r.page_start}-{r.page_end} | Score: {r.score:.2f} | {accuracy}")
        print(f"    Book ID: {r.book_id} | Chunk: {r.chunk_id}")
        print(f"    Source type: {r.source}")
        print("-" * 50)
        
        # Show content (first 400 chars)
        content = r.content[:400].replace('\n', ' ')
        print(f"    Content: {content}...")
    
    print("\n" + "=" * 70)
    print("✅ VERIFICATION COMPLETE")
    print("\nHow to interpret:")
    print("  🟢 HIGH (score ≥ 8.0) - Highly relevant, likely accurate")
    print("  🟡 MEDIUM (score 6.0-8.0) - Relevant, verify key facts")
    print("  🔴 LOW (score < 6.0) - Check against original source")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_response.py 'Your question here'")
        sys.exit(1)
    
    query = sys.argv[1]
    verify_query(query)
