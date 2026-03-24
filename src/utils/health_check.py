#!/usr/bin/env python3
"""
Health Check Script for RedCortex
Checks all system components before going live
"""
import os
import sys
import sqlite3
import time
import httpx
import requests
from datetime import datetime
from typing import Dict, List, Tuple

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()


class HealthChecker:
    """System health checker for RedCortex"""
    
    def __init__(self):
        self.checks: List[Tuple[str, bool, str]] = []
        self.warnings: List[str] = []
        
    def run_all_checks(self) -> bool:
        """Run all health checks and return overall status"""
        print("🔍 RedCortex Health Check")
        print("=" * 60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Core infrastructure checks
        self._check_environment()
        self._check_database()
        self._check_ollama()
        self._check_qdrant()
        self._check_openrouter()
        
        # Data checks
        self._check_books()
        self._check_chunks()
        
        # System checks
        self._check_disk_space()
        self._check_cache_dir()
        
        # Print summary
        print()
        print("=" * 60)
        print("📊 Health Check Summary")
        print("=" * 60)
        
        passed = sum(1 for _, status, _ in self.checks if status)
        failed = sum(1 for _, status, _ in self.checks if not status)
        
        for check_name, status, message in self.checks:
            icon = "✅" if status else "❌"
            print(f"{icon} {check_name}: {message}")
        
        if self.warnings:
            print()
            print("⚠️  Warnings:")
            for warning in self.warnings:
                print(f"   - {warning}")
        
        print()
        print(f"Result: {passed}/{len(self.checks)} checks passed")
        
        if failed == 0:
            print("🎉 System is healthy and ready for production!")
            return True
        else:
            print(f"⚠️  {failed} check(s) failed. Please fix before going live.")
            return False
    
    def _add_check(self, name: str, status: bool, message: str):
        """Add a check result"""
        self.checks.append((name, status, message))
        icon = "✅" if status else "❌"
        print(f"{icon} {name}: {message}")
    
    def _check_environment(self):
        """Check environment variables"""
        print("\n📋 Environment Configuration")
        print("-" * 40)
        
        required_vars = ['QDRANT_URL', 'QDRANT_API_KEY', 'OPENROUTER_API_KEY']
        missing = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing.append(var)
        
        if missing:
            self._add_check("Environment", False, f"Missing: {', '.join(missing)}")
        else:
            self._add_check("Environment", True, "All required variables set")
    
    def _check_database(self):
        """Check SQLite database"""
        print("\n🗄️  Database")
        print("-" * 40)
        
        try:
            if not os.path.exists("data/library.db"):
                self._add_check("Database", False, "Database file not found")
                return
            
            conn = sqlite3.connect("data/library.db")
            cursor = conn.cursor()
            
            # Check tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            
            required_tables = ['books', 'chunks', 'queries']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                self._add_check("Database", False, f"Missing tables: {missing_tables}")
            else:
                # Get counts
                cursor.execute("SELECT COUNT(*) FROM books")
                book_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM chunks")
                chunk_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM queries")
                query_count = cursor.fetchone()[0]
                
                self._add_check("Database", True, 
                    f"Connected ({book_count} books, {chunk_count} chunks, {query_count} queries)")
            
            conn.close()
            
        except Exception as e:
            self._add_check("Database", False, f"Error: {str(e)}")
    
    def _check_ollama(self):
        """Check Ollama connection"""
        print("\n🧠 Ollama (Embeddings)")
        print("-" * 40)
        
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        try:
            response = httpx.get(f"{ollama_host}/api/tags", timeout=5.0)
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                
                if "nomic-embed-text" in str(model_names):
                    self._add_check("Ollama", True, 
                        f"Connected ({len(models)} models, nomic-embed-text available)")
                else:
                    self._add_check("Ollama", True, 
                        f"Connected but nomic-embed-text not found")
                    self.warnings.append("Run: ollama pull nomic-embed-text")
            else:
                self._add_check("Ollama", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self._add_check("Ollama", False, f"Not reachable ({str(e)})")
    
    def _check_qdrant(self):
        """Check Qdrant connection"""
        print("\n🔍 Qdrant (Vector DB)")
        print("-" * 40)
        
        try:
            from qdrant_client import QdrantClient
            
            client = QdrantClient(
                url=os.getenv("QDRANT_URL"),
                api_key=os.getenv("QDRANT_API_KEY")
            )
            
            # Try to get collections
            collections = client.get_collections()
            collection_names = [c.name for c in collections.collections]
            
            if "books_hot" in collection_names:
                # Get collection info
                info = client.get_collection("books_hot")
                vectors_count = info.points_count
                
                self._add_check("Qdrant", True, 
                    f"Connected ({vectors_count} vectors in books_hot)")
            else:
                self._add_check("Qdrant", True, 
                    f"Connected but 'books_hot' collection not found")
                self.warnings.append("Run: python src/utils/setup_collection.py")
                
        except Exception as e:
            self._add_check("Qdrant", False, f"Connection failed ({str(e)})")
    
    def _check_openrouter(self):
        """Check OpenRouter API"""
        print("\n🤖 OpenRouter (LLM)")
        print("-" * 40)
        
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            self._add_check("OpenRouter", False, "API key not configured")
            return
        
        try:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            
            # Just check if we can reach the API (don't actually call it)
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                self._add_check("OpenRouter", True, "API key valid")
            elif response.status_code == 401:
                self._add_check("OpenRouter", False, "API key invalid")
            else:
                self._add_check("OpenRouter", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self._add_check("OpenRouter", False, f"Connection failed ({str(e)})")
    
    def _check_books(self):
        """Check indexed books"""
        print("\n📚 Books")
        print("-" * 40)
        
        try:
            conn = sqlite3.connect("data/library.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM books WHERE status = 'indexed'")
            indexed = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM books WHERE status = 'indexing'")
            indexing = cursor.fetchone()[0]
            
            cursor.execute("SELECT title FROM books ORDER BY id")
            titles = [t[0] for t in cursor.fetchall()]
            
            conn.close()
            
            if indexed == 0 and indexing == 0:
                self._add_check("Books", False, "No books indexed")
                self.warnings.append("Run: python src/ingestion/ingest.py <pdf> <title>")
            else:
                self._add_check("Books", True, 
                    f"{indexed} indexed, {indexing} in progress")
                
                if titles:
                    print(f"   Indexed: {', '.join(titles[:3])}")
                    
        except Exception as e:
            self._add_check("Books", False, f"Error: {str(e)}")
    
    def _check_chunks(self):
        """Check chunks"""
        print("\n🧩 Chunks")
        print("-" * 40)
        
        try:
            conn = sqlite3.connect("data/library.db")
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM chunks WHERE is_hot = 1")
            hot_chunks = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM chunks")
            total_chunks = cursor.fetchone()[0]
            
            conn.close()
            
            if total_chunks == 0:
                self._add_check("Chunks", False, "No chunks in database")
            elif hot_chunks == 0:
                self._add_check("Chunks", False, "No hot chunks (is_hot=1)")
                self.warnings.append("Chunks exist but none marked as hot (is_hot=1)")
            else:
                self._add_check("Chunks", True, 
                    f"{hot_chunks} hot / {total_chunks} total")
                
        except Exception as e:
            self._add_check("Chunks", False, f"Error: {str(e)}")
    
    def _check_disk_space(self):
        """Check disk space"""
        print("\n💾 Disk Space")
        print("-" * 40)
        
        try:
            import shutil
            
            stat = shutil.disk_usage(".")
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            percent_used = (stat.used / stat.total) * 100
            
            if free_gb < 1:
                self._add_check("Disk Space", False, 
                    f"Critical: {free_gb:.1f}GB free ({percent_used:.0f}% used)")
            elif free_gb < 5:
                self._add_check("Disk Space", True, 
                    f"Low: {free_gb:.1f}GB free ({percent_used:.0f}% used)")
                self.warnings.append(f"Low disk space: {free_gb:.1f}GB remaining")
            else:
                self._add_check("Disk Space", True, 
                    f"{free_gb:.1f}GB free ({percent_used:.0f}% used)")
                
        except Exception as e:
            self._add_check("Disk Space", False, f"Error: {str(e)}")
    
    def _check_cache_dir(self):
        """Check cache directory"""
        print("\n💾 Cache")
        print("-" * 40)
        
        cache_dir = "data/cache"
        
        if not os.path.exists(cache_dir):
            try:
                os.makedirs(cache_dir)
                self._add_check("Cache", True, "Directory created")
            except Exception as e:
                self._add_check("Cache", False, f"Cannot create directory: {str(e)}")
        else:
            # Count cached files
            try:
                files = os.listdir(cache_dir)
                json_files = [f for f in files if f.endswith('.json')]
                self._add_check("Cache", True, f"{len(json_files)} cached responses")
            except Exception as e:
                self._add_check("Cache", False, f"Error reading cache: {str(e)}")


def main():
    """Run health check"""
    checker = HealthChecker()
    healthy = checker.run_all_checks()
    
    sys.exit(0 if healthy else 1)


if __name__ == "__main__":
    main()
