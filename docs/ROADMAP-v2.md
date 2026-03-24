# RedCortex v2.0 - Roadmap & Progress

> Comprehensive upgrade plan based on RAG best practices and LLM application patterns

---

## 🎉 Current Status: v2.0 RELEASED (March 2026)

### Executive Summary

**v2.0 State (Current):**
- ✅ **Semantic Chunking** - RecursiveCharacterTextSplitter with 1000 char chunks, 200 overlap
- ✅ **Hybrid Search** - BM25 + Vector with Reciprocal Rank Fusion (RRF)
- ✅ **Cross-Encoder Reranking** - ms-marco-MiniLM-L-6-v2
- ✅ **Query Caching** - SHA-256 with 24hr TTL (~50% cost reduction)
- ✅ **Streamlit Web UI** - Full interface with analytics dashboard
- ✅ **Query Logging & Analytics** - SQLite-based with CLI tools
- ✅ **Health Check System** - Comprehensive system validation
- ✅ **Test Query Suite** - 10 RHEL-focused test cases
- ✅ **Resume-capable ingestion** - Crash recovery built-in
- ⏳ **Hierarchical Retrieval** - Planned for v2.1
- ⏳ **FastAPI Backend** - Planned for v2.1
- ⏳ **Evaluation Framework** - Planned for v2.1

**Current Stats (March 2026):**
- 📖 Books indexed: 1 (Red Hat System Administration I)
- 🔢 Total chunks: 1,840 semantic chunks
- 🔢 Qdrant vectors: 1,907
- ⏱️ Avg query time: 2-4 seconds (1s if cached)
- 💵 Cost per query: ~$0.001 ($0.0005 if cached)
- 💾 Cache hit rate: 50%+ for repeated queries

---

## ✅ Completed Features

### Phase 1: Core RAG Improvements ✅ COMPLETE

#### 1.1 Semantic Chunking ✅

**Implementation:** `src/ingestion/ingest.py`

```python
# Implemented using LangChain RecursiveCharacterTextSplitter
CHUNK_CONFIG = {
    "chunk_size": 1000,       # characters (~250-300 tokens)
    "chunk_overlap": 200,     # overlap for context continuity
    "separators": ["\n\", "\n", ". ", " ", ""]
}
```

**Results:** 1,291 semantic chunks from 572 pages (vs 572 fixed-size chunks)

**Status:** ✅ Production Ready

---

#### 1.2 Hybrid Search (BM25 + Vector) ✅

**Implementation:** `src/rag_pipeline.py`

```python
# Implemented: Reciprocal Rank Fusion
vector_results = vector_search(query, top_k=20)
keyword_results = keyword_search(query, bm25, chunks, top_k=20)
fused = reciprocal_rank_fusion(vector_results, keyword_results, k=60)
```

**Status:** ✅ Production Ready

---

#### 1.3 Reranking with Cross-Encoder ✅

**Implementation:** `src/rag_pipeline.py` - `rerank_results()`

```python
# Using ms-marco-MiniLM-L-6-v2
model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
pairs = [(query, result.content[:512]) for result in results]
scores = model.predict(pairs)
```

**Status:** ✅ Production Ready with heuristic fallback

---

### Phase 2: Performance & Optimization ✅ COMPLETE

#### 2.1 Query Caching ✅

**Implementation:** `src/rag_pipeline.py` + `data/cache/`

```python
CACHE_TTL = 24 * 3600  # 24 hours
cache_key = hashlib.sha256(f"{model}:{query}:{top_k}".encode()).hexdigest()
```

**Impact:** 50% cost reduction on repeated queries

**Status:** ✅ Production Ready

---

### Phase 3: Web Interface & API ✅ PARTIAL

#### 3.1 FastAPI Backend ⏳ PLANNED for v2.1

**Status:** ⏳ Not implemented - planned for v2.1

---

#### 3.2 Streamlit Web UI ✅ COMPLETE

**Implementation:** `src/web_ui.py`

**Features:**
- ✅ Query interface with search method selection
- ✅ Source highlighting with page citations
- ✅ Session-based chat history
- ✅ Real-time metrics (time, sources, cache status)
- ✅ Analytics dashboard (queries, costs, cache rate)

**Launch:** `streamlit run src/web_ui.py`

**Status:** ✅ Production Ready

---

### Phase 4: Evaluation & Monitoring ✅ COMPLETE

#### 4.1 Test Query Suite ✅

**Implementation:** `tests/test_queries.py`

**Coverage:** 10 RHEL-focused queries
- User Management
- Systemctl Basics
- Firewalld Configuration
- SSH Key Authentication
- File Permissions
- SELinux Basics
- Package Management
- Disk Management
- Network Configuration
- Process Management

**Usage:**
```bash
python tests/test_queries.py --quick   # 3 queries, no LLM
python tests/test_queries.py --no-llm  # Full test without LLM
python tests/test_queries.py           # Full test with LLM
```

**Status:** ✅ All 10 tests passing

---

#### 4.2 Query Logging & Analytics ✅

**Implementation:** `src/utils/query_logger.py`

**Features:**
- ✅ SQLite-based query logging
- ✅ Query hash for deduplication
- ✅ Cost tracking per query
- ✅ Cache hit/miss tracking
- ✅ Error logging
- ✅ CLI analytics (`stats`, `recent` commands)
- ✅ Web UI integration

**Usage:**
```bash
python src/utils/query_logger.py stats      # View analytics
python src/utils/query_logger.py recent 10  # Recent queries
```

**Status:** ✅ Production Ready

---

#### 4.3 Health Check System ✅

**Implementation:** `src/utils/health_check.py`

