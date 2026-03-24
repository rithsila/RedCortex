#!/usr/bin/env python3
"""
Test Query Suite for RedCortex
Sanity check queries to verify deployment readiness
"""
import os
import sys
import time

# Change to project root
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.path.insert(0, 'src')
from rag_pipeline import hybrid_search, format_context, query_llm, MODEL_DEFAULT


# Test queries covering different RHEL topics
TEST_QUERIES = [
    {
        "name": "User Management",
        "query": "How do I create a new user account in RHEL?",
        "category": "user_management",
        "expected_keywords": ["useradd", "user", "create"]
    },
    {
        "name": "Systemctl Basics",
        "query": "How to start and enable a service using systemctl?",
        "category": "services",
        "expected_keywords": ["systemctl", "start", "enable"]
    },
    {
        "name": "Firewalld Configuration",
        "query": "How do I configure firewalld rich rules?",
        "category": "networking",
        "expected_keywords": ["firewall", "firewalld", "rich rules"]
    },
    {
        "name": "SSH Key Authentication",
        "query": "How to set up SSH key authentication?",
        "category": "security",
        "expected_keywords": ["ssh", "key", "authentication"]
    },
    {
        "name": "File Permissions",
        "query": "How do I change file permissions with chmod?",
        "category": "filesystem",
        "expected_keywords": ["chmod", "permission"]
    },
    {
        "name": "SELinux Basics",
        "query": "What is SELinux and how do I check its status?",
        "category": "security",
        "expected_keywords": ["selinux", "getenforce", "sestatus"]
    },
    {
        "name": "Package Management",
        "query": "How to install packages with dnf?",
        "category": "packages",
        "expected_keywords": ["dnf", "install", "package"]
    },
    {
        "name": "Disk Management",
        "query": "How do I check disk space usage?",
        "category": "storage",
        "expected_keywords": ["df", "du", "disk"]
    },
    {
        "name": "Network Configuration",
        "query": "How to configure network interface with nmcli?",
        "category": "networking",
        "expected_keywords": ["nmcli", "network"]
    },
    {
        "name": "Process Management",
        "query": "How to view and manage running processes?",
        "category": "processes",
        "expected_keywords": ["ps", "top", "process"]
    }
]


class QueryTester:
    """Test suite for RAG queries"""
    
    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        
    def run_all_tests(self, skip_llm: bool = False):
        """Run all test queries"""
        print("🧪 RedCortex Test Query Suite")
        print("=" * 70)
        print(f"Running {len(TEST_QUERIES)} test queries...")
        print()
        
        for i, test in enumerate(TEST_QUERIES, 1):
            print(f"\n[{i}/{len(TEST_QUERIES)}] Testing: {test['name']}")
            print(f"Query: \"{test['query']}\"")
            print("-" * 50)
            
            success = self._run_single_test(test, skip_llm=skip_llm)
            
            if success:
                self.passed += 1
            else:
                self.failed += 1
        
        self._print_summary()
        
        return self.failed == 0
    
    def _run_single_test(self, test: dict, skip_llm: bool = False) -> bool:
        """Run a single test query"""
        try:
            # Test retrieval
            start_time = time.time()
            results, method = hybrid_search(test['query'], top_k=5, enable_hybrid=True)
            search_time = time.time() - start_time
            
            if not results:
                print("  ❌ No retrieval results")
                return False
            
            print(f"  ✅ Retrieved {len(results)} sources ({method})")
            print(f"  ⏱️  Search time: {search_time:.2f}s")
            
            # Check if expected keywords appear in results
            found_keywords = []
            content_combined = " ".join([r.content.lower() for r in results])
            
            for keyword in test['expected_keywords']:
                if keyword.lower() in content_combined:
                    found_keywords.append(keyword)
            
            keyword_match = len(found_keywords) / len(test['expected_keywords'])
            print(f"  🔑 Keyword match: {len(found_keywords)}/{len(test['expected_keywords'])} "
                  f"({keyword_match*100:.0f}%)")
            
            if keyword_match < 0.3:
                print(f"  ⚠️  Low keyword match (expected: {test['expected_keywords']})")
            
            # Test LLM generation (optional, can be skipped to save costs)
            if not skip_llm:
                context, sources = format_context(results)
                
                start_time = time.time()
                answer, cost_info, model = query_llm(
                    test['query'], context, MODEL_DEFAULT, method, len(results)
                )
                llm_time = time.time() - start_time
                
                if answer.startswith("Error"):
                    print(f"  ❌ LLM error: {answer}")
                    return False
                
                print(f"  ✅ LLM response generated ({model})")
                print(f"  ⏱️  LLM time: {llm_time:.2f}s")
                print(f"  💰 {cost_info}")
                
                # Check if answer contains any expected keywords
                answer_lower = answer.lower()
                answer_keywords = [k for k in test['expected_keywords'] if k.lower() in answer_lower]
                if answer_keywords:
                    print(f"  📝 Keywords in answer: {', '.join(answer_keywords[:3])}")
            
            self.results.append({
                "name": test['name'],
                "query": test['query'],
                "success": True,
                "sources": len(results),
                "method": method
            })
            
            return True
            
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.results.append({
                "name": test['name'],
                "query": test['query'],
                "success": False,
                "error": str(e)
            })
            return False
    
    def _print_summary(self):
        """Print test summary"""
        print()
        print("=" * 70)
        print("📊 Test Summary")
        print("=" * 70)
        print(f"Passed: {self.passed}/{len(TEST_QUERIES)}")
        print(f"Failed: {self.failed}/{len(TEST_QUERIES)}")
        
        if self.failed == 0:
            print()
            print("🎉 All tests passed! System is ready.")
        else:
            print()
            print("⚠️  Some tests failed. Check output above.")
            print()
            print("Failed tests:")
            for r in self.results:
                if not r['success']:
                    print(f"  - {r['name']}: {r.get('error', 'Unknown error')}")
    
    def run_quick_check(self):
        """Quick check with 3 essential queries (no LLM)"""
        quick_tests = TEST_QUERIES[:3]
        
        print("⚡ Quick Health Check (3 queries, no LLM)")
        print("=" * 60)
        
        all_passed = True
        for test in quick_tests:
            print(f"\n• {test['name']}: \"{test['query'][:50]}...\"")
            
            try:
                results, method = hybrid_search(test['query'], top_k=3, enable_hybrid=True)
                
                if results:
                    print(f"  ✅ {len(results)} sources ({method})")
                else:
                    print(f"  ❌ No results")
                    all_passed = False
                    
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                all_passed = False
        
        print()
        if all_passed:
            print("🎉 Quick check passed!")
        else:
            print("⚠️  Quick check failed - investigate before going live")
        
        return all_passed


def main():
    """Run tests based on command line arguments"""
    tester = QueryTester()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--quick":
            success = tester.run_quick_check()
        elif sys.argv[1] == "--no-llm":
            success = tester.run_all_tests(skip_llm=True)
        else:
            print("Usage: python tests/test_queries.py [OPTION]")
            print()
            print("Options:")
            print("  --quick     Quick check (3 queries, no LLM)")
            print("  --no-llm    Full test without LLM calls (saves costs)")
            print("  (none)      Full test with LLM")
            sys.exit(1)
    else:
        print("Note: Running with LLM calls (costs ~$0.01)")
        print("Use --no-llm to skip LLM generation")
        print()
        success = tester.run_all_tests(skip_llm=False)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
