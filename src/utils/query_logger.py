#!/usr/bin/env python3
"""
Query Logger for RedCortex
Logs all queries for analytics and monitoring
"""
import os
import sys
import sqlite3
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@dataclass
class QueryLogEntry:
    """Structure for query log entries"""
    timestamp: str
    query: str
    query_hash: str
    answer: str
    model_used: str
    search_method: str
    latency_ms: int
    tokens_used: Optional[int]
    cost_usd: Optional[float]
    sources_count: int
    cache_hit: bool
    error: Optional[str] = None
    user_feedback: Optional[int] = None  # 1 for thumbs up, -1 for thumbs down


class QueryLogger:
    """Logger for RAG queries"""
    
    def __init__(self, db_path: str = "data/library.db"):
        self.db_path = db_path
        self._ensure_table()
    
    def _ensure_table(self):
        """Ensure query_logs table exists with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if we need to migrate the existing queries table
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='queries'")
        if cursor.fetchone():
            # Check if new columns exist
            cursor.execute("PRAGMA table_info(queries)")
            columns = [col[1] for col in cursor.fetchall()]
            
            # Add missing columns
            if 'search_method' not in columns:
                cursor.execute("ALTER TABLE queries ADD COLUMN search_method TEXT")
            if 'sources_count' not in columns:
                cursor.execute("ALTER TABLE queries ADD COLUMN sources_count INTEGER DEFAULT 0")
            if 'cache_hit' not in columns:
                cursor.execute("ALTER TABLE queries ADD COLUMN cache_hit BOOLEAN DEFAULT 0")
            if 'query_hash' not in columns:
                cursor.execute("ALTER TABLE queries ADD COLUMN query_hash TEXT")
            if 'user_feedback' not in columns:
                cursor.execute("ALTER TABLE queries ADD COLUMN user_feedback INTEGER")
            if 'error' not in columns:
                cursor.execute("ALTER TABLE queries ADD COLUMN error TEXT")
            
            conn.commit()
        else:
            # Create new comprehensive table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    query TEXT NOT NULL,
                    query_hash TEXT,
                    answer TEXT,
                    model_used TEXT,
                    search_method TEXT,
                    latency_ms INTEGER,
                    tokens_used INTEGER,
                    cost_usd REAL,
                    sources_count INTEGER DEFAULT 0,
                    cache_hit BOOLEAN DEFAULT 0,
                    error TEXT,
                    user_feedback INTEGER,
                    metadata TEXT  -- JSON for extensibility
                )
            ''')
            conn.commit()
        
        conn.close()
    
    def log_query(
        self,
        query: str,
        answer: str,
        model_used: str,
        search_method: str,
        latency_ms: int,
        sources_count: int = 0,
        cache_hit: bool = False,
        tokens_used: Optional[int] = None,
        cost_usd: Optional[float] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Log a query to the database"""
        
        # Generate query hash for deduplication/analytics
        query_hash = self._hash_query(query)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Use 'question' column name (matches existing schema)
        cursor.execute('''
            INSERT INTO queries 
            (question, query_hash, model_used, search_method, latency_ms, 
             cost_usd, sources_count, cache_hit, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            query,
            query_hash,
            model_used,
            search_method,
            latency_ms,
            cost_usd,
            sources_count,
            cache_hit,
            error
        ))
        
        query_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return query_id
    
    def _hash_query(self, query: str) -> str:
        """Create a normalized hash of the query for analytics"""
        import hashlib
        normalized = query.lower().strip()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def add_feedback(self, query_id: int, rating: int):
        """Add user feedback to a query"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE queries SET user_feedback = ? WHERE id = ?",
            (rating, query_id)
        )
        
        conn.commit()
        conn.close()
    
    def get_analytics(self, days: int = 7) -> Dict[str, Any]:
        """Get query analytics for the past N days"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total queries
        cursor.execute('''
            SELECT COUNT(*) FROM queries 
            WHERE timestamp >= datetime('now', '-{} days')
        '''.format(days))
        total_queries = cursor.fetchone()[0]
        
        # Unique queries (by hash)
        cursor.execute('''
            SELECT COUNT(DISTINCT query_hash) FROM queries 
            WHERE timestamp >= datetime('now', '-{} days')
        '''.format(days))
        unique_queries = cursor.fetchone()[0]
        
        # Cache hit rate
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN cache_hit = 1 THEN 1 END) as hits,
                COUNT(*) as total
            FROM queries 
            WHERE timestamp >= datetime('now', '-{} days')
        '''.format(days))
        cache_data = cursor.fetchone()
        cache_hits = cache_data[0] if cache_data else 0
        cache_rate = (cache_hits / cache_data[1] * 100) if cache_data[1] > 0 else 0
        
        # Average latency
        cursor.execute('''
            SELECT AVG(latency_ms) FROM queries 
            WHERE timestamp >= datetime('now', '-{} days')
            AND error IS NULL
        '''.format(days))
        avg_latency = cursor.fetchone()[0] or 0
        
        # Total cost
        cursor.execute('''
            SELECT SUM(cost_usd) FROM queries 
            WHERE timestamp >= datetime('now', '-{} days')
            AND error IS NULL
        '''.format(days))
        total_cost = cursor.fetchone()[0] or 0
        
        # Error rate
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN error IS NOT NULL THEN 1 END) as errors,
                COUNT(*) as total
            FROM queries 
            WHERE timestamp >= datetime('now', '-{} days')
        '''.format(days))
        error_data = cursor.fetchone()
        error_count = error_data[0] if error_data else 0
        error_rate = (error_count / error_data[1] * 100) if error_data[1] > 0 else 0
        
        # Top queries
        cursor.execute('''
            SELECT question, COUNT(*) as count 
            FROM queries 
            WHERE timestamp >= datetime('now', '-{} days')
            GROUP BY query_hash 
            ORDER BY count DESC 
            LIMIT 5
        '''.format(days))
        top_queries = cursor.fetchall()
        
        # Search method distribution
        cursor.execute('''
            SELECT search_method, COUNT(*) as count 
            FROM queries 
            WHERE timestamp >= datetime('now', '-{} days')
            AND search_method IS NOT NULL
            GROUP BY search_method
        '''.format(days))
        search_methods = {row[0]: row[1] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            "period_days": days,
            "total_queries": total_queries,
            "unique_queries": unique_queries,
            "cache_hit_rate": round(cache_rate, 1),
            "avg_latency_ms": round(avg_latency, 0),
            "total_cost_usd": round(total_cost, 4),
            "error_count": error_count,
            "error_rate": round(error_rate, 1),
            "top_queries": top_queries,
            "search_method_distribution": search_methods
        }
    
    def get_recent_queries(self, limit: int = 10) -> list:
        """Get recent queries for display"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, timestamp, question as query, model_used, search_method, 
                   latency_ms, sources_count, cache_hit, error
            FROM queries 
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]


def main():
    """CLI for query logger utilities"""
    logger = QueryLogger()
    
    if len(sys.argv) < 2:
        print("Usage: python src/utils/query_logger.py <command>")
        print("\nCommands:")
        print("  stats [days]     - Show query analytics (default: 7 days)")
        print("  recent [limit]   - Show recent queries (default: 10)")
        print("  feedback <id> <1|-1>  - Add feedback to query")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "stats":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 7
        stats = logger.get_analytics(days)
        
        print(f"\n📊 Query Analytics (Last {days} days)")
        print("=" * 50)
        print(f"Total Queries:      {stats['total_queries']}")
        print(f"Unique Queries:     {stats['unique_queries']}")
        print(f"Cache Hit Rate:     {stats['cache_hit_rate']}%")
        print(f"Avg Latency:        {stats['avg_latency_ms']}ms")
        print(f"Total Cost:         ${stats['total_cost_usd']}")
        print(f"Errors:             {stats['error_count']} ({stats['error_rate']}%)")
        
        if stats['top_queries']:
            print(f"\n🔥 Top Queries:")
            for query, count in stats['top_queries']:
                print(f"  {count}x: {query[:50]}...")
        
        if stats['search_method_distribution']:
            print(f"\n🔍 Search Methods:")
            for method, count in stats['search_method_distribution'].items():
                print(f"  {method}: {count}")
    
    elif command == "recent":
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        queries = logger.get_recent_queries(limit)
        
        print(f"\n📝 Recent Queries (Last {limit})")
        print("=" * 80)
        for q in queries:
            status = "❌" if q['error'] else ("💾" if q['cache_hit'] else "✓")
            print(f"\n{status} [{q['timestamp']}] {q['query'][:60]}...")
            print(f"   Method: {q['search_method']}, Latency: {q['latency_ms']}ms, Sources: {q['sources_count']}")
    
    elif command == "feedback":
        if len(sys.argv) < 4:
            print("Usage: query_logger.py feedback <query_id> <1|-1>")
            sys.exit(1)
        query_id = int(sys.argv[2])
        rating = int(sys.argv[3])
        logger.add_feedback(query_id, rating)
        print(f"✅ Feedback recorded for query {query_id}")
    
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
