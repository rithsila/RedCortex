# RedCortex v2.2 Implementation Plan

> Step-by-step implementation prompts for building the next version of RedCortex

**Version**: 2.2  
**Target Date**: 4 weeks  
**Last Updated**: 2026-03-27

---

## Overview

This document provides self-contained implementation prompts for upgrading RedCortex from v2.1 to v2.2. Each prompt is designed to be implemented independently without conflicts with existing code.

### v2.2 Feature Summary

| Feature | Priority | Effort | Impact |
|---------|----------|--------|--------|
| Scale - Complete Library Ingestion | P0 | 3 days | ⭐⭐⭐⭐⭐ |
| Category-Based Search | P0 | 2 days | ⭐⭐⭐⭐ |
| Conversational Memory | P1 | 4 days | ⭐⭐⭐⭐⭐ |
| Contextual Compression | P1 | 3 days | ⭐⭐⭐⭐ |
| Multi-Book Cross-Reference | P2 | 4 days | ⭐⭐⭐⭐ |
| Production API Hardening | P2 | 3 days | ⭐⭐⭐⭐ |

---

## Phase 1: Scale - Complete Library Ingestion

### SCALE-01: Create Batch Ingestion Configuration System

**Task ID**: SCALE-01  
**Objective**: Create a configuration system to manage batch ingestion of multiple books with metadata

**Requirements**:
- Create `config/books.yaml` to define all books to be ingested
- Each book entry must have: title, file_path, category, priority, status
- Support categories: red_hat, ai_engineering, security, other
- Include book metadata: author, description, tags
- Create a loader utility to read and validate the configuration

**Dependencies**: None (uses existing ingestion pipeline)

**Deliverables**:
- `config/books.yaml` - Configuration file with all 18 books
- `src/utils/book_config.py` - Loader and validator
- `src/utils/book_config.py` CLI with commands: `list`, `validate`, `status`

**Acceptance Criteria**:
- [ ] `config/books.yaml` contains all 18 books with complete metadata
- [ ] `python src/utils/book_config.py list` shows all books with status
- [ ] `python src/utils/book_config.py validate` confirms all file paths exist
- [ ] Invalid configurations raise clear error messages
- [ ] Unit tests pass for config loader

**Testing**:
```bash
python src/utils/book_config.py validate
python src/utils/book_config.py list
```

---

### SCALE-02: Implement Batch Ingestion Runner

**Task ID**: SCALE-02  
**Objective**: Create a batch runner that processes multiple books sequentially with resume capability

**Requirements**:
- Create `src/ingestion/batch_runner.py` that reads from book configuration
- Process books in priority order (high → medium → low)
- Track ingestion status in database (pending, in_progress, completed, failed)
- Resume from last failed book on restart
- Generate detailed logs per book
- Support dry-run mode to preview what will be ingested
- Add progress reporting (book X of Y, estimated time remaining)

**Dependencies**: SCALE-01

**Deliverables**:
- `src/ingestion/batch_runner.py` - Main batch runner script
- Database migration to add `ingestion_jobs` table
- Progress tracking and ETA calculation
- Updated `scripts/batch_ingest.sh` to use new runner

**Acceptance Criteria**:
- [ ] Batch runner processes books in priority order
- [ ] Failed books are tracked and can be resumed
- [ ] Progress shows: current book, pages processed, ETA
- [ ] Dry-run mode lists books without ingesting
- [ ] Each book has its own log file in `logs/ingest/`
- [ ] Can stop and resume without losing progress

**Testing**:
```bash
# Dry run
python src/ingestion/batch_runner.py --dry-run

# Actual ingestion
python src/ingestion/batch_runner.py

# Resume failed
python src/ingestion/batch_runner.py --resume
```

---

### SCALE-03: Add Category Support to Database Schema

**Task ID**: SCALE-03  
**Objective**: Extend database schema to support book categories and enable category-based filtering

**Requirements**:
- Add `categories` table with: id, name, description, icon
- Add `book_categories` junction table for many-to-many relationship
- Add `chunks.category_id` column for fast filtering
- Create database migration script (backward compatible)
- Add category statistics view
- Update existing chunks with category from their book

