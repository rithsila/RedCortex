#!/usr/bin/env python3
"""
Multi-Query Retrieval for RedCortex
Generates query variations for better recall
"""
import os
import sys
from typing import List, Set, Tuple
from dataclasses import dataclass

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, 'src')

from rag_pipeline import hybrid_search, SearchResult


@dataclass
class QueryVariation:
    """A query variation with its source"""
    query: str
    source: str  # 'original', 'synonym', 'rephrased', 'expanded'
    weight: float


class MultiQueryRetriever:
    """
    Multi-query retriever that generates variations of the original query
    to improve recall for ambiguous queries.
    """
    
    def __init__(self):
        self.variation_templates = {
            'synonym': [
                "{query}",
            ],
            'rephrased': [
                "How to {action}",
                "What is the method for {action}",
                "Explain how {action} works",
            ],
            'expanded': [
                "{query} in RHEL",
                "{query} step by step",
                "Best practices for {query}",
            ]
        }
    
    def generate_variations(self, query: str, num_variations: int = 3) -> List[QueryVariation]:
        """
        Generate semantic variations of the query.
        
        For now, uses rule-based approach. In production, could use LLM to generate variations.
        """
        variations = [QueryVariation(query=query, source='original', weight=1.0)]
        
        # Simple rule-based variations
        query_lower = query.lower()
        
        # Extract action verb if present
        action_words = ['create', 'configure', 'set up', 'manage', 'install', 'start', 'stop', 'check']
        found_action = None
        for action in action_words:
            if action in query_lower:
                found_action = action
                break
        
        # Generate synonym variations
        synonyms = self._get_synonyms(query)
        for syn in synonyms[:1]:  # Limit to 1 synonym
            if syn.lower() != query_lower:
                variations.append(QueryVariation(
                    query=syn,
                    source='synonym',
                    weight=0.9
                ))
        
        # Generate expanded variations
        if 'rhel' not in query_lower and 'red hat' not in query_lower:
            variations.append(QueryVariation(
                query=f"{query} in RHEL 9",
                source='expanded',
                weight=0.8
            ))
        
        # Generate rephrased variation
        if found_action and 'how' in query_lower:
            # Extract the action target
            words = query.split()
            if len(words) > 3:
                rephrased = f"Steps to {found_action} {' '.join(words[words.index(found_action)+1:])}"
                variations.append(QueryVariation(
                    query=rephrased,
                    source='rephrased',
                    weight=0.85
                ))
        
        return variations[:num_variations]
    
    def _get_synonyms(self, query: str) -> List[str]:
        """Get simple synonyms for common RHEL terms"""
        synonyms = []
        query_lower = query.lower()
        
        # Common RHEL term synonyms
        replacements = {
            'create': ['add', 'make', 'set up'],
            'user': ['account', 'username'],
            'configure': ['set up', 'setup', 'enable'],
            'start': ['run', 'launch', 'initiate'],
            'stop': ['halt', 'terminate', 'end'],
            'check': ['view', 'see', 'display', 'show'],
            'firewall': ['firewalld', 'iptables'],
            'service': ['daemon', 'unit', 'systemd service'],
        }
        
        for term, alts in replacements.items():
            if term in query_lower:
                for alt in alts[:1]:  # Just first alternative
                    synonym = query_lower.replace(term, alt)
                    if synonym != query_lower:
                        synonyms.append(synonym)
        
        return synonyms
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        num_variations: int = 3,
        enable_hybrid: bool = True
    ) -> Tuple[List[SearchResult], str]:
        """
        Search with query variations.
        
        Args:
            query: Original query
            top_k: Number of final results
            num_variations: Number of query variations to generate
            enable_hybrid: Use hybrid search
            
        Returns:
            Tuple of (results, method)
        """
        print(f"\n🔍 Multi-Query Retrieval")
        print(f"Original: {query}")
        
        # Generate variations
        variations = self.generate_variations(query, num_variations)
        
        print(f"Generated {len(variations)} query variations:")
        for v in variations:
            print(f"  [{v.source}] {v.query} (weight: {v.weight})")
        
        # Search with each variation
        all_results = []
        seen_chunk_ids = set()
        
        for variation in variations:
            results, method = hybrid_search(
                variation.query,
                top_k=10,
                enable_hybrid=enable_hybrid
            )
            
            # Apply weight to scores and deduplicate
            for result in results:
                if result.chunk_id not in seen_chunk_ids:
                    # Adjust score by variation weight
                    result.score = result.score * variation.weight
                    result.source = f"{result.source}+{variation.source}"
                    all_results.append(result)
                    seen_chunk_ids.add(result.chunk_id)
        
        # Sort by adjusted score and return top_k
        all_results.sort(key=lambda x: x.score, reverse=True)
        final_results = all_results[:top_k]
        
        print(f"Retrieved {len(final_results)} unique results from {len(variations)} queries")
        
        return final_results, "multi-query+hybrid+rerank"
    
    def search_with_reranking(
        self,
        query: str,
        top_k: int = 5,
        num_variations: int = 3
    ) -> Tuple[List[SearchResult], str]:
        """
        Search with variations and rerank using original query.
        """
        from rag_pipeline import rerank_results
        
        # Get candidates from multi-query
        candidates, _ = self.search(
            query,
            top_k=20,
            num_variations=num_variations,
            enable_hybrid=True
        )
        
        if not candidates:
            return [], "multi-query"
        
        # Rerank using original query
        reranked = rerank_results(query, candidates, top_k=top_k)
        
        return reranked, "multi-query+rerank"


