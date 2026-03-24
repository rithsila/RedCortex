# RedCortex v2.0 - Next Version Roadmap

> Comprehensive upgrade plan based on RAG best practices and LLM application patterns

## Executive Summary

**Current State (v1.0):**
- ✅ Basic RAG working (semantic search + LLM)
- ✅ Resume-capable ingestion
- ✅ 1 book indexed, 7 processing
- ⚠️ Fixed-size chunking (not optimal)
- ⚠️ Simple retrieval (no reranking)
- ⚠️ No caching or optimization
- ⚠️ CLI only (no web interface)

**Target State (v2.0):**
- 🎯 Production-grade RAG with hybrid search
- 🎯 Semantic chunking with hierarchy
- 🎯 Query caching & optimization
- 🎯 Web UI + API server
- 🎯 Evaluation framework
- 🎯 Multi-book cross-referencing

---

## Phase 1: Core RAG Improvements (Week 1-2)

### 1.1 Semantic Chunking ⭐ HIGH PRIORITY

**Current:** Fixed-size chunks (1 page = 1 chunk)
**Problem:** Breaks context at arbitrary boundaries
**Solution:** Document-aware semantic chunking

```python
# New: Semantic chunking
class SemanticChunker:
    def chunk_document(self, pdf_path):
        # 1. Extract document structure
        sections = self.extract_structure(pdf_path)
        
        # 2. Chunk by semantic boundaries
        for section in sections:
            # Split on headers, paragraphs, not just size
            chunks = self.split_semantically(section)
            
            # 3. Add overlap for context continuity
            chunks_with_overlap = self.add_overlap(chunks)
            
            # 4. Preserve hierarchy metadata
            yield {
                "content": chunk,
                "section": section.title,
                "level": section.level,
                "page": chunk.page,
                "parent_section": section.parent
            }
```

**Implementation:**
- [ ] Use `langchain.text_splitter.RecursiveCharacterTextSplitter`
- [ ] Respect document structure (headers, lists, code blocks)
- [ ] Add configurable overlap (200-500 chars)
- [ ] Store hierarchy metadata in Qdrant

**Impact:** +20-30% retrieval accuracy

---

### 1.2 Hybrid Search (Semantic + Keyword) ⭐ HIGH PRIORITY

**Current:** Pure vector similarity search
**Problem:** Misses exact keyword matches (e.g., "CVE-2023-1234", "systemctl")
**Solution:** Combine BM25 + Vector search with Reciprocal Rank Fusion

```python
# New: Hybrid search
class HybridRetriever:
    def __init__(self):
        self.vector_store = QdrantClient(...)
        self.keyword_index = self.build_bm25_index()
    
    def search(self, query: str, top_k=10):
        # 1. Semantic search
        vector_results = self.vector_store.search(query, top_k=20)
        
        # 2. Keyword search (BM25)
        keyword_results = self.keyword_index.search(query, top_k=20)
        
        # 3. Reciprocal Rank Fusion
        combined = self.reciprocal_rank_fusion(
            vector_results, keyword_results, 
            alpha=0.7  # Weight: 70% semantic, 30% keyword
        )
        
        return combined[:top_k]
```

**Implementation:**
- [ ] Add SQLite FTS5 or Whoosh for BM25
- [ ] Implement RRF scoring
- [ ] Add query type detection (semantic vs keyword-heavy)
- [ ] Configurable weights per category

**Impact:** +25% recall for technical terms

---

### 1.3 Hierarchical Retrieval ⭐ HIGH PRIORITY

**Current:** Flat retrieval (all chunks equal)
**Problem:** No context about document structure
**Solution:** Multi-level retrieval (book → section → chunk)

```python
# New: Hierarchical retrieval
class HierarchicalRetriever:
    def retrieve(self, query: str):
        # Level 1: Find relevant books
        book_candidates = self.search_books(query, top_k=3)
        
        # Level 2: Find relevant sections within books
        section_candidates = []
        for book in book_candidates:
            sections = self.search_sections(query, book_id=book.id, top_k=5)
            section_candidates.extend(sections)
        
        # Level 3: Find specific chunks within sections
        chunk_candidates = []
        for section in section_candidates:
            chunks = self.search_chunks(query, section_id=section.id, top_k=10)
            chunk_candidates.extend(chunks)
        
        # Rerank with context
        return self.rerank_with_hierarchy(chunk_candidates)
```

**Implementation:**
- [ ] Add parent-child relationships in SQLite
- [ ] Three-tier search (books, sections, chunks)
- [ ] Contextual retrieval (get parent section for each chunk)

**Impact:** +15% precision, better context

---

### 1.4 Reranking with Cross-Encoder ⭐ HIGH PRIORITY

