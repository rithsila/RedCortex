#!/usr/bin/env python3
"""
Simple & Robust Ingestion - Phase 2
One embedding at a time with retry logic
"""
import os
import sys
import uuid
import sqlite3
import time
import fitz
import ollama
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

load_dotenv()

EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "books_hot"
MAX_RETRIES = 3


def get_embedding_safe(text: str, retries=MAX_RETRIES) -> list:
    """Get embedding with retry logic"""
    for attempt in range(retries):
        try:
            # Limit to 2000 chars (~500 tokens) for speed
            truncated = text[:2000]
            response = ollama.embeddings(model=EMBED_MODEL, prompt=truncated)
            return response["embedding"]
        except Exception as e:
            print(f"      ⚠️  Retry {attempt+1}/{retries}: {e}")
            time.sleep(1)
    raise Exception("Failed to get embedding after retries")


def main():
    if len(sys.argv) < 3:
        print("Usage: python ingest_simple.py <pdf_path> <title> [category]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    title = sys.argv[2]
    category = sys.argv[3] if len(sys.argv) > 3 else "red_hat"
    
    # Init connections
    db = sqlite3.connect("library.db")
    qdrant = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    
    print(f"\n📚 Processing: {title}")
    
    # 1. Add book record
    cursor = db.execute(
        "INSERT INTO books (title, category, file_path, status) VALUES (?, ?, ?, ?)",
        (title, category, pdf_path, "indexing")
    )
    book_id = cursor.lastrowid
    db.commit()
    
    try:
        # 2. Extract text
        print("   Extracting text...")
        pages = []
        with fitz.open(pdf_path) as doc:
            for i, page in enumerate(doc):
                text = page.get_text().strip()
                if text:
                    pages.append(text)
        
        total_pages = len(pages)
        db.execute("UPDATE books SET total_pages = ? WHERE id = ?", (total_pages, book_id))
        db.commit()
        print(f"   Pages with text: {total_pages}")
        
        # 3. Simple chunking: every 3 pages = 1 chunk
        chunk_size = 3
        chunks = []
        for i in range(0, len(pages), chunk_size):
            chunk_pages = pages[i:i+chunk_size]
            chunk_text = "\n\n".join(chunk_pages)
            chunks.append({
                "text": chunk_text,
                "page_start": i + 1,
                "page_end": min(i + chunk_size, len(pages))
            })
        
        print(f"   Chunks to process: {len(chunks)}")
        
        # 4. Process each chunk
        total_points = 0
        for i, chunk in enumerate(chunks):
            print(f"   [{i+1}/{len(chunks)}] Embedding...", end=" ")
            
            # Get embedding
            vec = get_embedding_safe(chunk["text"])
            
            # Insert to SQLite
            cursor = db.execute(
                """INSERT INTO chunks (book_id, content, summary, page_start, page_end, is_hot)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (book_id, chunk["text"], chunk["text"][:100], 
                 chunk["page_start"], chunk["page_end"], 1)
            )
            parent_id = cursor.lastrowid
            db.commit()
            
            # Upload to Qdrant
            point_id = str(uuid.uuid4())
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=[PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={
                        "book_id": book_id,
                        "parent_id": parent_id,
                        "category": category,
                        "summary": chunk["text"][:100]
                    }
                )]
            )
            
            # Update SQLite with qdrant_id
            db.execute("UPDATE chunks SET qdrant_id = ? WHERE id = ?", (point_id, parent_id))
            db.commit()
            
            total_points += 1
            print(f"✓ (point: {point_id[:8]}...)")
        
        # Mark complete
        db.execute("UPDATE books SET status = ? WHERE id = ?", ("indexed", book_id))
        db.commit()
        
        print(f"\n🎉 SUCCESS! Book ID: {book_id}, Points: {total_points}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        db.execute("UPDATE books SET status = ? WHERE id = ?", ("failed", book_id))
        db.commit()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
