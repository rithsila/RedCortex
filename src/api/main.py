#!/usr/bin/env python3
"""
RedCortex FastAPI Backend
Provides REST API endpoints for RAG queries
"""
import os
import sys
import time
from typing import List, Optional
from datetime import datetime
from contextlib import asynccontextmanager

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, 'src')

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
import uvicorn

from rag_pipeline import (
    hybrid_search, 
    format_context, 
    query_llm,
    get_cached_response,
    get_cache_key,
    MODEL_DEFAULT
)
from utils.query_logger import QueryLogger

# API Configuration
API_VERSION = "2.1.0"
API_TITLE = "RedCortex API"
API_DESCRIPTION = "Production-grade RAG API for Red Hat Enterprise Linux documentation"

# Initialize components
query_logger = QueryLogger()
security = HTTPBearer(auto_error=False)


# Pydantic Models
class QueryRequest(BaseModel):
    """Query request model"""
    question: str = Field(..., min_length=3, max_length=1000, description="The question to ask")
    top_k: int = Field(default=5, ge=1, le=10, description="Number of sources to retrieve")
    enable_hybrid: bool = Field(default=True, description="Enable hybrid search (BM25 + Vector)")
    model: str = Field(default=MODEL_DEFAULT, description="LLM model to use")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "How do I create a user in RHEL?",
                "top_k": 5,
                "enable_hybrid": True,
                "model": "qwen/qwen3-coder"
            }
        }


class Source(BaseModel):
    """Source document model"""
    chunk_id: int
    page_start: int
    page_end: int
    score: float
    source_type: str
    preview: str


class QueryResponse(BaseModel):
    """Query response model"""
    success: bool
    question: str
    answer: str
    sources: List[Source]
    metadata: dict


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: str
    components: dict


class StatsResponse(BaseModel):
    """Statistics response"""
    period_days: int
    total_queries: int
    unique_queries: int
    cache_hit_rate: float
    avg_latency_ms: float
    total_cost_usd: float
    error_count: int
    error_rate: float
    top_queries: List[tuple]
    search_method_distribution: dict


class BookInfo(BaseModel):
    """Book information model"""
    id: int
    title: str
    category: Optional[str]
    status: str
    total_pages: Optional[int]
    created_at: str


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    print(f"🚀 {API_TITLE} v{API_VERSION} starting up...")
    yield
    print(f"👋 {API_TITLE} shutting down...")


