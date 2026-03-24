#!/usr/bin/env python3
"""Ingest only first N pages for testing"""
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

MAX_PAGES = int(os.getenv("MAX_PAGES", 50))  # Default 50 pages

def main():
    pdf_path = sys.argv[1]
    title = sys.argv[2]
    category = sys.argv[3] if len(sys.argv) > 3 else "red_hat"
    
    db = sqlite3.connect("library.db")
    qdrant = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
    
    print(f"📚 Processing: {title}")
    print(f"   Limit: First {MAX_PAGES} pages only")
    
    # Add book
    cursor = db.execute(
        "INSERT INTO books (title, category, file_path, status) VALUES (?, ?, ?, ?)",
        (title, category, pdf_path, "indexing")
    )
    book_id = cursor.lastrowid
    db.commit()
    
    # Extract only first N pages
    pages = []
    with fitz.open(pdf_path) as doc:
        for i in range(min(MAX_PAGES, len(doc))):
            text = doc[i].get_text().strip()
            if text:
                pages.append(text)
    
    print(f"   Pages to process: {len(pages)}")
    
    # Process each page
    for i, page_text in enumerate(pages):
        print(f"   [{i+1}/{len(pages)}] Embedding page {i+1}...", end=" ", flush=True)
        
        try:
            response = ollama.embeddings(model="nomic-embed-text", prompt=page_text[:1500])
            vec = response["embedding"]
            
            # SQLite
            cursor = db.execute(
                "INSERT INTO chunks (book_id, content, summary, page_start, page_end, is_hot) VALUES (?, ?, ?, ?, ?, ?)",
                (book_id, page_text, page_text[:100], i+1, i+1, 1)
            )
            parent_id = cursor.lastrowid
            db.commit()
            
            # Qdrant
            point_id = str(uuid.uuid4())
            qdrant.upsert(
                collection_name="books_hot",
                points=[PointStruct(
                    id=point_id,
                    vector=vec,
                    payload={"book_id": book_id, "parent_id": parent_id, "category": category, "page": i+1}
                )]
            )
            
            db.execute("UPDATE chunks SET qdrant_id = ? WHERE id = ?", (point_id, parent_id))
            db.commit()
            
            print("✓")
            time.sleep(0.3)
            
        except Exception as e:
            print(f"✗ ({str(e)[:40]})")
    
    db.execute("UPDATE books SET status = ?, total_pages = ? WHERE id = ?", 
               ("indexed", len(pages), book_id))
    db.commit()
    
    print(f"\n🎉 Done! Book ID: {book_id}")
    db.close()

if __name__ == "__main__":
    main()
