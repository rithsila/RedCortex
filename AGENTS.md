# RedCortex - AI Agent Guide

> This file contains essential information for AI coding agents working on the RedCortex project.

## Project Overview

**RedCortex** is a production-grade Retrieval-Augmented Generation (RAG) system for technical books, built with Qdrant, Ollama, and OpenRouter. It transforms technical library PDFs into an intelligent, queryable knowledge base.

### Key Features
- **Hybrid Search**: BM25 + Vector similarity with Reciprocal Rank Fusion (RRF)
- **Cross-Encoder Reranking**: Two-stage retrieval for precision
- **Query Caching**: SHA-256 based caching with 24hr TTL (50% cost reduction)
- **Semantic Chunking**: Context-aware document splitting using RecursiveCharacterTextSplitter
- **Resume-Capable Ingestion**: Handles crashes gracefully, resumes from last page
- **FastAPI Backend**: REST API with `/query`, `/health`, `/stats` endpoints
- **Streamlit Web UI**: Interactive web interface

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Language | Python 3.10+ | Core runtime |
| Vector DB | Qdrant Cloud | Vector storage and similarity search |
| Embeddings | Ollama (nomic-embed-text) | Local embedding generation |
| LLM | OpenRouter (qwen/qwen3-coder) | Text generation |
| Database | SQLite | Metadata and query logging |
| API | FastAPI | REST API backend |
| Web UI | Streamlit | Interactive interface |
| Chunking | LangChain | Semantic text splitting |
| Search | rank-bm25, sentence-transformers | Keyword search and reranking |

## Project Structure

```
RedCortex/
├── .env                      # API keys (NOT in git)
├── .env.example              # Environment template
├── requirements.txt          # Python dependencies
├── README.md                 # User documentation
├── AGENTS.md                 # This file
│
├── src/                      # Source code
│   ├── api/
│   │   ├── __init__.py
│   │   └── main.py           # FastAPI server (v2.1.0)
│   ├── evaluation/
│   │   └── evaluator.py      # RAG evaluation framework
│   ├── ingestion/
│   │   ├── ingest.py         # Main ingestion (semantic chunking)
│   │   └── archive/          # Development iterations
│   ├── utils/
│   │   ├── health_check.py   # System validation (9 checks)
│   │   ├── init_db.py        # Initialize SQLite schema
│   │   ├── query_logger.py   # Analytics and logging
│   │   └── setup_collection.py  # Qdrant collection setup
│   ├── rag_pipeline.py       # Core RAG pipeline
│   ├── query.py              # CLI query tool
│   ├── search.py             # Search comparison tool
│   ├── hierarchical_retrieval.py  # Multi-level search
│   ├── multi_query_retrieval.py   # Query variations
│   └── web_ui.py             # Streamlit interface
│
├── tests/                    # Test suite
│   ├── test_queries.py       # 10 RHEL-focused test queries
│   ├── test_qdrant.py        # Connection test
│   ├── test_ingest.py        # Ingestion test
│   └── query_test.py         # OpenRouter model tests
│
├── scripts/                  # Deployment scripts
│   ├── batch_ingest.sh       # 24/7 ingestion script
│   ├── monitor.sh            # Status monitor
│   ├── setup_macmini.sh      # Mac Mini setup
│   └── sync_to_macbook.sh    # Data sync utility
│
├── docs/                     # Documentation
│   ├── DEPLOYMENT.md         # Mac Mini deployment guide
│   ├── PRD.md                # Product Requirements
│   ├── UPGRADE-ANALYSIS.md   # Upgrade analysis
│   └── UPGRADE-IMPLEMENTATION.md
│
└── data/                     # Data directory
    ├── library.db            # SQLite database
    └── cache/                # Query cache (JSON files)
```

## Environment Configuration

Create `.env` file from `.env.example`:

```bash
# Qdrant Cloud (free tier available)
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key

# OpenRouter (for LLM queries)
OPENROUTER_API_KEY=your-openrouter-api-key

# Optional: Ollama host (default: http://localhost:11434)
OLLAMA_HOST=http://localhost:11434
```