**Dependencies**: None (database migration)

**Deliverables**:
- `src/utils/migrations/add_categories.py` - Migration script
- `src/utils/category_manager.py` - Category CRUD operations
- Updated `src/utils/init_db.py` with new schema
- Database views for category statistics

**Acceptance Criteria**:
- [ ] Migration runs without data loss
- [ ] Existing chunks get proper category assignment
- [ ] `category_manager.py list` shows all categories with book counts
- [ ] Can query chunks by category efficiently
- [ ] Rollback script works if needed

**Testing**:
```bash
# Run migration
python src/utils/migrations/add_categories.py

# Verify
python src/utils/category_manager.py list
python src/utils/category_manager.py stats
```

---

### SCALE-04: Implement Category-Aware Ingestion

**Task ID**: SCALE-04  
**Objective**: Update ingestion pipeline to tag chunks with categories and optimize per-category settings

**Requirements**:
- Update `src/ingestion/ingest.py` to accept category parameter
- Store category_id in chunk metadata
- Apply category-specific chunking strategies:
  - red_hat: 1000 char chunks, 200 overlap
  - ai_engineering: 800 char chunks, 150 overlap
  - security: 600 char chunks, preserve code blocks
- Add category to Qdrant payload
- Update ingestion logging to include category

**Dependencies**: SCALE-03

**Deliverables**:
- Updated `src/ingestion/ingest.py` with category support
- `CHUNK_CONFIGS` dictionary per category
- Updated Qdrant payload with category field
- Tests for category-aware chunking

**Acceptance Criteria**:
- [ ] Ingestion accepts `--category` parameter
- [ ] Chunks are tagged with correct category_id
- [ ] Different categories use different chunk sizes
- [ ] Qdrant points include category in payload
- [ ] Can filter by category in search (preparation for SEARCH-01)

**Testing**:
```bash
# Ingest with category
python src/ingestion/ingest.py "path/to/book.pdf" "Title" red_hat

# Verify in database
sqlite3 data/library.db "SELECT c.category, COUNT(*) FROM chunks ch JOIN books b ON ch.book_id = b.id JOIN categories c ON b.category_id = c.id GROUP BY c.category"
```

---

## Phase 2: Category-Based Search

### SEARCH-01: Implement Category Filtering in RAG Pipeline

**Task ID**: SEARCH-01  
**Objective**: Extend hybrid_search to support filtering by category

**Requirements**:
- Add `category_filter` parameter to `hybrid_search()` function
- Support single category or list of categories
- Implement in `vector_search()` using Qdrant filter
- Implement in `keyword_search()` using SQL WHERE clause
- Update `reciprocal_rank_fusion()` to respect filters
- Maintain backward compatibility (no filter = search all)

**Dependencies**: SCALE-03, SCALE-04

**Deliverables**:
- Updated `src/rag_pipeline.py` with category filtering
- Qdrant filter construction for categories
- SQL filter for BM25 search
- Updated `SearchResult` to include category

**Acceptance Criteria**:
- [ ] `hybrid_search(query, category_filter="red_hat")` works
- [ ] Multiple categories: `category_filter=["red_hat", "security"]`
- [ ] Empty filter searches all categories
- [ ] Filter works with both vector and BM25 search
- [ ] No performance degradation when filtering

**Testing**:
```python
# Test in Python
from src.rag_pipeline import hybrid_search

# Single category
results, method = hybrid_search("user management", category_filter="red_hat")

# Multiple categories
results, method = hybrid_search("security", category_filter=["red_hat", "security"])
```

---

### SEARCH-02: Add Category Filter to API Endpoints

**Task ID**: SEARCH-02  
**Objective**: Expose category filtering through FastAPI endpoints

**Requirements**:
- Update `QueryRequest` model to include optional `categories` field
- Validate category names against database
- Return category information in `Source` model
- Update `/books` endpoint to support category filtering
- Add `/categories` endpoint to list available categories
- Document new parameters in OpenAPI schema

**Dependencies**: SEARCH-01

**Deliverables**:
- Updated `src/api/main.py` with category endpoints
- New `/categories` GET endpoint
- Updated Pydantic models
- API documentation updates

