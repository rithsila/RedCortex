#!/usr/bin/env python3
"""
Optimized Book Ingestion - Phase 2
Batch processing for faster ingestion
"""
import os
import sys
import uuid
import sqlite3
from pathlib import Path
from typing import List

import ollama
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
import fitz  # PyMuPDF

load_dotenv()

EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "books_hot"
BATCH_SIZE = 10  # Process 10 children at a time


class FastIngestor:
    def __init__(self, db_path: str = "library.db"):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.qdrant = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        
    def extract_text_by_page(self, pdf_path: str) -> List[str]:
        """Extract text page by page"""
        pages = []
        with fitz.open(pdf_path) as doc:
            print(f"   PDF pages: {len(doc)}")
            for page_num, page in enumerate(doc, 1):
                text = page.get_text()
                if text.strip():
                    pages.append(text)
                if page_num % 50 == 0:
                    print(f"   Extracted {page_num} pages...", end="\r")
        print(f"   Extracted {len(pages)} pages with text")
        return pages
    
    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text) // 4)
    
    def chunk_pages(self, pages: List[str], target_chars: int = 2000) -> List[dict]:
        """Simple page-based chunking"""
        chunks = []
        current_text = ""
        start_page = 1
        
        for i, page_text in enumerate(pages):
            current_text += f"\n\n--- Page {i+1} ---\n\n" + page_text
            
            if len(current_text) >= target_chars:
                chunks.append({
                    "text": current_text,
                    "page_start": start_page,
                    "page_end": i + 1
                })
                current_text = ""
                start_page = i + 2
        
        # Add remaining
        if current_text:
            chunks.append({
                "text": current_text,
                "page_start": start_page,
                "page_end": len(pages)
            })
        
        return chunks
    
    def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for multiple texts"""
        embeddings = []
        for text in texts:
            response = ollama.embeddings(model=EMBED_MODEL, prompt=text[:8000])  # Limit text length
            embeddings.append(response["embedding"])
        return embeddings
    
    def add_book(self, pdf_path: str, title: str, category: str = "red_hat") -> int:
        print(f"\n📚 Processing: {title}")
        
        # 1. Add book record
        cursor = self.db.execute(
            "INSERT INTO books (title, category, file_path, status) VALUES (?, ?, ?, ?)",
            (title, category, pdf_path, "indexing")
        )
        book_id = cursor.lastrowid
        self.db.commit()
        
        # 2. Extract text
        print("   Step 1: Extracting text...")
        pages = self.extract_text_by_page(pdf_path)
        
        self.db.execute("UPDATE books SET total_pages = ? WHERE id = ?", (len(pages), book_id))
        self.db.commit()
        
        # 3. Create chunks
        print("   Step 2: Chunking...")
        chunks = self.chunk_pages(pages)
        print(f"   Created {len(chunks)} chunks")
        
        # 4. Process chunks
        print("   Step 3: Generating embeddings & uploading...")
        total_points = 0
        
        for i, chunk in enumerate(chunks):
            print(f"   Chunk {i+1}/{len(chunks)}...", end="\r")
            
            # Insert parent
            cursor = self.db.execute(
                """INSERT INTO chunks (book_id, content, summary, page_start, page_end, token_count, is_hot)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (book_id, chunk["text"], chunk["text"][:100], 
                 chunk["page_start"], chunk["page_end"], 
                 self.estimate_tokens(chunk["text"]), 1)
            )
            parent_id = cursor.lastrowid
            self.db.commit()
            
            # Split into smaller pieces for embedding
            text = chunk["text"]
            sub_chunks = [text[j:j+4000] for j in range(0, len(text), 4000)]
            
            # Get embeddings
            vectors = self.get_embeddings_batch(sub_chunks)
            
            # Upload to Qdrant
            points = []
            for j, (vec, sub_text) in enumerate(zip(vectors, sub_chunks)):
                point_id = str(uuid.uuid4())
                points.append(PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={
                        "book_id": book_id,
                        "parent_id": parent_id,
                        "category": category,
                        "summary": sub_text[:100],
                        "chunk_idx": j
                    }
                ))
            
            self.qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
            total_points += len(points)
        
        # Mark complete
        self.db.execute("UPDATE books SET status = ? WHERE id = ?", ("indexed", book_id))
        self.db.commit()
        
        print(f"\n✅ Complete! Book ID: {book_id}, Qdrant points: {total_points}")
        return book_id
    
    def close(self):
        self.db.close()


def main():
    if len(sys.argv) < 3:
        print("Usage: python ingest_fast.py <pdf_path> <title> [category]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    title = sys.argv[2]
    category = sys.argv[3] if len(sys.argv) > 3 else "red_hat"
    
    if not os.path.exists(pdf_path):
        print(f"❌ File not found: {pdf_path}")
        sys.exit(1)
    
    ingestor = FastIngestor()
    try:
        book_id = ingestor.add_book(pdf_path, title, category)
    finally:
        ingestor.close()


if __name__ == "__main__":
    main()
