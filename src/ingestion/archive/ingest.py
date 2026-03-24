#!/usr/bin/env python3
"""
Book Ingestion Pipeline - Phase 2
Tier 1 (Hot): 50 books → Qdrant with parent-child chunking
"""
import os
import sys
import uuid
import sqlite3
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

import ollama
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    from pypdf import PdfReader

load_dotenv()

# Config
CHUNK_SIZE = 512      # Parent chunk (tokens)
CHUNK_OVERLAP = 50    # Parent overlap
CHILD_SIZE = 128      # Child chunk for Qdrant (tokens)
CHILD_OVERLAP = 20    # Child overlap
EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "books_hot"


@dataclass
class Chunk:
    text: str
    page_start: int
    page_end: int
    token_count: int


class BookIngestor:
    def __init__(self, db_path: str = "library.db"):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
    def extract_text_pymupdf(self, pdf_path: str) -> List[str]:
        """Extract text by page using PyMuPDF (better for code)"""
        pages = []
        with fitz.open(pdf_path) as doc:
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                pages.append(text)
        return pages
    
    def extract_text_pypdf(self, pdf_path: str) -> List[str]:
        """Fallback: Extract text using PyPDF"""
        reader = PdfReader(pdf_path)
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        return pages
    
    def extract_text(self, pdf_path: str) -> List[str]:
        """Extract text from PDF"""
        if PYMUPDF_AVAILABLE:
            return self.extract_text_pymupdf(pdf_path)
        return self.extract_text_pypdf(pdf_path)
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimate (1 token ≈ 4 chars for English)"""
        return len(text) // 4
    
    def create_parents(self, pages: List[str], chunk_size: int = CHUNK_SIZE, 
                       overlap: int = CHUNK_OVERLAP) -> List[Chunk]:
        """Create parent chunks from pages"""
        # Join all pages
        full_text = "\n\n".join(pages)
        
        # Simple chunking by character count (approximate tokens)
        chars_per_chunk = chunk_size * 4
        chars_overlap = overlap * 4
        
        chunks = []
        start = 0
        current_page = 1
        chars_seen = 0
        
        while start < len(full_text):
            end = min(start + chars_per_chunk, len(full_text))
            chunk_text = full_text[start:end]
            
            # Track page numbers (rough estimate)
            text_before = full_text[:start]
            page_start = text_before.count('\f') + 1 if '\f' in full_text else current_page
            page_end = page_start + chunk_text.count('\f')
            
            chunks.append(Chunk(
                text=chunk_text,
                page_start=page_start,
                page_end=max(page_end, page_start),
                token_count=self.estimate_tokens(chunk_text)
            ))
            
            start = end - chars_overlap
            current_page = page_end
        
        return chunks
    
    def create_children(self, parent_text: str, chunk_size: int = CHILD_SIZE,
                        overlap: int = CHILD_OVERLAP) -> List[str]:
        """Split parent into smaller child chunks for Qdrant"""
        chars_per_chunk = chunk_size * 4
        chars_overlap = overlap * 4
        
        children = []
        start = 0
        
        while start < len(parent_text):
            end = min(start + chars_per_chunk, len(parent_text))
            children.append(parent_text[start:end])
            start = end - chars_overlap if end < len(parent_text) else end
        
        return children
    
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding from local Ollama"""
        response = ollama.embeddings(model=EMBED_MODEL, prompt=text)
        return response["embedding"]
    
    def add_book(self, pdf_path: str, title: str, category: str = "red_hat",
                 tier: str = "hot") -> int:
        """
        Ingest a book into the system
        
        Args:
            pdf_path: Path to PDF file
            title: Book title
            category: 'security', 'red_hat', 'ai_engineering', 'other'
            tier: 'hot' (Qdrant) or 'warm' (local FAISS)
        """
        print(f"\n📚 Processing: {title}")
        print(f"   File: {pdf_path}")
        print(f"   Category: {category}, Tier: {tier}")
        
        # 1. Add to books table
        cursor = self.db.execute(
            "INSERT INTO books (title, category, file_path, status) VALUES (?, ?, ?, ?)",
            (title, category, pdf_path, "indexing")
        )
        book_id = cursor.lastrowid
        self.db.commit()
        
        # 2. Extract text
        print("   Extracting text...")
        pages = self.extract_text(pdf_path)
        total_pages = len(pages)
        
        # Update total pages
        self.db.execute("UPDATE books SET total_pages = ? WHERE id = ?", (total_pages, book_id))
        self.db.commit()
        print(f"   Pages: {total_pages}")
        
        # 3. Create parent chunks
        print("   Creating parent chunks...")
        parents = self.create_parents(pages)
        print(f"   Parents: {len(parents)}")
        
        # 4. Process each parent
        for i, parent in enumerate(parents):
            print(f"   Processing parent {i+1}/{len(parents)}...", end="\r")
            
            # Insert parent into SQLite
            cursor = self.db.execute(
                """INSERT INTO chunks (book_id, content, summary, page_start, page_end, token_count, is_hot)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (book_id, parent.text, parent.text[:100], parent.page_start, 
                 parent.page_end, parent.token_count, 1 if tier == "hot" else 0)
            )
            parent_id = cursor.lastrowid
            self.db.commit()
            
            if tier == "hot":
                # Create children and upload to Qdrant
                children = self.create_children(parent.text)
                
                for child_text in children:
                    # Get embedding
                    vec = self.get_embedding(child_text)
                    
                    # Upload to Qdrant
                    point_id = str(uuid.uuid4())
                    self.qdrant.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[PointStruct(
                            id=point_id,
                            vector=vec,
                            payload={
                                "book_id": book_id,
                                "parent_id": parent_id,
                                "category": category,
                                "summary": child_text[:100]
                            }
                        )]
                    )
                    
                    # Update SQLite with qdrant_id
                    self.db.execute(
                        "UPDATE chunks SET qdrant_id = ? WHERE id = ?",
                        (point_id, parent_id)
                    )
                    self.db.commit()
        
        # Mark book as indexed
        self.db.execute("UPDATE books SET status = ? WHERE id = ?", ("indexed", book_id))
        self.db.commit()
        
        print(f"\n✅ Book indexed: {title} (ID: {book_id})")
        return book_id
    
    def close(self):
        self.db.close()


def main():
    if len(sys.argv) < 3:
        print("Usage: python ingest.py <pdf_path> <title> [category]")
        print("Example: python ingest.py 'book.pdf' 'RHEL 9 Admin Guide' red_hat")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    title = sys.argv[2]
    category = sys.argv[3] if len(sys.argv) > 3 else "red_hat"
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    ingestor = BookIngestor()
    try:
        book_id = ingestor.add_book(pdf_path, title, category, tier="hot")
        print(f"\n🎉 Successfully ingested book ID: {book_id}")
    finally:
        ingestor.close()


if __name__ == "__main__":
    main()