**Never commit `.env` to git.** It's already in `.gitignore`.

## Build and Setup Commands

### Initial Setup

```bash
# 1. Create virtual environment
python3 -m venv secondbrain
source secondbrain/bin/activate  # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Install Ollama and pull model
brew install ollama
ollama pull nomic-embed-text

# 4. Initialize database
python src/utils/init_db.py

# 5. Setup Qdrant collection
python src/utils/setup_collection.py

# 6. Verify setup
python src/utils/health_check.py
```

### Running the System

```bash
# CLI Query (hybrid search default)
python src/query.py "How do I create a user account in RHEL?"
python src/query.py "How do I create a user account in RHEL?" --no-hybrid

# Search comparison
python src/search.py "systemctl commands"
python src/search.py "systemctl commands" --compare

# Hierarchical retrieval
python src/hierarchical_retrieval.py "How to configure SSH?"

# Web UI
streamlit run src/web_ui.py

# FastAPI Backend
python src/api/main.py
# API docs at: http://localhost:8000/docs

# Ingest a book
python src/ingestion/ingest.py \
  "path/to/book.pdf" \
  "Book Title" \
  red_hat
```

### Testing

```bash
# Quick health check (3 queries, no LLM)
python tests/test_queries.py --quick

# Full test suite without LLM (saves costs)
python tests/test_queries.py --no-llm

# Full test suite with LLM (~$0.01 cost)
python tests/test_queries.py

# Qdrant connection test
python tests/test_qdrant.py

# Run evaluation
python src/evaluation/evaluator.py
python src/evaluation/evaluator.py --compare  # Hybrid vs Vector
```

### Monitoring and Analytics

```bash
# System health check (9 components)
python src/utils/health_check.py

# Query analytics
python src/utils/query_logger.py stats [days]
python src/utils/query_logger.py recent [limit]

# Bash monitor script
./scripts/monitor.sh
```

## Code Style Guidelines

### Python Conventions

1. **Shebang**: All executable scripts start with `#!/usr/bin/env python3`

2. **Project Root Navigation**: Scripts must change to project root:
   ```python
   import os
   os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   ```

3. **Environment Loading**: Always load `.env` at module level:
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

4. **Import Pattern**: Use sys.path.insert for cross-module imports:
   ```python
   import sys
   sys.path.insert(0, 'src')
   from rag_pipeline import hybrid_search
   ```

5. **Type Hints**: Use typing for function signatures:
   ```python
   from typing import List, Dict, Tuple, Optional
   
   def hybrid_search(
       query: str,
       top_k: int = 5,
       enable_hybrid: bool = True
   ) -> Tuple[List[SearchResult], str]:
       ...
   ```

6. **Constants**: Use UPPER_SNAKE_CASE for config constants:
   ```python
   EMBED_MODEL = "nomic-embed-text"
   COLLECTION_NAME = "books_hot"
   CACHE_TTL = 24 * 3600  # 24 hours
   ```

7. **Error Handling**: Use try-except with meaningful messages:
   ```python
   try:
       result = risky_operation()
   except Exception as e:
       raise Exception(f"Contextual error message: {e}")
   ```

### File Organization

- **Core Pipeline**: `src/rag_pipeline.py` - All search and LLM logic
- **Ingestion**: `src/ingestion/ingest.py` - PDF processing and indexing
- **API**: `src/api/main.py` - FastAPI endpoints
- **Utils**: `src/utils/` - Helper modules with standalone CLIs
- **Tests**: `tests/` - All test scripts executable standalone

## Database Schema

### SQLite (data/library.db)

