import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

url = os.getenv("QDRANT_API_KEY")
api_key = os.getenv("QDRANT_API_KEY")

# Fix: URL was swapped
url = os.getenv("QDRANT_URL")

print(f"Connecting to: {url}")

try:
    client = QdrantClient(url=url, api_key=api_key)
    
    # Test with get_collections (works for cloud)
    collections = client.get_collections()
    print("✅ Qdrant connection successful!")
    print(f"   Existing collections: {len(collections.collections)}")
    for c in collections.collections:
        print(f"     - {c.name}")
    
    # Check cluster info
    cluster_info = client.info()
    print(f"   Version: {cluster_info.version}")
    print(f"   Title: {cluster_info.title}")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    import traceback
    traceback.print_exc()
