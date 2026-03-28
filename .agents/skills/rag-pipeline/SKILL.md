---
name: rag-pipeline
description: RAG pipeline development and optimization for RedCortex
---

# RAG Pipeline Development

This skill guides development and optimization of the Retrieval-Augmented Generation pipeline in RedCortex.

## Architecture Overview

```
Query → Hybrid Search (BM25 + Vector) → Reranking → LLM → Response
            ↓                              ↓
        Qdrant Cloud                 Cross-encoder
        (nomic-embed-text)           (msmarco)
```

## Key Components

### 1. Embedding Generation
- **Model**: nomic-embed-text via Ollama
- **Dimensions**: 768
- **Host**: http://localhost:11434 (configurable via OLLAMA_HOST)

### 2. Vector Database
- **Service**: Qdrant Cloud
- **Collection**: books_hot
- **Distance**: Cosine
- **Quantization**: Binary

### 3. Hybrid Search
- **Vector search**: Semantic similarity
- **BM25**: Keyword-based ranking
- **Fusion**: Reciprocal Rank Fusion (RRF, k=60)

### 4. Reranking
- **Model**: cross-encoder/ms-marco-MiniLM-L-6-v2
- **Top-k**: 20 → 5 after reranking

## Development Guidelines

### Adding a New Search Method

1. Implement in `src/rag_pipeline.py`
2. Add to `hybrid_search()` function
3. Update `SearchResult.source` field
4. Add tests in `tests/test_queries.py`
5. Update API in `src/api/main.py`

### Modifying Chunking Strategy

Current config in `src/ingestion/ingest.py`:
```python
CHUNK_CONFIG = {
    "chunk_size": 1000,       # characters (~250-300 tokens)
    "chunk_overlap": 200,     # overlap for context continuity
    "separators": ["\n\n", "\n", ". ", " ", ""]
}
```

### Query Cache Implementation

- **Key**: SHA-256 of query string
- **TTL**: 24 hours
- **Location**: `data/cache/`
- **Format**: JSON

## Common Tasks

### Debugging Search Quality

```python
# Run search comparison
python src/search.py "your query" --compare

# Test with specific method
python src/search.py "your query" --no-hybrid  # Vector only
```

### Evaluating Retrieval Performance

```bash
# Run evaluation
python src/evaluation/evaluator.py
python src/evaluation/evaluator.py --compare  # Hybrid vs Vector
```

### Testing the Pipeline

```bash
# Quick test (3 queries, no LLM)
python tests/test_queries.py --quick

# Full test suite without LLM
python tests/test_queries.py --no-llm

# Full test with LLM (~$0.01 cost)
python tests/test_queries.py
```

## Performance Optimization

### Vector Search
- Use binary quantization for memory efficiency
- Consider HNSW index tuning for latency vs recall trade-off

### BM25
- Pre-tokenize documents during ingestion
- Tune k1 and b parameters for your corpus

### Caching
- Monitor cache hit rates via SQLite queries
- Adjust TTL based on query patterns

## Error Handling

Common issues and solutions:

| Issue | Solution |
|-------|----------|
| Ollama connection error | Check OLLAMA_HOST, start Ollama |
| Qdrant auth error | Verify QDRANT_URL and QDRANT_API_KEY |
| No search results | Check chunks exist in Qdrant |
| Slow cross-encoder | First run downloads model (~100MB) |
| Cache not working | Ensure data/cache/ is writable |

## References

- Main pipeline: `src/rag_pipeline.py`
- Ingestion: `src/ingestion/ingest.py`
- API: `src/api/main.py`
- Tests: `tests/test_queries.py`
