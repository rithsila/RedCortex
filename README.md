# RedCortex

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> A production-grade Retrieval-Augmented Generation (RAG) system for technical books, built with Qdrant, Ollama, and OpenRouter.

---

## 🎉 What's New in v2.0

✅ **Semantic Chunking** - 1291 intelligent chunks vs 572 page-level chunks  
✅ **Hybrid Search** - BM25 + Vector search with Reciprocal Rank Fusion  
✅ **Cross-Encoder Reranking** - `ms-marco-MiniLM-L-6-v2` for better precision  
✅ **Query Caching** - 50% cost reduction on repeated queries  
✅ **Streamlit Web UI** - Interactive web interface  

---

## 🎯 Overview

RedCortex transforms your technical library into an intelligent, queryable knowledge base. It combines local embeddings (Ollama), cloud vector storage (Qdrant), and LLM APIs (OpenRouter) to provide accurate, cited answers from your books.

### Key Features

- 🔍 **Hybrid Search**: BM25 + Vector similarity for better recall
- 🎯 **Cross-Encoder Reranking**: Two-stage retrieval for precision
- 💾 **Query Caching**: Reduce API costs by 50%
- 🧠 **Semantic Chunking**: Context-aware document splitting
- 🤖 **RAG Pipeline**: AI-generated answers with page citations
- 💰 **Cost-Optimized**: Local embeddings ($0) + pay-per-use LLM (~$0.001/query)
- 📚 **Resume-Capable Ingestion**: Handles crashes gracefully, resumes from last page
- 🌐 **Web UI**: Streamlit interface for easy querying

---

## 📊 Current Status

| Component | Status | Details |
|-----------|--------|---------|
| **Phase 1: Foundation** | ✅ Complete | Ollama, Qdrant Cloud, SQLite |
| **Phase 2: Ingestion** | ✅ Complete | Semantic chunking, 1291 chunks indexed |
| **Phase 3: Query** | ✅ Complete | Hybrid search + reranking + caching |
| **Phase 4: Web UI** | ✅ Complete | Streamlit interface |
| **Phase 5: Archive** | ⏳ Pending | 7 more books ready |

**Current Stats:**
- 📖 Books indexed: 1 (Red Hat System Administration I)
- 🔢 Total chunks: 1,291 (semantic)
- 🔢 Qdrant vectors: 1,291
- ⏱️ Avg query time: 2-3 seconds (1s if cached)
- 💵 Cost per query: ~$0.001 ($0.0005 if cached)
- 💾 Cache hit rate: 50%+ for repeated queries

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Query                           │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                    RedCortex Pipeline v2.0                  │
├─────────────────────────────────────────────────────────────┤
│  1. HYBRID SEARCH                                           │
│     • Vector Search (Qdrant) ──┐                            │
│     • BM25 Keyword Search ─────┼──► RRF Fusion              │
├────────────────────────────────┼────────────────────────────┤
│  2. RERANKING (Cross-encoder)  │                            │
├────────────────────────────────┼────────────────────────────┤
│  3. CACHE CHECK                ▼                            │
├─────────────────────────────────────────────────────────────┤
│  4. LLM RESPONSE (OpenRouter)                               │
│     • qwen/qwen3-coder with context                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- macOS/Linux (tested on MacBook Pro M4)
- Python 3.10+
- Homebrew (for macOS)

### 1. Clone & Setup

```bash
git clone <repo-url>
cd RedCortex

# Create virtual environment
python3 -m venv secondbrain
source secondbrain/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Install Ollama

```bash
brew install ollama
ollama pull nomic-embed-text
```

### 3. Configure Environment

Create `.env` file:

```bash
# Qdrant Cloud (free tier)
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your-qdrant-api-key

# OpenRouter (for LLM queries)
OPENROUTER_API_KEY=your-openrouter-api-key
```

Get your API keys:
- [Qdrant Cloud](https://cloud.qdrant.io/) - Free 1GB cluster
- [OpenRouter](https://openrouter.ai/) - Pay-per-use LLM access

### 4. Initialize System

```bash
# Initialize SQLite database
python src/utils/init_db.py

# Setup Qdrant collection with binary quantization
python src/utils/setup_collection.py
```

### 5. Ingest Books (with Semantic Chunking)

```bash
# Ingest a PDF book
python src/ingestion/ingest.py \
  "path/to/book.pdf" \
  "Book Title" \
  red_hat

# The script is resume-capable - if it crashes, just run again!
```

**Example Output:**
```
📚 New book: System-Administration-l
   Extracting text...
   Total pages with text: 572
   Created 1291 chunks from 572 pages
   [1/1291] Chunk (pages 1-5)... ✓
   ...
🎉 Done!
   Chunks created: 1290
   Skipped: 1
