#!/usr/bin/env python3
"""
Semantic chunking ingestion with resume capability
Uses RecursiveCharacterTextSplitter for better context preservation
"""
import os
import sys
import uuid
import sqlite3
import time
import fitz
import httpx
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv()

EMBED_MODEL = "nomic-embed-text"
COLLECTION_NAME = "books_hot"
DELAY = 0.3
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Semantic chunking configuration
CHUNK_CONFIG = {
    "chunk_size": 1000,       # characters (roughly 250-300 tokens)
    "chunk_overlap": 200,     # overlap for context continuity
    "separators": ["\n\n", "\n", ". ", " ", ""]  # Try paragraphs first
}


def get_embedding(text: str) -> list[float]:
    """Get embedding from Ollama using direct HTTP API"""
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={
                    "model": EMBED_MODEL,
                    "prompt": text[:1500]  # Truncate to safe limit
                }
            )
            response.raise_for_status()
            data = response.json()
            return data["embedding"]
    except httpx.HTTPStatusError as e:
        raise Exception(f"Ollama HTTP error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Embedding error: {e}")


def extract_text_with_structure(pdf_path: str) -> list[dict]:
    """
    Extract text from PDF with page structure preserved.
    Returns list of dicts with page_num and text.
    """
    pages = []
    with fitz.open(pdf_path) as doc:
        for i, page in enumerate(doc):
            text = page.get_text().strip()
            if text:
                pages.append({
                    "page_num": i + 1,
                    "text": text
                })
    return pages


def create_semantic_chunks(pages: list[dict], book_id: int) -> list[dict]:
    """
    Create semantic chunks from pages using RecursiveCharacterTextSplitter.
    Preserves page boundaries while allowing multi-page chunks.
    """
    # Combine all text with page markers for context
    full_text = ""
    page_boundaries = {}  # Map character positions to page numbers
    current_pos = 0
    
    for page in pages:
        page_start = current_pos
        full_text += page["text"] + "\n\n"
        current_pos = len(full_text)
        # Mark the range of characters belonging to this page
        for pos in range(page_start, current_pos):
            page_boundaries[pos] = page["page_num"]
    
    # Use RecursiveCharacterTextSplitter for semantic chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_CONFIG["chunk_size"],
        chunk_overlap=CHUNK_CONFIG["chunk_overlap"],
        separators=CHUNK_CONFIG["separators"],
        length_function=len,
        is_separator_regex=False
    )
    
    chunks = splitter.create_documents([full_text])
    
    # Map chunks back to page numbers and create chunk records
    chunk_records = []
    for chunk in chunks:
        chunk_text = chunk.page_content.strip()
        if not chunk_text:
            continue
            
        # Find which pages this chunk spans
        start_char = full_text.find(chunk_text)
        if start_char == -1:
            # Fallback: search with relaxed matching
            start_char = full_text.find(chunk_text[:100])
        
        if start_char != -1:
            end_char = start_char + len(chunk_text)
            start_page = page_boundaries.get(start_char, 1)
            end_page = page_boundaries.get(end_char - 1, start_page)
        else:
            start_page = end_page = 1
        
        chunk_records.append({
            "content": chunk_text,
            "page_start": start_page,
            "page_end": end_page,
            "book_id": book_id
        })
    
    return chunk_records