**Acceptance Criteria**:
- [ ] POST `/query` accepts `categories` array parameter
- [ ] GET `/categories` returns all categories
- [ ] GET `/books?category=red_hat` filters books
- [ ] Invalid category names return 400 error
- [ ] Sources include category in response

**Testing**:
```bash
# List categories
curl http://localhost:8000/categories

# Query with category filter
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How to create user?", "categories": ["red_hat"]}'

# Filter books by category
curl http://localhost:8000/books?category=ai_engineering
```

---

### SEARCH-03: Add Category Filter to Web UI

**Task ID**: SEARCH-03  
**Objective**: Add category selection to Streamlit web interface

**Requirements**:
- Add category multi-select in sidebar
- Show category icons/colors for visual distinction
- Display category badge on each source
- Add category filter to search results display
- Update analytics to show queries per category
- Remember user's category preferences in session

**Dependencies**: SEARCH-02

**Deliverables**:
- Updated `src/web_ui.py` with category UI
- Category color/icon mapping
- Updated source display with category badges
- Category analytics section

**Acceptance Criteria**:
- [ ] Sidebar shows category multi-select dropdown
- [ ] Selected categories persist during session
- [ ] Each source shows its category badge
- [ ] Analytics shows "Queries by Category" chart
- [ ] Category filter applies to all searches

**Testing**:
```bash
streamlit run src/web_ui.py
# Verify category filter appears and works
```

---

## Phase 3: Conversational Memory

### CHAT-01: Design and Implement Session Schema

**Task ID**: CHAT-01  
**Objective**: Create database schema for storing conversation sessions and messages

**Requirements**:
- Create `chat_sessions` table: id, user_id, title, created_at, updated_at, context_window
- Create `chat_messages` table: id, session_id, role (user/assistant/system), content, tokens, timestamp
- Create `chat_context` table: session_id, current_summary, key_facts, referenced_pages
- Add indexes for fast session lookup and message retrieval
- Support SQLite JSON fields for flexible metadata
- Create session management utilities

**Dependencies**: None (new tables)

**Deliverables**:
- `src/utils/migrations/add_chat_tables.py` - Migration
- Updated `src/utils/init_db.py` with new schema
- `src/chat/session_manager.py` - Session CRUD operations
- `src/chat/models.py` - Pydantic models for chat entities

