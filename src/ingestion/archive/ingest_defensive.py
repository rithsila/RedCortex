#!/usr/bin/env python3
"""
Defensive Ingestion - Phase 2
Skips bad chunks, longer delays between requests
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
DELAY = 0.5  # Seconds between requests


def get_embedding_defensive(text: str) -> tuple:
    """Get embedding with skip-on-fail logic"""
    try:
        truncated = text[:1500]  # Even smaller chunks
        response = ollama.embeddings(model=EMBED_MODEL, prompt=truncated)
        return response["embedding"], True
    except Exception as e:
        print(f"\n      ⚠️  Embedding failed: {str(e)[:60]}")
        return None, False


def main():
    if len(sys.argv) < 3:
        print("Usage: python ingest_defensive.py <pdf_path> <title> [category]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    title = sys.argv[2]
    category = sys.argv[3] if len(sys.argv) > 3 else "red_hat"
    
    db = sqlite3.connect("library.db")
    qdrant = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    
    print(f"\n📚 Processing: {title}")
    
    # Check if already exists
    cursor = db.execute("SELECT id, status FROM books WHERE file_path = ?", (pdf_path,))
    existing = cursor.fetchone()
    if existing:
        book_id, status = existing
        print(f"   Book exists (ID: {book_id}, status: {status})")
        if status == "indexed":
            print("   Already complete!")
            return
        # Resume from existing
    else:
        cursor = db.execute(
            "INSERT INTO books (title, category, file_path, status) VALUES (?, ?, ?, ?)",
            (title, category, pdf_path, "indexing")
        )
        book_id = cursor.lastrowid
        db.commit()
    
    try:
        # Extract text
        print("   Extracting text...")
        pages = []
        with fitz.open(pdf_path) as doc:
            for page in doc:
                text = page.get_text().strip()
                if text:
                    pages.append(text)
        
        total_pages = len(pages)
        db.execute("UPDATE books SET total_pages = ? WHERE id = ?", (total_pages, book_id))
        db.commit()
        print(f"   Pages: {total_pages}")
        
        # Check which chunks already exist
        cursor = db.execute(
            "SELECT COUNT(*) FROM chunks WHERE book_id = ? AND qdrant_id IS NOT NULL", 
            (book_id,)
        )
        already_done = cursor.fetchone()[0]
        
        # Simple: 1 page = 1 chunk for reliability
        chunks = []
        for i, page_text in enumerate(pages):
            chunks.append({
                "idx": i,
                "text": page_text,
                "page": i + 1
            })
        
        print(f"   Chunks: {len(chunks)} (already done: {already_done})")
        
        # Process chunks
        success_count = 0
        skip_count = 0
        
        for i, chunk in enumerate(chunks):
            if i < already_done:
                continue  # Skip already processed
                
            print(f"   [{i+1}/{len(chunks)}] Page {chunk['page']}...", end=" ", flush=True)
            
            # Delay to prevent Ollama overload
            time.sleep(DELAY)
            
            # Get embedding
            vec, success = get_embedding_defensive(chunk["text"])
            
            if not success:
                print("SKIPPED")
                skip_count += 1
                continue
            
            # Insert to SQLite
            cursor = db.execute(
                """INSERT INTO chunks (book_id, content, summary, page_start, page_end, is_hot)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (book_id, chunk["text"], chunk["text"][:100], 
                 chunk["page"], chunk["page"], 1)
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
                        "page": chunk["page"],
                        "summary": chunk["text"][:100]
                    }
                )]
            )
            
            db.execute("UPDATE chunks SET qdrant_id = ? WHERE id = ?", (point_id, parent_id))
            db.commit()
            
            success_count += 1
            print(f"✓")
        
        # Mark status
        if skip_count == 0:
            db.execute("UPDATE books SET status = ? WHERE id = ?", ("indexed", book_id))
        else:
            db.execute("UPDATE books SET status = ? WHERE id = ?", ("partial", book_id))
        db.commit()
        
        print(f"\n🎉 Done! Success: {success_count}, Skipped: {skip_count}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        db.execute("UPDATE books SET status = ? WHERE id = ?", ("failed", book_id))
        db.commit()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