**Current:** First-stage retrieval results used directly
**Problem:** Vector similarity ≠ relevance to query
**Solution:** Add reranking step with cross-encoder

```python
# New: Two-stage retrieval with reranking
class RerankingRetriever:
    def __init__(self):
        self.vector_retriever = VectorRetriever()
        self.cross_encoder = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    
    def search(self, query: str, top_k=5):
        # Stage 1: Retrieve candidates (vector search)
        candidates = self.vector_retriever.search(query, top_k=50)
        
        # Stage 2: Rerank with cross-encoder
        pairs = [(query, doc.content) for doc in candidates]
        scores = self.cross_encoder.predict(pairs)
        
        # Sort by rerank score
        reranked = sorted(
            zip(candidates, scores),
            key=lambda x: x[1],
            reverse=True
        )
        
        return reranked[:top_k]
```

**Implementation:**
- [ ] Add sentence-transformers dependency
- [ ] Use lightweight cross-encoder (MiniLM)
- [ ] Cache reranker results
- [ ] Optional: Fine-tune on book-specific data

**Impact:** +30% precision at top-5

---

## Phase 2: Performance & Optimization (Week 3-4)

### 2.1 Query Caching ⭐ MEDIUM PRIORITY

**Current:** Every query hits LLM API ($0.001/query)
**Problem:** Repeated questions cost money
**Solution:** Cache frequent queries

```python
# New: Query caching
class CachedRAG:
    def __init__(self):
        self.cache = RedisCache()  # or SQLite for simplicity
        self.cache_ttl = 3600 * 24  # 24 hours
    
    def query(self, question: str):
        # Check cache
        cache_key = self.hash_query(question)
        cached = self.cache.get(cache_key)
        if cached:
            return cached
        
        # Generate response
        response = self.rag_pipeline(question)
        
        # Cache if temperature=0 (deterministic)
        if self.llm.temperature == 0:
            self.cache.set(cache_key, response, ttl=self.cache_ttl)
        
        return response
    
    def hash_query(self, query: str) -> str:
        """Normalize and hash query for caching"""
        normalized = query.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()
```

**Implementation:**
- [ ] Add Redis or SQLite caching layer
- [ ] Cache both retrieval results and LLM responses
- [ ] Implement query normalization
- [ ] Cache invalidation on new book ingestion

**Impact:** -50% API costs for repeated queries

---

### 2.2 Multi-Query Retrieval

**Current:** Single query embedding
**Problem:** Query might not match document phrasing
**Solution:** Generate query variations for better recall

```python
# New: Multi-query retrieval
class MultiQueryRetriever:
    def generate_variations(self, query: str, n=3) -> list[str]:
        """Generate semantic variations of the query"""
        prompt = f"""Generate {n} different ways to ask this question:
        Original: {query}
        
        Variations:"""
        
        variations = self.llm.generate(prompt).split('\n')
        return [query] + variations  # Include original
    
    def search(self, query: str):
        # Generate variations
        queries = self.generate_variations(query, n=3)
        
        # Search with each variation
        all_results = []
        for q in queries:
            results = self.vector_store.search(q, top_k=10)
            all_results.extend(results)
        
        # Deduplicate and rerank
        return self.deduplicate_and_rerank(all_results)
```

**Impact:** +20% recall for ambiguous queries

---

### 2.3 Contextual Compression

**Current:** Full page content in context
**Problem:** LLM sees irrelevant parts, wastes tokens
**Solution:** Compress to relevant parts only

```python
# New: Contextual compression
class ContextualCompressor:
    def compress(self, query: str, documents: list) -> list[str]:
        """Extract only relevant parts of documents"""
        compressed = []
        
        for doc in documents:
            # Use smaller LLM to extract relevant sentences
            prompt = f"""Extract sentences from the following text that are relevant to: {query}
            
            Text:
            {doc.content}
            
            Relevant sentences only:"""
            
            relevant = self.extractor_llm.generate(prompt)
            compressed.append(relevant)
        
        return compressed
```

**Impact:** -30% token usage, +15% relevance

---

## Phase 3: Web Interface & API (Week 5-6)

### 3.1 FastAPI Backend ⭐ HIGH PRIORITY

```python
# New: API server
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RedCortex API")

class QueryRequest(BaseModel):
    question: str
    category: str | None = None
    top_k: int = 5

class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]
    confidence: float
    tokens_used: int

@app.post("/query", response_model=QueryResponse)
async def query(request: QueryRequest):
    """Main RAG query endpoint"""
    result = rag_pipeline.query(
        question=request.question,
        category=request.category,
        top_k=request.top_k
    )
    return result

@app.get("/books")
async def list_books():
    """List all indexed books"""
    return db.get_books()

@app.get("/stats")
async def get_stats():
    """System statistics"""
    return {
        "books": db.count_books(),
        "chunks": db.count_chunks(),
        "queries_today": db.count_queries_today(),
        "avg_latency": metrics.get_avg_latency()
    }
```