**Acceptance Criteria**:
- [ ] Migration creates all tables without errors
- [ ] Can create, read, update, delete sessions
- [ ] Messages are properly linked to sessions
- [ ] Can retrieve full conversation history
- [ ] Session listing supports pagination
- [ ] Soft delete for sessions (archive, don't delete)

**Testing**:
```python
from src.chat.session_manager import SessionManager

manager = SessionManager()
session_id = manager.create_session("RHEL Configuration Help")
manager.add_message(session_id, "user", "How do I create a user?")
manager.add_message(session_id, "assistant", "Use useradd command...")
history = manager.get_history(session_id)
assert len(history) == 2
```

---

### CHAT-02: Implement Context Window Management

**Task ID**: CHAT-02  
**Objective**: Build system to manage conversation context window for LLM prompts

**Requirements**:
- Create `src/chat/context_manager.py`
- Implement sliding window: keep last N messages (default: 5 exchanges)
- Summarize older messages when window slides
- Track token count to stay within limits
- Extract key facts from conversation for persistent context
- Support context compression (remove redundant information)
- Return formatted context string for LLM prompt

**Dependencies**: CHAT-01

**Deliverables**:
- `src/chat/context_manager.py` - Context window management
- Message summarization using LLM
- Token counting and budget management
- Key facts extraction

**Acceptance Criteria**:
- [ ] Context window keeps configurable N recent messages
- [ ] Older messages are summarized, not lost
- [ ] Token count stays within limit (default: 2000 tokens)
- [ ] Key facts are extracted and persisted
- [ ] Context is formatted for LLM system prompt

**Testing**:
```python
from src.chat.context_manager import ContextManager

ctx = ContextManager(max_messages=5, max_tokens=2000)
for i in range(10):
    ctx.add_message("user", f"Question {i}")
    ctx.add_message("assistant", f"Answer {i}")

context = ctx.get_context_for_llm()
assert len(ctx.messages) <= 5  # Sliding window
assert "summary" in context or len(ctx.key_facts) > 0
```

---

### CHAT-03: Create Conversation-Aware RAG Pipeline

**Task ID**: CHAT-03  
**Objective**: Extend RAG pipeline to include conversation context in queries

**Requirements**:
- Create `conversational_query()` function in new `src/chat/rag_chat.py`
- Accept session_id parameter
- Retrieve conversation history from database
- Build context-aware prompt: history + current query
- Detect follow-up questions ("What about X?", "How do I do that?")
- Expand follow-ups with context from previous answers
- Include referenced pages from previous turns
- Update `query_llm()` to accept optional conversation context

**Dependencies**: CHAT-01, CHAT-02

**Deliverables**:
- `src/chat/rag_chat.py` - Conversation-aware RAG
- Follow-up detection logic
- Query expansion for context-dependent questions
- Updated `query_llm()` signature to accept context

**Acceptance Criteria**:
- [ ] Follow-up questions are detected automatically
- [ ] Context from previous answers is included
- [ ] Page citations from previous turns are accessible
- [ ] New user queries work normally (no context needed)
- [ ] Performance: <100ms overhead for context retrieval

**Testing**:
```python
from src.chat.rag_chat import conversational_query

# First question
result1 = conversational_query(
    session_id="sess_123",
    question="How do I create a user in RHEL?"
)

# Follow-up (should understand context)
result2 = conversational_query(
    session_id="sess_123",
    question="What about setting the password?"  # Follow-up
)
assert "useradd" in result2.get("context", "") or "password" in result2["answer"]
```

---

### CHAT-04: Add Chat API Endpoints

**Task ID**: CHAT-04  
**Objective**: Create REST API endpoints for conversation management

**Requirements**:
- `POST /chat/sessions` - Create new chat session
- `GET /chat/sessions` - List user's sessions
- `GET /chat/sessions/{id}` - Get session details with messages
- `DELETE /chat/sessions/{id}` - Archive session
- `POST /chat/sessions/{id}/messages` - Send message (get response)
- `GET /chat/sessions/{id}/messages` - Get message history
- `POST /chat/sessions/{id}/clear` - Clear history but keep session
- WebSocket support for streaming responses (optional)

**Dependencies**: CHAT-03

**Deliverables**:
- New router in `src/api/chat_router.py`
- Pydantic models for chat requests/responses
- Integration with main FastAPI app
- Rate limiting per session

**Acceptance Criteria**:
- [ ] Can create session and get session_id
- [ ] Sending message returns AI response with sources
- [ ] Follow-up questions work with context
- [ ] Can retrieve full conversation history
- [ ] Sessions can be listed, archived
- [ ] Clear history resets conversation but keeps session

**Testing**:
```bash
# Create session
curl -X POST http://localhost:8000/chat/sessions \
  -d '{"title": "RHEL Help"}'

# Send message
curl -X POST http://localhost:8000/chat/sessions/sess_123/messages \
  -d '{"message": "How to create user?"}'

# Follow-up
curl -X POST http://localhost:8000/chat/sessions/sess_123/messages \
  -d '{"message": "What about password?"}'

# Get history
curl http://localhost:8000/chat/sessions/sess_123/messages
```

---

### CHAT-05: Build Chat Interface in Web UI

**Task ID**: CHAT-05  
**Objective**: Create chat-based interface in Streamlit with conversation history

**Requirements**:
- Add chat page/section to Web UI
- Sidebar shows conversation list
- Main area shows chat messages (bubbles)
- Input box at bottom for new messages
- Show sources as expandable cards in assistant messages
- Allow starting new conversation
- Allow renaming/deleting conversations
- Show typing indicator during response
- Display token usage per conversation

**Dependencies**: CHAT-04

**Deliverables**:
- `src/web_ui_chat.py` - Chat interface module
- Updated `src/web_ui.py` with chat navigation
- Session management sidebar
- Message bubble components

**Acceptance Criteria**:
- [ ] Chat interface shows message history
- [ ] New messages appear with loading indicator
- [ ] Sources are shown in expandable sections
- [ ] Can start new conversation
- [ ] Can switch between conversations
- [ ] Conversations persist after page refresh
- [ ] Mobile-friendly layout

**Testing**:
```bash
streamlit run src/web_ui.py
# Navigate to Chat section
# Test: create session, ask questions, check follow-ups work
```

---

## Phase 4: Contextual Compression

### COMP-01: Implement Sentence-Level Relevance Extraction

**Task ID**: COMP-01  
**Objective**: Build system to extract only relevant sentences from retrieved chunks

**Requirements**:
- Create `src/compression/sentence_extractor.py`
- Split chunks into sentences using NLTK/spacy
- Calculate relevance score for each sentence vs query
- Use cross-encoder or cosine similarity for scoring
- Return top-K most relevant sentences
- Preserve sentence order from original text
- Handle code blocks as atomic units (don't split)
- Configurable compression ratio (default: 50%)

**Dependencies**: None (new module)

**Deliverables**:
- `src/compression/sentence_extractor.py`
- Sentence tokenization with code block handling
- Relevance scoring function
- Configurable compression ratio
- Tests with sample chunks

**Acceptance Criteria**:
- [ ] Sentences are extracted maintaining order
- [ ] Code blocks are preserved intact
- [ ] Relevance scores rank sentences correctly
- [ ] Compression ratio is configurable
- [ ] Performance: <500ms for 5 chunks
- [ ] Unit tests with edge cases (no sentences, all code, etc.)

**Testing**:
```python
from src.compression.sentence_extractor import SentenceExtractor

extractor = SentenceExtractor(compression_ratio=0.5)
chunk = """
This is sentence one about user management.
This is sentence two about disk space.
Use this command: useradd -m username
This is sentence four about networking.
"""

relevant = extractor.extract_relevant(chunk, "How to create user?")
assert "useradd" in relevant
assert "disk space" not in relevant  # Less relevant
```

---

### COMP-02: Integrate Compression into RAG Pipeline

**Task ID**: COMP-02  
**Objective**: Add contextual compression option to hybrid_search and query flow

**Requirements**:
- Add `enable_compression` parameter to `hybrid_search()`
- After retrieval, compress each chunk's content
- Maintain original metadata (page numbers, scores)
- Track token savings
- Update `format_context()` to handle compressed content
- Ensure citations still point to correct pages
- Add compression stats to query logging

**Dependencies**: COMP-01

**Deliverables**:
- Updated `src/rag_pipeline.py` with compression option
- `compress_results()` function
- Token savings tracking
- Updated query logging with compression metrics

**Acceptance Criteria**:
- [ ] `hybrid_search(query, enable_compression=True)` works
- [ ] Compressed context is used for LLM query
- [ ] Token count is reduced by 30-50%
- [ ] Page citations remain accurate
- [ ] Compression stats logged to database
- [ ] Can disable compression (backward compatible)

**Testing**:
```python
# Without compression
results1, _ = hybrid_search("user management", enable_compression=False)
context1, _ = format_context(results1)
tokens1 = count_tokens(context1)

# With compression
results2, _ = hybrid_search("user management", enable_compression=True)
context2, _ = format_context(results2)
tokens2 = count_tokens(context2)

assert tokens2 < tokens1 * 0.7  # At least 30% reduction
```

---

### COMP-03: Add Compression Controls to API and UI

**Task ID**: COMP-03  
**Objective**: Expose compression feature through API and Web UI

**Requirements**:
- Add `enable_compression` to `QueryRequest` model
- Add `compression_ratio` parameter (0.0 - 1.0)
- Return compression stats in response (tokens_saved, ratio)
- Add compression toggle in Web UI sidebar
- Show token savings in query results
- Add compression analytics to dashboard

**Dependencies**: COMP-02

**Deliverables**:
- Updated API endpoints with compression params
- Updated Web UI with compression controls
- Compression analytics in dashboard
- Documentation updates

**Acceptance Criteria**:
- [ ] API accepts compression parameters
- [ ] UI has toggle for enable/disable compression
- [ ] Token savings displayed to user
- [ ] Analytics tracks compression usage and savings
- [ ] Default is disabled (opt-in feature)

**Testing**:
```bash
# API with compression
curl -X POST http://localhost:8000/query \
  -d '{"question": "How to create user?", "enable_compression": true, "compression_ratio": 0.5}'

# Check response includes compression_stats
```

---

## Phase 5: Multi-Book Cross-Referencing

### CROSS-01: Implement Multi-Book Result Aggregation

**Task ID**: CROSS-01  
**Objective**: Modify search to retrieve and rank results from multiple books simultaneously

**Requirements**:
- Extend search to retrieve top-K from each book category
- Implement result deduplication (same content from different books)
- Add book-level relevance scoring
- Create book diversity filter (ensure multiple books represented)
- Update ranking algorithm to consider:
  - Chunk relevance score
  - Book authority (can be weighted)
  - Content freshness (if applicable)
- Return results grouped by book

**Dependencies**: SEARCH-01

**Deliverables**:
- `src/cross_reference/aggregator.py`
- Multi-book search function
- Deduplication logic
- Book diversity enforcement
- Result grouping by source book

**Acceptance Criteria**:
- [ ] Search returns results from multiple books when relevant
- [ ] Duplicate content is detected and merged
- [ ] Results can be grouped by book
- [ ] Diversity parameter ensures variety
- [ ] Performance: <2x single-book search time

**Testing**:
```python
from src.cross_reference.aggregator import multi_book_search

results = multi_book_search("container security", top_k_per_book=3)
books_represented = set(r.book_id for r in results)
assert len(books_represented) >= 2  # Multiple books
```

---

### CROSS-02: Build Answer Synthesis Engine

**Task ID**: CROSS-02  
**Objective**: Create system to synthesize answers from multiple book sources

**Requirements**:
- Create `src/cross_reference/synthesizer.py`
- Group sources by topic/section
- Detect conflicts between sources (different versions)
- Generate synthesized answer that:
  - Cites multiple books
  - Highlights consensus views
  - Notes discrepancies with source attribution
  - Orders information by relevance
- Create prompt template for synthesis
- Handle case where sources disagree

**Dependencies**: CROSS-01

**Deliverables**:
- `src/cross_reference/synthesizer.py`
- Conflict detection algorithm
- Synthesis prompt template
- Answer structure with multi-book citations

**Acceptance Criteria**:
- [ ] Answer cites sources from multiple books when applicable
- [ ] Conflicting information is flagged
- [ ] Consensus information is highlighted
- [ ] Citations include book name + page number
- [ ] Synthesis adds value vs concatenating sources

**Testing**:
```python
from src.cross_reference.synthesizer import synthesize_answer

sources = [
    {"book": "RHEL 9 Guide", "page": 100, "content": "Use command X"},
    {"book": "RHEL 8 Guide", "page": 95, "content": "Use command Y"},
]
answer = synthesize_answer("How to configure X?", sources)
assert "RHEL 9 Guide" in answer
assert "RHEL 8 Guide" in answer
# Should note difference between versions
```

---

### CROSS-03: Add Cross-Reference API and UI

**Task ID**: CROSS-03  
**Objective**: Expose multi-book search and synthesis through API and UI

**Requirements**:
- Add `enable_cross_reference` parameter to query endpoint
- Return `related_books` in response with relevance scores
- Add "See Also" section in UI with related topics from other books
- Show book comparison when sources conflict
- Add book filter to search (include/exclude specific books)
- Visual indicator for multi-book answers

**Dependencies**: CROSS-02

**Deliverables**:
- Updated API with cross-reference support
- Updated Web UI with book comparison view
- "See Also" recommendations component
- Book filter controls

**Acceptance Criteria**:
- [ ] API returns related books and cross-references
- [ ] UI shows when answer uses multiple books
- [ ] "See Also" suggests related content
- [ ] Book filter works in UI
- [ ] Conflicts are visually highlighted

**Testing**:
```bash
# Query with cross-reference
curl -X POST http://localhost:8000/query \
  -d '{"question": "container security", "enable_cross_reference": true}'

# Should include related_books and synthesis info
```

---

## Phase 6: Production Hardening

### PROD-01: Implement API Rate Limiting

**Task ID**: PROD-01  
**Objective**: Add rate limiting to prevent abuse and control costs

**Requirements**:
- Create `src/api/middleware/rate_limiter.py`
- Implement sliding window rate limit
- Different limits per endpoint:
  - `/query`: 10/minute, 100/hour per IP
  - `/chat`: 20/minute per session
  - `/health`: 60/minute (higher for monitoring)
- Return 429 status with Retry-After header
- Store rate limit counters in SQLite (simple) or Redis (scalable)
- Add rate limit info to response headers: X-RateLimit-Limit, X-RateLimit-Remaining

**Dependencies**: None

**Deliverables**:
- `src/api/middleware/rate_limiter.py`
- Rate limit configuration
- SQLite-based counter storage
- Middleware integration in FastAPI

**Acceptance Criteria**:
- [ ] Requests beyond limit return 429
- [ ] Rate limit headers present in responses
- [ ] Different limits apply per endpoint
- [ ] Limits are configurable
- [ ] Counter persists across restarts
- [ ] Whitelist for internal IPs (optional)

**Testing**:
```bash
# Test rate limit
for i in {1..15}; do
  curl -I http://localhost:8000/query -X POST
done
# Should see 429 after limit exceeded
```

---

### PROD-02: Add API Authentication

**Task ID**: PROD-02  
**Objective**: Implement API key authentication for production use

**Requirements**:
- Create `src/api/auth/` package
- Generate API keys: `sha256(uuid + secret + timestamp)`
- Store API keys in database with metadata: created_at, last_used, rate_limit_tier
- Support multiple authentication methods:
  - Header: `Authorization: Bearer <api_key>`
  - Query param: `?api_key=<key>` (for simple testing)
- Create API key management endpoints (admin only):
  - POST `/admin/api-keys` - Generate new key
  - GET `/admin/api-keys` - List keys
  - DELETE `/admin/api-keys/{id}` - Revoke key
- Default behavior: auth optional (backward compatible)

**Dependencies**: PROD-01

**Deliverables**:
- `src/api/auth/manager.py` - Key management
- `src/api/auth/dependencies.py` - FastAPI dependencies
- Admin endpoints for key management
- Database migration for api_keys table

**Acceptance Criteria**:
- [ ] Can generate and revoke API keys
- [ ] Valid keys allow access
- [ ] Invalid keys return 401
- [ ] Last used timestamp updated on each request
- [ ] Different rate limits per key tier
- [ ] Can disable auth for development mode

**Testing**:
```bash
# Generate key (admin)
curl -X POST http://localhost:8000/admin/api-keys \
  -H "Authorization: Bearer admin_secret"

# Use key
curl http://localhost:8000/query \
  -H "Authorization: Bearer <api_key>" \
  -d '{"question": "test"}'

# Invalid key
curl http://localhost:8000/query \
  -H "Authorization: Bearer invalid_key"
# Should return 401
```

---

### PROD-03: Implement Structured Logging

**Task ID**: PROD-03  
**Objective**: Replace print statements with structured JSON logging

**Requirements**:
- Create `src/utils/logger.py` with structured logging
- Use Python `logging` with JSON formatter
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Standard log fields:
  - timestamp (ISO 8601)
  - level
  - message
  - module
  - request_id (correlation ID)
  - user_id (if authenticated)
  - duration_ms (for operations)
- Separate log files:
  - `logs/app.jsonl` - Application logs
  - `logs/query.jsonl` - Query logs (structured)
  - `logs/error.jsonl` - Error logs only
- Log rotation: 10MB files, keep 5 backups

**Dependencies**: None

**Deliverables**:
- `src/utils/logger.py` - Structured logger
- `logs/` directory configuration
- Log rotation setup
- Replace all print statements in codebase

**Acceptance Criteria**:
- [ ] All logs are valid JSON
- [ ] Log rotation works (test with small size limit)
- [ ] Different log levels go to appropriate files
- [ ] Request correlation IDs work
- [ ] No print statements remain in production code
- [ ] Logs can be easily parsed by log aggregation tools

**Testing**:
```python
from src.utils.logger import get_logger

logger = get_logger("test")
logger.info("Test message", extra={"user_id": "user123", "query": "test"})
# Check logs/app.jsonl for structured output
```

---

### PROD-04: Add Prometheus Metrics Endpoint

**Task ID**: PROD-04  
**Objective**: Expose metrics for monitoring with Prometheus/Grafana

**Requirements**:
- Add `/metrics` endpoint using `prometheus-client`
- Export key metrics:
  - `redcortex_queries_total` - Counter with method, status labels
  - `redcortex_query_duration_seconds` - Histogram
  - `redcortex_cache_hits_total` - Counter
  - `redcortex_llm_tokens_total` - Counter with model label
  - `redcortex_llm_cost_usd` - Gauge
  - `redcortex_active_sessions` - Gauge
  - `redcortex_books_indexed` - Gauge with category label
  - `redcortex_chunks_total` - Gauge
- Add custom collectors for application-specific metrics
- Document metrics in `docs/METRICS.md`

**Dependencies**: PROD-03

**Deliverables**:
- `src/api/metrics.py` - Metrics collection
- Updated `src/api/main.py` with /metrics endpoint
- `docs/METRICS.md` - Documentation
- Sample Prometheus config

**Acceptance Criteria**:
- [ ] `/metrics` returns Prometheus format
- [ ] All key metrics are exported
- [ ] Metrics update in real-time
- [ ] Labels work for filtering/aggregation
- [ ] Documentation explains each metric
- [ ] Can import into Prometheus without errors

**Testing**:
```bash
# Check metrics
curl http://localhost:8000/metrics

# Should see redcortex_* metrics
```

---

## Implementation Order

### Week 1: Scale
1. **SCALE-01**: Book configuration system
2. **SCALE-03**: Category database schema
3. **SCALE-04**: Category-aware ingestion
4. **SCALE-02**: Batch ingestion runner
5. Run batch ingestion for all books

### Week 2: Search & Categories
6. **SEARCH-01**: Category filtering in pipeline
7. **SEARCH-02**: Category API endpoints
8. **SEARCH-03**: Category UI
9. **CROSS-01**: Multi-book aggregation

### Week 3: Conversational Memory
10. **CHAT-01**: Session schema
11. **CHAT-02**: Context window management
12. **CHAT-03**: Conversation-aware RAG
13. **CHAT-04**: Chat API endpoints
14. **CHAT-05**: Chat UI

### Week 4: Compression & Production
15. **COMP-01**: Sentence extraction
16. **COMP-02**: Compression in pipeline
17. **COMP-03**: Compression API/UI
18. **CROSS-02**: Answer synthesis
19. **CROSS-03**: Cross-reference UI
20. **PROD-01**: Rate limiting
21. **PROD-02**: API authentication
22. **PROD-03**: Structured logging
23. **PROD-04**: Prometheus metrics

---

## Testing Strategy

### Unit Tests
Each deliverable should include unit tests in `tests/unit/`

### Integration Tests
Create `tests/integration/test_v2.2_features.py`:
- End-to-end category filtering
- Full conversation flow
- Compression effectiveness
- Multi-book synthesis

### Load Tests
Create `tests/load/test_api.py`:
- 100 concurrent queries
- Rate limiting effectiveness
- Memory usage under load

---

## Documentation Updates

Update these documents as features are implemented:

- `README.md` - Feature list and quick start
- `docs/API.md` - New endpoints and parameters
- `docs/ROADMAP-v2.md` - Mark completed features
- `docs/DEPLOYMENT.md` - Production setup with auth
- `docs/CHANGES-v2.2.md` - Changelog

---

## Success Criteria for v2.2

| Metric | Target | Measurement |
|--------|--------|-------------|
| Books Indexed | 15+ | Database count |
| Category Filter Usage | >30% | Query logs |
| Avg Tokens/Query | -40% | Compression stats |
| Multi-turn Sessions | >20% | Chat logs |
| API Uptime | 99.9% | Health checks |
| P95 Query Latency | <3s | Metrics |
| Cache Hit Rate | >60% | Query logs |

---

*End of Implementation Plan*