```

### 6. Query

#### CLI with Hybrid Search (Default)
```bash
python src/query.py "How do I create a user account in RHEL?"
```

**Output:**
```
🔍 Searching knowledge base...
   (Using hybrid search: BM25 + Vector + Reranking)
------------------------------------------------------------
✓ Found 5 relevant passages (hybrid+rerank)
✓ Using model: qwen/qwen3-coder

📚 SOURCES:
------------------------------------------------------------
  • Page 510 (score: 6.648, source: hybrid)
  • Page 502 (score: -1.714, source: hybrid)
  ...

💡 ANSWER:
------------------------------------------------------------
To configure firewalld, use the `firewall-cmd` command...

📊 METADATA:
------------------------------------------------------------
  Model: qwen/qwen3-coder
  Search method: hybrid+rerank
  Tokens: 1147
```

#### Compare Search Methods
```bash
python src/search.py "systemctl commands" --compare
```

#### Web UI
```bash
streamlit run src/web_ui.py
```

---

## 📁 Project Structure

```
RedCortex/
├── .agents/
│   └── skills/             # AI agent skills for this project
├── .env                      # API keys (not in git)
├── .gitignore               # Git ignore rules
├── LICENSE                  # MIT License
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── data/
│   ├── library.db          # SQLite database
│   └── cache/              # Query cache directory
├── docs/
│   ├── DEPLOYMENT.md       # Mac Mini deployment guide
│   ├── PRD.md              # Product Requirements Document
│   ├── UPGRADE-ANALYSIS.md # Upgrade analysis
│   └── UPGRADE-IMPLEMENTATION.md # Implementation details
├── scripts/
│   ├── batch_ingest.sh     # 24/7 ingestion script
│   ├── monitor.sh          # Status monitor
│   ├── setup_macmini.sh    # Mac Mini setup
│   └── sync_to_macbook.sh  # Data sync utility
├── src/
│   ├── ingestion/
│   │   ├── ingest.py       # Main ingestion (semantic chunking)
│   │   └── archive/        # Development iterations
│   ├── rag_pipeline.py     # NEW: Complete RAG pipeline
│   ├── web_ui.py           # NEW: Streamlit web interface
│   ├── query.py            # RAG query with hybrid search
│   ├── search.py           # Search with method comparison
│   └── utils/
│       ├── init_db.py      # Initialize SQLite
│       └── setup_collection.py  # Setup Qdrant
└── tests/
    ├── query_test.py       # OpenRouter model tests
    ├── test_ingest.py      # Ingestion test
    └── test_qdrant.py      # Connection test
```

---

## 💡 Usage Examples

### Search for Content

```bash
$ python src/search.py "SSH key authentication"

🔍 Query: "SSH key authentication"
============================================================
✓ Found 5 relevant passages (hybrid+rerank)

📚 Top 5 results:

