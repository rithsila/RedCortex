#!/usr/bin/env python3
"""
Hierarchical Retrieval for RedCortex
Implements multi-level search: book → section → chunk
"""
import os
import sys
import sqlite3
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, 'src')

from rag_pipeline import hybrid_search, SearchResult, get_embedding
from qdrant_client import QdrantClient
from dotenv import load_dotenv

load_dotenv()


@dataclass
class BookResult:
    """Book-level search result"""
    book_id: int
    title: str
    category: str
    relevance_score: float
    matched_chunks: int


@dataclass
class SectionResult:
    """Section-level search result"""
    section_id: str  # Could be chapter or page range
    book_id: int
    title: str
    page_start: int
    page_end: int
    relevance_score: float
    chunks: List[SearchResult]


@dataclass
class HierarchicalResults:
    """Complete hierarchical search results"""
    books: List[BookResult]
    sections: List[SectionResult]
    chunks: List[SearchResult]
    search_method: str


class HierarchicalRetriever:
    """
    Hierarchical retriever that searches at multiple levels:
    1. Book level: Find relevant books
    2. Section level: Find relevant sections within books
    3. Chunk level: Find specific chunks within sections
    """
    
    def __init__(self, db_path: str = "data/library.db"):
        self.db_path = db_path
        self.qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        self.collection_name = "books_hot"
    
    def search(
        self,
        query: str,
        top_k_books: int = 3,
        top_k_sections: int = 5,
        top_k_chunks: int = 5,
        enable_hybrid: bool = True
    ) -> HierarchicalResults:
        """
        Perform hierarchical search.
        
        Args:
            query: Search query
            top_k_books: Number of books to retrieve
            top_k_sections: Number of sections to retrieve
            top_k_chunks: Final number of chunks to return
            enable_hybrid: Use hybrid search for chunk retrieval
            
        Returns:
            HierarchicalResults with books, sections, and chunks
        """
        # Step 1: Get all chunk candidates
        candidates, method = hybrid_search(query, top_k=50, enable_hybrid=enable_hybrid)
        
        if not candidates:
            return HierarchicalResults(
                books=[],
                sections=[],
                chunks=[],
                search_method="hierarchical"
            )
        
        # Step 2: Aggregate by book
        book_scores = defaultdict(lambda: {"score": 0.0, "chunks": 0, "title": ""})
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for chunk in candidates:
            # Get book info
            cursor.execute(
                "SELECT title, category FROM books WHERE id = ?",
                (chunk.book_id,)
            )
            book_info = cursor.fetchone()
            
            if book_info:
                book_scores[chunk.book_id]["score"] += chunk.score
                book_scores[chunk.book_id]["chunks"] += 1
                book_scores[chunk.book_id]["title"] = book_info[0]
                book_scores[chunk.book_id]["category"] = book_info[1]
        
        # Step 3: Create book results
        books = []
        for book_id, data in sorted(
            book_scores.items(),
            key=lambda x: x[1]["score"],
            reverse=True
        )[:top_k_books]:
            books.append(BookResult(
                book_id=book_id,
                title=data["title"],
                category=data.get("category", "unknown"),
                relevance_score=data["score"],
                matched_chunks=data["chunks"]
            ))
        
        # Step 4: Group chunks by section (page ranges)
        section_groups = defaultdict(list)
        
        for chunk in candidates:
            # Create section key based on page range
            # Group pages in ranges of 50
            section_start = (chunk.page_start // 50) * 50 + 1
            section_end = section_start + 49
            section_key = f"{chunk.book_id}_{section_start}_{section_end}"
            
            section_groups[section_key].append(chunk)
        
        # Step 5: Create section results
        sections = []
        for section_key, chunks in sorted(
            section_groups.items(),
            key=lambda x: sum(c.score for c in x[1]),
            reverse=True
        )[:top_k_sections]:
            parts = section_key.split("_")
            book_id = int(parts[0])
            page_start = int(parts[1])
            page_end = int(parts[2])
            
            # Get book title
            cursor.execute(
                "SELECT title FROM books WHERE id = ?",
                (book_id,)
            )
            book_title = cursor.fetchone()
            book_title = book_title[0] if book_title else "Unknown"
            
            total_score = sum(c.score for c in chunks)
            
            sections.append(SectionResult(
                section_id=section_key,
                book_id=book_id,
                title=f"{book_title} (Pages {page_start}-{page_end})",
                page_start=page_start,
                page_end=page_end,
                relevance_score=total_score,
                chunks=chunks[:5]  # Top 5 chunks in section
            ))
        
        conn.close()
        
        # Step 6: Return top chunks with hierarchy info
        final_chunks = candidates[:top_k_chunks]
        
        return HierarchicalResults(
            books=books,
            sections=sections,
            chunks=final_chunks,
            search_method=f"hierarchical+{method}"
        )
    
    def search_with_context(
        self,
        query: str,
        book_id: Optional[int] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Search with optional book filter and get surrounding context.
        
        Args:
            query: Search query
            book_id: Optional book ID to filter by
            top_k: Number of results
            
        Returns:
            List of search results with context
        """
        # Get initial results
        results, method = hybrid_search(query, top_k=top_k * 2, enable_hybrid=True)
        
        if not results:
            return []
        
        # Filter by book if specified
        if book_id:
            results = [r for r in results if r.book_id == book_id]
        
        # Get surrounding chunks for context
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        enriched_results = []
        
        for result in results[:top_k]:
            # Get adjacent chunks (previous and next)
            cursor.execute('''
                SELECT id, content, page_start, page_end
                FROM chunks
                WHERE book_id = ?
                AND page_end < ?
                ORDER BY page_end DESC
                LIMIT 1
            ''', (result.book_id, result.page_start))
            
            prev_chunk = cursor.fetchone()
            
            cursor.execute('''
                SELECT id, content, page_start, page_end
                FROM chunks
                WHERE book_id = ?
                AND page_start > ?
                ORDER BY page_start
                LIMIT 1
            ''', (result.book_id, result.page_end))
            
            next_chunk = cursor.fetchone()
            
            # Build context-enhanced content
            context_parts = []
            
            if prev_chunk:
                context_parts.append(f"[Context from Page {prev_chunk[2]}]: {prev_chunk[1][:300]}...")
            
            context_parts.append(f"[Main Content - Page {result.page_start}]: {result.content}")
            
            if next_chunk:
                context_parts.append(f"[Context from Page {next_chunk[2]}]: {next_chunk[1][:300]}...")
            
            result.content = "\n\n".join(context_parts)
            enriched_results.append(result)
        
        conn.close()
        
        return enriched_results


def format_hierarchical_results(results: HierarchicalResults) -> str:
    """Format hierarchical results for display"""
    output = []
    
    output.append("🔍 Hierarchical Search Results")
    output.append("=" * 60)
    output.append(f"Method: {results.search_method}")
    output.append("")
    
    # Books
    output.append(f"📚 Top Books ({len(results.books)}):")
    for i, book in enumerate(results.books, 1):
        output.append(f"  {i}. {book.title}")
        output.append(f"     Score: {book.relevance_score:.3f}, Matched chunks: {book.matched_chunks}")
    
    output.append("")
    
    # Sections
    output.append(f"📖 Top Sections ({len(results.sections)}):")
    for i, section in enumerate(results.sections, 1):
        output.append(f"  {i}. {section.title}")
        output.append(f"     Score: {section.relevance_score:.3f}, Chunks: {len(section.chunks)}")
    
    output.append("")
    
    # Chunks
    output.append(f"🧩 Top Chunks ({len(results.chunks)}):")
    for i, chunk in enumerate(results.chunks, 1):
        output.append(f"  {i}. Page {chunk.page_start} (Score: {chunk.score:.3f})")
        output.append(f"     {chunk.content[:200]}...")
    
    return "\n".join(output)


def main():
    """CLI for hierarchical retrieval"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python src/hierarchical_retrieval.py <query> [--context]")
        print("\nOptions:")
        print("  --context  Include surrounding chunks for context")
        print("\nExamples:")
        print('  python src/hierarchical_retrieval.py "How to configure SSH?"')
        sys.exit(1)
    
    query = sys.argv[1]
    use_context = "--context" in sys.argv
    
    retriever = HierarchicalRetriever()
    
    if use_context:
        results = retriever.search_with_context(query, top_k=5)
        print("\n🔍 Search with Context")
        print("=" * 60)
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Page {result.page_start}")
            print("-" * 40)
            print(result.content)
    else:
        results = retriever.search(query)
        print(format_hierarchical_results(results))


if __name__ == "__main__":
    main()