```sql
-- Books table
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

-- Chunks table
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
    is_hot BOOLEAN DEFAULT 0,
    embedding_blob BLOB
);

-- Queries table (with analytics columns)
CREATE TABLE queries (
    id INTEGER PRIMARY KEY,
    question TEXT,
    query_hash TEXT,
    model_used TEXT,
    search_method TEXT,
    latency_ms INTEGER,
    cost_usd REAL,
    sources_count INTEGER DEFAULT 0,
    cache_hit BOOLEAN DEFAULT 0,
    error TEXT,
    user_feedback INTEGER,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Qdrant Collection (books_hot)

- **Vectors**: 768 dimensions (nomic-embed-text)
- **Distance**: Cosine
- **Payload**: `book_id`, `parent_id` (SQLite chunk ID), `category`, `page`
- **Quantization**: Binary (for memory efficiency)

## Key Configuration Values

### Semantic Chunking (src/ingestion/ingest.py)

```python
CHUNK_CONFIG = {
    "chunk_size": 1000,       # characters (~250-300 tokens)
    "chunk_overlap": 200,     # overlap for context continuity
    "separators": ["\n\n", "\n", ". ", " ", ""]
}
```

### Hybrid Search (src/rag_pipeline.py)

```python
# RRF fusion parameter (lower = favors top ranks more)
k: float = 60.0

# Retrieval counts
vector_top_k: int = 20
bm25_top_k: int = 20
final_top_k: int = 5
```

### LLM Configuration

```python
MODEL_DEFAULT = "qwen/qwen3-coder"  # $0.75/M tokens
# Alternative: "deepseek/deepseek-chat"  # $0.28/M tokens

# Generation params
temperature: float = 0.1
max_tokens: int = 1000
timeout: int = 60  # seconds
```

## Testing Strategy

### Test Categories

1. **Unit Tests**: Individual component tests in `tests/`
2. **Integration Tests**: `test_queries.py` with real RAG pipeline
3. **Health Checks**: `health_check.py` validates all 9 components
4. **Evaluation**: `evaluator.py` measures Recall@5, MRR, Keyword Match

### Test Data

- 10 RHEL-focused test queries in `tests/test_queries.py`
- Expected keywords defined per query for validation
- Sample expected page numbers for retrieval metrics

### Running Tests

```bash
# Quick validation (recommended before commits)
python tests/test_queries.py --quick

# Full validation
python src/utils/health_check.py && python tests/test_queries.py --quick
```

## Security Considerations

1. **API Keys**: 
   - Store in `.env` file only
   - Never log or print API keys
   - File permissions: `chmod 600 .env`

2. **Input Validation**:
   - All API endpoints validate Pydantic models
   - Query length limits (3-1000 chars)
   - SQL parameterized queries only

3. **CORS**: FastAPI configured with permissive CORS for development
   ```python
   allow_origins=["*"]  # Configure for production
   ```

4. **Database**:
   - SQLite file should not be publicly accessible
   - No sensitive data in vector payloads

## Deployment Notes

### Mac Mini 24/7 Ingestion

See `docs/DEPLOYMENT.md` for complete guide.

Quick commands:
```bash
# Start batch ingestion
./scripts/batch_ingest.sh

# Monitor progress
tail -f logs/ingest_*.log
./scripts/monitor.sh