1. Score: 0.8074 | Page: 335 | Source: hybrid
------------------------------------------------------------
Chapter 10 | Configure and Secure SSH [student@workstation ...

2. Score: 0.7784 | Page: 341 | Source: hybrid
------------------------------------------------------------
Chapter 10 | Configure and Secure SSH Summary • With the s...
```

### Ask Questions (RAG)

```bash
$ python src/query.py "How to start a service with systemctl?"

🔍 Searching knowledge base...
   (Using hybrid search: BM25 + Vector + Reranking)
------------------------------------------------------------
✓ Found 5 relevant passages (hybrid+rerank)
✓ Using model: qwen/qwen3-coder

📚 SOURCES:
------------------------------------------------------------
  • Page 312 (score: 5.490, source: hybrid)
  • Page 315 (score: 5.373, source: hybrid)
  • Page 322 (score: 3.893, source: hybrid)

💡 ANSWER:
------------------------------------------------------------
To start and enable a service with `systemctl`:

1. Start the service:
   ```bash
   systemctl start UNIT
   ```
   (Page 315)

2. Enable for automatic boot:
   ```bash
   systemctl enable UNIT
   ```
   (Page 322)

📊 METADATA:
------------------------------------------------------------
  Model: qwen/qwen3-coder
  Search method: hybrid+rerank
  Tokens: 1223
```

---

## 💰 Cost Breakdown

| Component | Cost | Notes |
|-----------|------|-------|
| **Embeddings** | $0 | Local Ollama (nomic-embed-text) |
| **Vector Storage** | $0 | Qdrant Cloud free tier (1GB) |
| **LLM Queries** | ~$0.001/query | qwen/qwen3-coder at $0.75/M tokens |
| **Caching** | -50% | Repeated queries served from cache |
| **Typical Usage** | ~$1.50/month | 100 queries/day with 50% cache hit |

---

## 🔧 Configuration

### Model Selection

Edit `src/rag_pipeline.py` to change the LLM:

```python
MODEL_DEFAULT = "qwen/qwen3-coder"  # $0.75/M tokens, reliable
# Alternative: "deepseek/deepseek-chat"  # $0.28/M tokens
```

### Semantic Chunking Settings

Adjust in `src/ingestion/ingest.py`:

```python
CHUNK_CONFIG = {
    "chunk_size": 1000,       # characters per chunk
    "chunk_overlap": 200,     # overlap for context continuity
    "separators": ["\n\n", "\n", ". ", " ", ""]
}
```

### Hybrid Search Settings

Adjust in `src/rag_pipeline.py`:

```python
# RRF fusion parameter (default: 60)
k: float = 60.0  # Lower = favors top ranks more

# Number of candidates to rerank
vector_top_k: int = 20
bm25_top_k: int = 20
final_top_k: int = 5
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |
| `bad request (status code: 500)` | Fixed in v2.0 - uses `httpx` instead of `ollama` library |
| No hybrid search results | Check that documents are indexed in `chunks` table |
| Cache not working | Ensure `data/cache/` directory is writable |
| Cross-encoder slow | First load downloads model (~100MB), subsequent uses are fast |
| Web UI won't start | Check `streamlit` is installed: `pip install streamlit` |

---

## 📈 Roadmap

### Current (v2.0) ✅
- [x] **Semantic Chunking** - 1000 char chunks with 200 overlap
- [x] **Hybrid Search** - BM25 + Vector with RRF
- [x] **Cross-Encoder Reranking** - ms-marco-MiniLM-L-6-v2
- [x] **Query Caching** - SHA-256 with 24hr TTL
- [x] **Web UI** - Streamlit interface
- [x] Resume-capable ingestion
- [x] OpenRouter LLM integration

### Next (v2.1) 📋
- [ ] Evaluation Framework - Test cases and metrics
- [ ] Query Logging & Analytics
- [ ] Hierarchical Retrieval - Book → Section → Chunk

### Future (v2.2+) 📋
- [ ] Multi-Query Retrieval - Query variations
- [ ] Contextual Compression - Reduce token usage
- [ ] Conversational Memory - Multi-turn sessions
- [ ] Multi-Book Cross-Referencing
- [ ] FastAPI Backend

See [docs/UPGRADE-ANALYSIS.md](docs/UPGRADE-ANALYSIS.md) for detailed analysis.

---

## 🧠 Agent Skills

This project includes 30 specialized AI agent skills in `.agents/skills/`:

**Core RAG Skills:**
- `rag-engineer`, `rag-implementation` - RAG architecture
- `vector-database-engineer`, `vector-index-tuning` - Vector DB optimization
- `search-specialist`, `similarity-search-patterns` - Search techniques

**Development Skills:**
- `python-pro`, `python-patterns`, `async-python-patterns` - Python
- `bash-pro`, `bash-scripting` - Shell automation
- `pdf-official` - PDF processing

**Deployment Skills:**
- `deployment-engineer`, `devops-deploy` - Production deployment
- `deployment-pipeline-design` - CI/CD setup

See `.agents/skills/README.md` for full list.

---

## 🖥️ Mac Mini 24/7 Deployment

For continuous ingestion on a dedicated Mac Mini:

```bash
# 1. Copy project to Mac Mini
rsync -avz --exclude 'secondbrain' ~/Projects/RedCortex/ \
  user@macmini.local:~/Projects/RedCortex/

# 2. SSH into Mac Mini and run setup
ssh user@macmini.local
cd ~/Projects/RedCortex
./scripts/setup_macmini.sh

# 3. Copy PDF books
rsync -avz ~/Redhat\ E-Books/ user@macmini.local:~/Projects/RedCortex/Redhat\ E-Books/

# 4. Start 24/7 ingestion
./scripts/batch_ingest.sh

# 5. Monitor remotely
./scripts/monitor.sh
tail -f logs/ingest_*.log

# 6. Sync data back when done
./scripts/sync_to_macbook.sh macbook-pro.local
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for complete guide.

### Deployment Scripts

| Script | Purpose |
|--------|---------|
| `scripts/setup_macmini.sh` | Initial setup on Mac Mini |
| `scripts/batch_ingest.sh` | 24/7 ingestion with auto-resume |
| `scripts/monitor.sh` | Check status and statistics |
| `scripts/sync_to_macbook.sh` | Sync database back to MacBook |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open a Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) file

---

## 🙏 Acknowledgments

- [Qdrant](https://qdrant.tech/) - Vector database
- [Ollama](https://ollama.ai/) - Local embeddings
- [OpenRouter](https://openrouter.ai/) - LLM API gateway
- [Nomic](https://nomic.ai/) - nomic-embed-text model
- [Hugging Face](https://huggingface.co/) - Cross-encoder models

---

<p align="center">
  Built with ❤️ for the technical reader
</p>