def main():
    if len(sys.argv) < 3:
        print("Usage: python src/ingestion/ingest.py <pdf_path> <title> [category]")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    title = sys.argv[2]
    category = sys.argv[3] if len(sys.argv) > 3 else "red_hat"
    
    # Verify Ollama is accessible
    try:
        with httpx.Client(timeout=5.0) as client:
            response = client.get(f"{OLLAMA_HOST}/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            if EMBED_MODEL not in str(model_names):
                print(f"⚠️  Warning: {EMBED_MODEL} not found in Ollama models")
                print(f"   Available models: {model_names}")
                print(f"   Run: ollama pull {EMBED_MODEL}")
            else:
                print(f"✓ Ollama ready with {EMBED_MODEL}")
    except Exception as e:
        print(f"❌ Error: Cannot connect to Ollama at {OLLAMA_HOST}")
        print(f"   Error: {e}")
        sys.exit(1)
    
    db = sqlite3.connect("data/library.db")
    qdrant = QdrantClient(
        url=os.getenv("QDRANT_URL"), 
        api_key=os.getenv("QDRANT_API_KEY")
    )
    
    # Check if book exists
    cursor = db.execute("SELECT id FROM books WHERE file_path = ?", (pdf_path,))
    result = cursor.fetchone()
    
    if result:
        book_id = result[0]
        cursor = db.execute("SELECT MAX(page_end) FROM chunks WHERE book_id = ?", (book_id,))
        last_page = cursor.fetchone()[0] or 0
        print(f"📚 Resuming: {title}")
        print(f"   Already indexed: {last_page} pages")
        start_page = last_page
    else:
        cursor = db.execute(
            "INSERT INTO books (title, category, file_path, status) VALUES (?, ?, ?, ?)",
            (title, category, pdf_path, "indexing")
        )
        book_id = cursor.lastrowid
        db.commit()
        print(f"📚 New book: {title}")
        start_page = 0
    
    # Extract all pages with structure
    print("   Extracting text...")
    pages = extract_text_with_structure(pdf_path)
    
    total_pages = len(pages)
    db.execute("UPDATE books SET total_pages = ? WHERE id = ?", (total_pages, book_id))
    db.commit()
    
    print(f"   Total pages with text: {total_pages}")
    
    # Filter pages for resumption
    pages_to_process = [p for p in pages if p["page_num"] > start_page]
    
    if not pages_to_process:
        print("   All pages already indexed!")
        db.close()
        return
    
    print(f"   Pages to process: {len(pages_to_process)}")
    print(f"   Creating semantic chunks...")
    
    # Create semantic chunks
    chunks = create_semantic_chunks(pages_to_process, book_id)
    print(f"   Created {len(chunks)} chunks from {len(pages_to_process)} pages")
    
    processed = 0
    skipped = 0
    consecutive_errors = 0
    
    for i, chunk in enumerate(chunks):
        print(f"   [{i+1}/{len(chunks)}] Chunk (pages {chunk['page_start']}-{chunk['page_end']})...", end=" ", flush=True)
        
        try:
            vec = get_embedding(chunk["content"])
            
            cursor = db.execute(
                """INSERT INTO chunks (book_id, content, summary, page_start, page_end, is_hot)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (book_id, chunk["content"], chunk["content"][:200], 
                 chunk["page_start"], chunk["page_end"], 1)
            )
            parent_id = cursor.lastrowid
            db.commit()
            
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
                        "page": chunk["page_start"]
                    }
                )]
            )
            
            db.execute("UPDATE chunks SET qdrant_id = ? WHERE id = ?", (point_id, parent_id))
            db.commit()
            
            print("✓")
            processed += 1
            consecutive_errors = 0
            time.sleep(DELAY)
            
        except Exception as e:
            print(f"✗ (skipped: {e})")
            skipped += 1
            consecutive_errors += 1
            
            # Stop if too many consecutive errors
            if consecutive_errors >= 5:
                print(f"\n❌ Too many consecutive errors ({consecutive_errors}). Stopping.")
                print("   Please check Ollama status and try again.")
                break
            
            continue
    
    cursor = db.execute("SELECT COUNT(*) FROM chunks WHERE book_id = ?", (book_id,))
    total_indexed = cursor.fetchone()[0]
    
    status = "indexed" if skipped == 0 else "partial"
    db.execute("UPDATE books SET status = ? WHERE id = ?", (status, book_id))
    db.commit()
    
    print(f"\n🎉 Done!")
    print(f"   Chunks created: {processed}")
    print(f"   Skipped: {skipped}")
    print(f"   Total chunks for book: {total_indexed}")
    db.close()


if __name__ == "__main__":
    main()
