"""Quick test - ingest only first 5 pages"""
import os
import uuid
import sqlite3
import fitz
import ollama
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct

load_dotenv()

pdf_path = "Redhat E-Books/Enterprise Linux Automation with Ansible9.0.pdf"

# Extract first 5 pages
print("Extracting first 5 pages...")
pages = []
with fitz.open(pdf_path) as doc:
    for i in range(min(5, len(doc))):
        pages.append(doc[i].get_text())

full_text = "\n\n".join(pages)
print(f"Text length: {len(full_text)} chars")

# Get embedding
print("Getting embedding from Ollama...")
response = ollama.embeddings(model="nomic-embed-text", prompt=full_text[:4000])
vec = response["embedding"]
print(f"Vector dimension: {len(vec)}")

# Test Qdrant upload
print("Uploading to Qdrant...")
client = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
point_id = str(uuid.uuid4())
client.upsert(
    collection_name="books_hot",
    points=[PointStruct(
        id=point_id,
        vector=vec,
        payload={"test": True, "pages": "1-5"}
    )]
)

print(f"✅ Success! Point ID: {point_id}")

# Verify
result = client.retrieve(collection_name="books_hot", ids=[point_id])
print(f"Retrieved: {len(result)} point(s)")