**Implementation:**
- [ ] Create `src/api/` module
- [ ] Add FastAPI + uvicorn dependencies
- [ ] Implement query endpoint
- [ ] Add authentication (API keys)
- [ ] Rate limiting

---

### 3.2 Streamlit Web UI ⭐ HIGH PRIORITY

```python
# New: Web interface
import streamlit as st

st.title("📚 RedCortex - Technical Library RAG")

# Query input
query = st.text_input("Ask a question:", placeholder="How do I configure firewalld?")

if query:
    with st.spinner("Searching..."):
        response = api.query(query)
    
    # Display answer
    st.markdown("### Answer")
    st.markdown(response.answer)
    
    # Display sources
    st.markdown("### Sources")
    for source in response.sources:
        with st.expander(f"📄 {source.title} (Page {source.page})"):
            st.markdown(source.content[:500] + "...")
    
    # Feedback buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("👍 Helpful"):
            api.submit_feedback(query, response, rating=1)
    with col2:
        if st.button("👎 Not Helpful"):
            api.submit_feedback(query, response, rating=-1)

# Sidebar stats
st.sidebar.markdown("### System Stats")
st.sidebar.metric("Books Indexed", db.count_books())
st.sidebar.metric("Total Chunks", db.count_chunks())
st.sidebar.metric("Queries Today", db.count_queries_today())
```

**Implementation:**
- [ ] Create `src/web/` module
- [ ] Add streamlit dependency
- [ ] Build chat interface
- [ ] Add source highlighting
- [ ] Implement feedback collection

---

## Phase 4: Evaluation & Monitoring (Week 7-8)

### 4.1 Retrieval Evaluation Framework

```python
# New: Evaluation framework
class RAGEvaluator:
    def __init__(self):
        self.test_cases = self.load_test_cases()
    
    def evaluate_retrieval(self) -> dict:
        """Evaluate retrieval quality"""
        metrics = {
            "recall@5": [],
            "recall@10": [],
            "mrr": [],  # Mean Reciprocal Rank
            "ndcg": []  # Normalized Discounted Cumulative Gain
        }
        
        for test_case in self.test_cases:
            results = retriever.search(test_case.query, top_k=10)
            
            # Check if relevant docs are retrieved
            relevant_ids = set(test_case.relevant_chunk_ids)
            retrieved_ids = [r.id for r in results]
            
            # Calculate metrics
            metrics["recall@5"].append(
                len(relevant_ids & set(retrieved_ids[:5])) / len(relevant_ids)
            )
            metrics["recall@10"].append(
                len(relevant_ids & set(retrieved_ids[:10])) / len(relevant_ids)
            )
            
            # MRR
            for i, rid in enumerate(retrieved_ids):
                if rid in relevant_ids:
                    metrics["mrr"].append(1 / (i + 1))
                    break
            else:
                metrics["mrr"].append(0)
        
        return {k: sum(v) / len(v) for k, v in metrics.items()}
    
    def evaluate_generation(self) -> dict:
        """Evaluate answer quality using LLM-as-judge"""
        # Use GPT-4 to evaluate answer quality
        pass
```

**Implementation:**
- [ ] Create test set of 50+ questions
- [ ] Add evaluation metrics
- [ ] Automate evaluation runs
- [ ] Track metrics over time

---

### 4.2 Query Logging & Analytics

```python
# New: Query logging
class QueryLogger:
    def log_query(self, query: str, response: dict, metadata: dict):
        """Log query for analytics"""
        log_entry = {
            "timestamp": datetime.now(),
            "query": query,
            "query_hash": hashlib.md5(query.encode()).hexdigest(),
            "response": response,
            "latency_ms": metadata["latency"],
            "tokens_used": metadata["tokens"],
            "cost_usd": metadata["cost"],
            "model": metadata["model"],
            "sources": [s.id for s in response.sources],
            "user_feedback": None  # To be filled later
        }
        
        db.insert_query_log(log_entry)
    
    def get_analytics(self, days=7) -> dict:
        """Get query analytics"""
        return {
            "total_queries": db.count_queries(days=days),
            "unique_queries": db.count_unique_queries(days=days),
            "avg_latency": db.avg_latency(days=days),
            "total_cost": db.total_cost(days=days),
            "top_queries": db.top_queries(days=days, n=10),
            "failed_queries": db.count_failed_queries(days=days)
        }
```

---

## Phase 5: Advanced Features (Week 9-10)