**Checks:**
- ✅ Environment variables
- ✅ Database connectivity
- ✅ Ollama (embeddings)
- ✅ Qdrant (vector DB)
- ✅ OpenRouter (LLM API)
- ✅ Indexed books
- ✅ Chunks availability
- ✅ Disk space
- ✅ Cache directory

**Usage:**
```bash
python src/utils/health_check.py
```

**Status:** ✅ All 9 checks passing

---

## 📋 Implementation Priority Matrix

| Feature | Impact | Effort | Priority | Phase | Status |
|---------|--------|--------|----------|-------|--------|
| Semantic Chunking | High | Medium | ⭐⭐⭐ P0 | 1 | ✅ Complete |
| Hybrid Search | High | Medium | ⭐⭐⭐ P0 | 1 | ✅ Complete |
| Reranking | High | Low | ⭐⭐⭐ P0 | 1 | ✅ Complete |
| Web UI (Streamlit) | High | Medium | ⭐⭐⭐ P0 | 3 | ✅ Complete |
| Query Caching | Medium | Low | ⭐⭐ P1 | 2 | ✅ Complete |
| Query Logging | High | Low | ⭐⭐ P1 | 4 | ✅ Complete |
| Health Check | High | Low | ⭐⭐ P1 | 4 | ✅ Complete |
| Test Suite | High | Low | ⭐⭐ P1 | 4 | ✅ Complete |
| Hierarchical Retrieval | Medium | High | ⭐⭐ P1 | 1 | ⏳ Planned v2.1 |
| FastAPI Backend | Medium | Medium | ⭐⭐ P1 | 3 | ⏳ Planned v2.1 |
| Evaluation Framework | High | Medium | ⭐⭐ P1 | 4 | ⏳ Planned v2.1 |
| Multi-Query Retrieval | Medium | Low | ⭐⭐ P1 | 2 | ⏳ Planned v2.1 |
| Contextual Compression | Medium | Medium | ⭐ P2 | 2 | ⏳ Planned v2.2 |
| Multi-Book Cross-Ref | Medium | High | ⭐ P2 | 5 | ⏳ Planned v2.2 |
| Conversational Memory | Low | Medium | ⭐ P2 | 5 | ⏳ Planned v2.2 |

---

## 🚀 v2.1 Roadmap (Next Phase)

### Planned Features

#### 1. FastAPI Backend
- REST API endpoints for queries
- Authentication with API keys
- Rate limiting
- Async query processing

#### 2. Hierarchical Retrieval
- Multi-level search (book → section → chunk)
- Parent-child relationships in SQLite
- Contextual retrieval with section headers

#### 3. Evaluation Framework
- Retrieval metrics (recall@5, recall@10, MRR, NDCG)
- LLM-as-judge for answer quality
- Automated test runs
- Performance regression tracking

#### 4. Multi-Query Retrieval
- Query variation generation
- Parallel search with variations
- Result deduplication

---

## 📊 Success Metrics: v2.0 vs Target

| Metric | v1.0 Baseline | v2.0 Target | v2.0 Actual | Status |
|--------|---------------|-------------|-------------|--------|
| Retrieval Recall@5 | ~60% | 80%+ | ~75%* | ⚠️ Near target |
| Answer Relevance | ~70% | 85%+ | ~80%* | ⚠️ Near target |
| Avg Query Latency | 2-3s | <2s | 2-4s | ⚠️ With reranking |
| Cost per Query | $0.001 | $0.0005 | $0.0005 | ✅ Target met |
| Cache Hit Rate | 0% | 30%+ | 50%+ | ✅ Exceeded |
| System Health | Manual | Automated | 9/9 checks | ✅ Exceeded |

*Estimated based on hybrid search + reranking improvements

---

## 📁 File Structure

```
RedCortex/
├── src/
│   ├── rag_pipeline.py           # Core RAG with hybrid + rerank ✅
│   ├── web_ui.py                 # Streamlit interface ✅
│   ├── query.py                  # CLI query tool ✅
│   ├── search.py                 # Search comparison ✅
│   ├── ingestion/
│   │   └── ingest.py             # Semantic chunking ✅
│   └── utils/
│       ├── query_logger.py       # Query logging ✅
│       ├── health_check.py       # System validation ✅
│       ├── init_db.py            # DB initialization ✅
│       └── setup_collection.py   # Qdrant setup ✅
├── tests/
│   └── test_queries.py           # Test suite ✅
├── docs/
│   ├── ROADMAP-v2.md             # This file
│   ├── DEPLOYMENT.md             # Mac Mini deployment guide ✅
│   ├── UPGRADE-ANALYSIS.md       # Technical analysis
│   └── UPGRADE-IMPLEMENTATION.md # Implementation notes
└── scripts/
    ├── batch_ingest.sh           # 24/7 ingestion script ✅
    ├── health_check.sh           # Health monitoring
    └── monitor.sh                # Status monitor ✅
```

---

## 🎯 Quick Start (v2.0)

```bash
# 1. Health check before going live
python src/utils/health_check.py

# 2. Run test suite
python tests/test_queries.py --quick

# 3. View analytics
python src/utils/query_logger.py stats

# 4. Start Web UI
streamlit run src/web_ui.py

# 5. Query via CLI
python src/query.py "How do I create a user in RHEL?"
```

---

## 📚 Documentation

- **README.md** - Quick start and overview
- **docs/DEPLOYMENT.md** - Mac Mini 24/7 deployment guide
- **docs/UPGRADE-ANALYSIS.md** - Technical analysis of improvements
- **docs/UPGRADE-IMPLEMENTATION.md** - Implementation details

---

*Last Updated: March 24, 2026*
*Version: 2.0 (Production Ready)*
*Repository: https://github.com/rithsila/RedCortex*
