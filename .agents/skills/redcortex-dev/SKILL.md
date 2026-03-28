---
name: redcortex-dev
description: RedCortex project development guidelines and workflows
---

# RedCortex Development Guide

RedCortex is a production-grade RAG system for technical books, built with Qdrant, Ollama, and OpenRouter.

## Quick Commands

```bash
# Health check
python src/utils/health_check.py

# CLI Query
python src/query.py "How do I create a user in RHEL?"

# Web UI
streamlit run src/web_ui.py

# API Server
python src/api/main.py

# Ingest a book
python src/ingestion/ingest.py "path/to/book.pdf" "Book Title" red_hat
```

## Project Structure

```
RedCortex/
├── src/
│   ├── api/main.py           # FastAPI server
│   ├── rag_pipeline.py       # Core RAG logic
│   ├── ingestion/ingest.py   # PDF processing
│   ├── utils/                # Utilities
│   └── evaluation/           # RAG evaluation
├── tests/                    # Test suite
├── scripts/                  # Deployment scripts
└── data/                     # SQLite + cache
```

## Code Style

### Python Conventions

1. **Shebang**: `#!/usr/bin/env python3` for executable scripts
2. **Project Root Navigation**:
   ```python
   import os
   os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```
3. **Environment Loading**:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```
4. **Import Pattern**:
   ```python
   import sys
   sys.path.insert(0, 'src')
   from rag_pipeline import hybrid_search
   ```
5. **Type Hints**: Use for all function signatures
6. **Constants**: UPPER_SNAKE_CASE for config
7. **Error Handling**: Try-except with meaningful messages

## Environment Variables

Required in `.env`:
```bash
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key
OPENROUTER_API_KEY=your-openrouter-api-key
# Optional: OLLAMA_HOST=http://localhost:11434
```

## Database Schema

### Books Table
```sql
CREATE TABLE books (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    author TEXT,
    category TEXT CHECK(category IN ('security', 'red_hat', 'ai_engineering', 'other')),
    file_path TEXT UNIQUE,
    total_pages INTEGER,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Chunks Table
```sql
CREATE TABLE chunks (
    id INTEGER PRIMARY KEY,
    book_id INTEGER REFERENCES books(id),
    parent_id INTEGER,
    qdrant_id TEXT,
    content TEXT,
    summary TEXT,
    page_start INTEGER,
    page_end INTEGER,
    token_count INTEGER,
    is_hot BOOLEAN DEFAULT 0
);
```

## Testing Strategy

1. **Quick validation**: `python tests/test_queries.py --quick`
2. **Full suite (no LLM)**: `python tests/test_queries.py --no-llm`
3. **Full suite (with LLM)**: `python tests/test_queries.py`

## Adding Features

1. Update `AGENTS.md` if changing architecture
2. Add tests for new functionality
3. Run health check before committing
4. Update documentation

## Deployment

Mac Mini 24/7 ingestion:
```bash
./scripts/batch_ingest.sh
tail -f logs/ingest_*.log
./scripts/monitor.sh
```