### 5.1 Multi-Book Cross-Referencing

```python
# New: Cross-book search
class CrossBookRetriever:
    def search_across_books(self, query: str) -> dict:
        """Search across all books and synthesize answer"""
        
        # Get results from each book
        book_results = {}
        for book in db.get_all_books():
            results = retriever.search(query, book_id=book.id, top_k=3)
            if results:
                book_results[book.title] = results
        
        # Synthesize cross-book answer
        synthesis_prompt = f"""Synthesize information from multiple sources:
        
        Query: {query}
        
        Sources:
        {self.format_book_results(book_results)}
        
        Provide a comprehensive answer that integrates information from all relevant books.
        Cite which book each piece of information comes from.
        """
        
        answer = self.llm.generate(synthesis_prompt)
        
        return {
            "answer": answer,
            "sources_by_book": book_results
        }
```

---

### 5.2 Conversational Memory

```python
# New: Conversational RAG with memory
from langchain.memory import ConversationBufferMemory

class ConversationalRAG:
    def __init__(self):
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    
    def chat(self, message: str) -> str:
        # Get conversation context
        chat_history = self.memory.load_memory_variables({})["chat_history"]
        
        # Reformulate query with context
        contextualized_query = self.reformulate_query(message, chat_history)
        
        # Retrieve with contextualized query
        docs = retriever.search(contextualized_query)
        
        # Generate response
        response = self.generate_response(
            query=message,
            context=docs,
            chat_history=chat_history
        )
        
        # Save to memory
        self.memory.save_context(
            {"input": message},
            {"output": response}
        )
        
        return response
```

---

## Implementation Priority Matrix

| Feature | Impact | Effort | Priority | Phase |
|---------|--------|--------|----------|-------|
| Semantic Chunking | High | Medium | ⭐⭐⭐ P0 | 1 |
| Hybrid Search | High | Medium | ⭐⭐⭐ P0 | 1 |
| Reranking | High | Low | ⭐⭐⭐ P0 | 1 |
| Web UI (Streamlit) | High | Medium | ⭐⭐⭐ P0 | 3 |
| Query Caching | Medium | Low | ⭐⭐ P1 | 2 |
| Evaluation Framework | High | Medium | ⭐⭐ P1 | 4 |
| FastAPI Backend | Medium | Medium | ⭐⭐ P1 | 3 |
| Multi-Query Retrieval | Medium | Low | ⭐⭐ P1 | 2 |
| Hierarchical Retrieval | Medium | High | ⭐⭐ P1 | 1 |
| Contextual Compression | Medium | Medium | ⭐ P2 | 2 |
| Multi-Book Cross-Ref | Medium | High | ⭐ P2 | 5 |
| Conversational Memory | Low | Medium | ⭐ P2 | 5 |

---

## Technology Stack Additions

### New Dependencies

```txt
# Core improvements
sentence-transformers>=2.3.0  # Cross-encoder reranking
rank-bm25>=0.2.2              # BM25 keyword search

# API & Web
fastapi>=0.109.0
uvicorn>=0.27.0
streamlit>=1.30.0
pydantic>=2.5.0

# Caching
redis>=5.0.0  # Optional

# Monitoring
prometheus-client>=0.19.0
```

---

## Success Metrics for v2.0

| Metric | v1.0 Baseline | v2.0 Target |
|--------|---------------|-------------|
| Retrieval Recall@5 | ~60% | 80%+ |
| Answer Relevance | ~70% | 85%+ |
| Avg Query Latency | 2-3s | <2s |
| Cost per Query | $0.001 | $0.0005 (-50%) |
| User Satisfaction | N/A | 4.0/5.0+ |
| Cache Hit Rate | 0% | 30%+ |

---

## Timeline Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1 | Weeks 1-2 | Semantic chunking, hybrid search, reranking |
| Phase 2 | Weeks 3-4 | Caching, multi-query, compression |
| Phase 3 | Weeks 5-6 | FastAPI backend, Streamlit UI |
| Phase 4 | Weeks 7-8 | Evaluation framework, analytics |
| Phase 5 | Weeks 9-10 | Cross-referencing, conversational |

**Total: 10 weeks to v2.0**

---

## Quick Wins (Do First)

1. **Reranking** - Add cross-encoder (1 day, +30% precision)
2. **Caching** - Simple SQLite cache (1 day, -50% costs)
3. **Web UI** - Streamlit prototype (2 days, user-friendly)
4. **Semantic Chunking** - Better text splitting (2 days, +20% accuracy)

**These 4 features = 80% of v2.0 value in 20% of the time**

---

*Generated using RAG Engineer, Vector Database Engineer, and LLM App Patterns skills*
