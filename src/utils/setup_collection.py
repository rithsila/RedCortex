#!/usr/bin/env python3
"""Setup Qdrant collection with binary quantization"""
import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, 
    Distance, 
    BinaryQuantization,
    BinaryQuantizationConfig,
    OptimizersConfigDiff
)

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
load_dotenv()

client = QdrantClient(
    url=os.getenv("QDRANT_URL"),
    api_key=os.getenv("QDRANT_API_KEY")
)

COLLECTION_NAME = "books_hot"

collections = client.get_collections()
exists = any(c.name == COLLECTION_NAME for c in collections.collections)

if exists:
    print(f"⚠️  Collection '{COLLECTION_NAME}' already exists")
    info = client.get_collection(COLLECTION_NAME)
    print(f"   Vectors count: {info.points_count}")
else:
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=768, distance=Distance.COSINE),
        quantization_config=BinaryQuantization(
            binary=BinaryQuantizationConfig(always_ram=True)
        ),
        optimizers_config=OptimizersConfigDiff(indexing_threshold=1000)
    )
    print(f"✅ Collection '{COLLECTION_NAME}' created with binary quantization")

info = client.get_collection(COLLECTION_NAME)
print(f"\n📊 Collection: {info.points_count} points, status: {info.status}")