# Sync data back
./scripts/sync_to_macbook.sh macbook-pro.local
```

### Environment Variables for Deployment

```bash
# Ingestion-specific
export OLLAMA_KEEP_ALIVE=60m
export PROJECT_DIR="$HOME/Projects/RedCortex"
```

## Common Tasks

### Adding a New Search Method

1. Implement in `src/rag_pipeline.py`
2. Add to `hybrid_search()` function
3. Update `SearchResult.source` field
4. Add tests in `tests/test_queries.py`
5. Update API in `src/api/main.py`

### Adding a New API Endpoint

1. Add Pydantic model for request/response
2. Implement endpoint in `src/api/main.py`
3. Add to appropriate router tag
4. Test with `curl` or interactive docs

### Modifying Database Schema

1. Update `src/utils/init_db.py`
2. Add migration logic to handle existing data
3. Update `query_logger.py` if queries table affected
4. Test with fresh and existing databases

### Ingesting New Books

1. Add PDF to `Redhat E-Books/` directory
2. Run: `python src/ingestion/ingest.py "path" "Title" category`
3. Script is resume-capable - safe to re-run
4. Verify with: `python src/utils/health_check.py`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| Ollama connection error | Check `OLLAMA_HOST` env var, start Ollama |
| Qdrant auth error | Verify `QDRANT_URL` and `QDRANT_API_KEY` |
| No search results | Check chunks exist: `SELECT COUNT(*) FROM chunks WHERE is_hot=1` |
| Cache not working | Ensure `data/cache/` is writable |
| Cross-encoder slow | First run downloads model (~100MB) |

## Kimi CLI Integration

This project includes Kimi CLI-specific configurations adapted from the **everything-claude-code** (ECC) performance optimization system.

### ⚠️ Important: Command Syntax Difference

**Claude Code (ECC)** uses: `/tdd`, `/code-review`

**Kimi CLI** uses: `/skill:<name>` or `/flow:<name>`

### ECC → Kimi Command Mapping

| ECC Command | Kimi CLI Equivalent |
|-------------|---------------------|
| `/plan "feature"` | Create a plan using the planner subagent |
| `/tdd` | `/skill:tdd-python` |
| `/code-review` | Ask for code review with quality guidelines |
| `/security-scan` | `/skill:security-review` (after install) |
| `/build-fix` | Use `coder` subagent directly |
| `/refactor-clean` | Use `explore` subagent for analysis |
| `/skill-create` | Built-in Kimi skill! |

### Available Flow Skills (Use `/flow:<name>`)

| Command | Purpose | Usage |
|---------|---------|-------|
| `tdd-workflow` | TDD RED-GREEN-IMPROVE cycle | `/flow:tdd-workflow` |
| `code-review` | Comprehensive code review | `/flow:code-review` |
| `security-review` | Security audit | `/flow:security-review` |
| `plan-feature` | Implementation planning | `/flow:plan-feature` |

### Available Regular Skills (Use `/skill:<name>`)

| Skill | Purpose | Usage |
|-------|---------|-------|
| `rag-pipeline` | RAG development and optimization | `/skill:rag-pipeline` |
| `redcortex-dev` | Project-specific guidelines | `/skill:redcortex-dev` |
| `tdd-python` | Python TDD patterns | `/skill:tdd-python` |
| `tdd-workflow` | TDD methodology (knowledge) | `/skill:tdd-workflow` |
| `code-review` | Code review guide | `/skill:code-review` |
| `security-review` | Security checklist | `/skill:security-review` |

### Available Subagents (`.agents/subagents/`)

Mention these in prompts:
- `code-reviewer` - Code quality and security review
- `planner` - Implementation planning
- `rag-expert` - Vector search and RAG specialist

### Using with Kimi CLI

```bash
# Start Kimi CLI in project directory
kimi

# Run a flow (executes workflow)
> /flow:tdd-workflow

# Load skill knowledge with task
> /skill:rag-pipeline How do I optimize the hybrid search?

# Use with specific task
> /skill:tdd-python Create tests for the query function

# Use built-in subagent types
> Use the plan subagent to analyze the codebase structure

# Direct code review
> /skill:code-review Review src/rag_pipeline.py
```

See `docs/KIMI-COMMANDS-GUIDE.md` for detailed command reference.

### Installing ECC Skills System-Wide

```bash
# Run the installer script
./scripts/install-ecc-for-kimi.sh

# Or with full skill set
./scripts/install-ecc-for-kimi.sh https://github.com/affaan-m/everything-claude-code.git --full
```

See `docs/ECC-KIMI-ADAPTER.md` for complete documentation on adapting everything-claude-code to Kimi CLI.

## Resources

- **Qdrant Cloud**: https://cloud.qdrant.io/
- **OpenRouter**: https://openrouter.ai/
- **Ollama**: https://ollama.ai/
- **Skills**: Check `.agents/skills/` for specialized knowledge
- **Kimi CLI Docs**: https://moonshotai.github.io/kimi-cli/
- **Everything Claude Code**: https://github.com/affaan-m/everything-claude-code

---

*Last updated: 2026-03-26*
*Version: 2.2*