def compare_search_methods(query: str):
    """Compare single query vs multi-query retrieval"""
    print("=" * 70)
    print(f"Query: {query}")
    print("=" * 70)
    
    # Single query
    print("\n📊 Single Query Search:")
    single_results, single_method = hybrid_search(query, top_k=5, enable_hybrid=True)
    
    print(f"Method: {single_method}")
    print(f"Results: {len(single_results)}")
    for i, r in enumerate(single_results[:3], 1):
        print(f"  {i}. Page {r.page_start} (Score: {r.score:.3f})")
    
    # Multi-query
    print("\n📊 Multi-Query Search:")
    retriever = MultiQueryRetriever()
    multi_results, multi_method = retriever.search(query, top_k=5)
    
    print(f"Method: {multi_method}")
    print(f"Results: {len(multi_results)}")
    for i, r in enumerate(multi_results[:3], 1):
        print(f"  {i}. Page {r.page_start} (Score: {r.score:.3f})")
    
    # Compare overlap
    single_pages = {r.page_start for r in single_results}
    multi_pages = {r.page_start for r in multi_results}
    overlap = single_pages & multi_pages
    
    print(f"\n📈 Comparison:")
    print(f"  Single query pages: {sorted(single_pages)[:5]}")
    print(f"  Multi-query pages:  {sorted(multi_pages)[:5]}")
    print(f"  Overlap: {len(overlap)} pages ({overlap})")


def main():
    """CLI for multi-query retrieval"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python src/multi_query_retrieval.py <query> [--compare]")
        print("\nExamples:")
        print('  python src/multi_query_retrieval.py "How to create user?"')
        print('  python src/multi_query_retrieval.py "firewall config" --compare')
        sys.exit(1)
    
    query = sys.argv[1]
    compare_mode = "--compare" in sys.argv
    
    if compare_mode:
        compare_search_methods(query)
    else:
        retriever = MultiQueryRetriever()
        results, method = retriever.search(query, top_k=5)
        
        print(f"\n📚 Top {len(results)} Results ({method}):")
        print("-" * 60)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Page {result.page_start} (Score: {result.score:.3f}, Source: {result.source})")
            print(f"   {result.content[:200]}...")


if __name__ == "__main__":
    main()