# Create FastAPI app
app = FastAPI(
    title=API_TITLE,
    description=API_DESCRIPTION,
    version=API_VERSION,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependencies
async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API token (placeholder for future auth)"""
    # For now, accept any token or no token
    # In production, validate against database
    return credentials


# API Endpoints
@app.get("/", tags=["General"])
async def root():
    """API root endpoint"""
    return {
        "name": API_TITLE,
        "version": API_VERSION,
        "status": "operational",
        "documentation": "/docs"
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """Health check endpoint"""
    start_time = time.time()
    
    components = {
        "database": "unknown",
        "qdrant": "unknown",
        "ollama": "unknown",
        "openrouter": "unknown"
    }
    
    # Check database
    try:
        import sqlite3
        conn = sqlite3.connect("data/library.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM books")
        book_count = cursor.fetchone()[0]
        conn.close()
        components["database"] = f"connected ({book_count} books)"
    except Exception as e:
        components["database"] = f"error: {str(e)}"
    
    # Check Qdrant
    try:
        from qdrant_client import QdrantClient
        client = QdrantClient(
            url=os.getenv("QDRANT_URL"),
            api_key=os.getenv("QDRANT_API_KEY")
        )
        collections = client.get_collections()
        components["qdrant"] = f"connected ({len(collections.collections)} collections)"
    except Exception as e:
        components["qdrant"] = f"error: {str(e)}"
    
    # Check Ollama
    try:
        import httpx
        response = httpx.get(
            f"{os.getenv('OLLAMA_HOST', 'http://localhost:11434')}/api/tags",
            timeout=5.0
        )
        if response.status_code == 200:
            components["ollama"] = "connected"
        else:
            components["ollama"] = f"error: HTTP {response.status_code}"
    except Exception as e:
        components["ollama"] = f"error: {str(e)}"
    
    # Determine overall status
    all_healthy = all("connected" in str(v) for v in components.values())
    status = "healthy" if all_healthy else "degraded"
    
    return HealthResponse(
        status=status,
        version=API_VERSION,
        timestamp=datetime.now().isoformat(),
        components=components
    )


@app.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    credentials: HTTPAuthorizationCredentials = Depends(verify_token)
):
    """
    Execute a RAG query against the knowledge base.
    """
    start_time = time.time()
    
    try:
        # Check cache first
        cache_key = get_cache_key(request.question, request.model, request.top_k)
        cached = get_cached_response(cache_key)
        
        if cached:
            # Return cached response
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Log cached query
            background_tasks.add_task(
                query_logger.log_query,
                query=request.question,
                answer=cached["answer"],
                model_used=request.model,
                search_method="cache",
                latency_ms=latency_ms,
                sources_count=0,
                cache_hit=True,
                cost_usd=0.0
            )
            
            return QueryResponse(
                success=True,
                question=request.question,
                answer=cached["answer"],
                sources=[],
                metadata={
                    "model": request.model,
                    "search_method": "cache",
                    "latency_ms": latency_ms,
                    "cache_hit": True,
                    "cost_usd": 0.0
                }
            )
        
        # Perform search
        search_start = time.time()
        results, method = hybrid_search(
            request.question, 
            top_k=request.top_k, 
            enable_hybrid=request.enable_hybrid
        )
        search_time = time.time() - search_start
        
        if not results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No relevant documents found in knowledge base"
            )
        
        # Format context and query LLM
        context, source_texts = format_context(results)
        
        llm_start = time.time()
        answer, cost_info, used_model = query_llm(
            request.question,
            context,
            request.model,
            method,
            len(results)
        )
        llm_time = time.time() - llm_start
        
        total_latency_ms = int((time.time() - start_time) * 1000)
        
        # Parse cost
        cost_usd = None
        if "Tokens:" in cost_info:
            try:
                tokens = int(cost_info.split("Tokens:")[1].split()[0])
                cost_usd = tokens * 0.75 / 1000000
            except:
                pass
        
        # Format sources
        sources = [
            Source(
                chunk_id=r.chunk_id,
                page_start=r.page_start,
                page_end=r.page_end,
                score=r.score,
                source_type=r.source,
                preview=r.content[:200] + "..."
            )
            for r in results
        ]
        
        # Log query in background
        background_tasks.add_task(
            query_logger.log_query,
            query=request.question,
            answer=answer,
            model_used=used_model,
            search_method=method,
            latency_ms=total_latency_ms,
            sources_count=len(results),
            cache_hit=False,
            cost_usd=cost_usd
        )
        
        return QueryResponse(
            success=True,
            question=request.question,
            answer=answer,
            sources=sources,
            metadata={
                "model": used_model,
                "search_method": method,
                "search_time_ms": int(search_time * 1000),
                "llm_time_ms": int(llm_time * 1000),
                "total_latency_ms": total_latency_ms,
                "cache_hit": False,
                "sources_count": len(results),
                "cost_usd": cost_usd
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        # Log error
        latency_ms = int((time.time() - start_time) * 1000)
        background_tasks.add_task(
            query_logger.log_query,
            query=request.question,
            answer="",
            model_used=request.model,
            search_method="error",
            latency_ms=latency_ms,
            sources_count=0,
            cache_hit=False,
            error=str(e)
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query processing failed: {str(e)}"
        )


@app.get("/books", response_model=List[BookInfo], tags=["Knowledge Base"])
async def list_books():
    """List all indexed books"""
    try:
        import sqlite3
        conn = sqlite3.connect("data/library.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, title, category, status, total_pages, created_at 
            FROM books 
            ORDER BY id
        ''')
        
        books = []
        for row in cursor.fetchall():
            books.append(BookInfo(
                id=row['id'],
                title=row['title'],
                category=row['category'],
                status=row['status'],
                total_pages=row['total_pages'],
                created_at=row['created_at']
            ))
        
        conn.close()
        return books
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch books: {str(e)}"
        )


@app.get("/stats", response_model=StatsResponse, tags=["Analytics"])
async def get_stats(days: int = 7):
    """Get query statistics"""
    try:
        stats = query_logger.get_analytics(days=days)
        return StatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch stats: {str(e)}"
        )


@app.get("/stats/recent", tags=["Analytics"])
async def get_recent_queries(limit: int = 10):
    """Get recent queries"""
    try:
        queries = query_logger.get_recent_queries(limit=limit)
        return {"queries": queries}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch recent queries: {str(e)}"
        )


# Run server
if __name__ == "__main__":
    port = int(os.getenv("API_PORT", 8000))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    print(f"\n🚀 Starting {API_TITLE} v{API_VERSION}")
    print(f"📖 Documentation: http://{host}:{port}/docs")
    print(f"🔍 Health Check: http://{host}:{port}/health\n")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )
