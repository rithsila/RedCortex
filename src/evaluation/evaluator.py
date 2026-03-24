#!/usr/bin/env python3
"""
RedCortex Evaluation Framework
Measures retrieval and generation quality
"""
import os
import sys
import json
import time
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

os.chdir(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, 'src')

from rag_pipeline import hybrid_search, vector_search, query_llm, format_context, MODEL_DEFAULT


@dataclass
class TestCase:
    """Single test case for evaluation"""
    id: str
    query: str
    expected_topics: List[str]
    expected_pages: List[int]
    category: str
    difficulty: str


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality"""
    recall_at_5: float
    recall_at_10: float
    mrr: float
    precision_at_5: float
    keyword_match_rate: float
    avg_latency_ms: float


@dataclass
class GenerationMetrics:
    """Metrics for generation quality"""
    answer_completeness: float
    citation_accuracy: float
    avg_tokens: float
    avg_latency_ms: float


@dataclass
class EvaluationResult:
    """Complete evaluation results"""
    timestamp: str
    total_tests: int
    retrieval_metrics: RetrievalMetrics
    generation_metrics: GenerationMetrics


class RAGEvaluator:
    """RAG System Evaluator"""
    
    def __init__(self, test_cases: Optional[List[TestCase]] = None):
        self.test_cases = test_cases or self._load_default_tests()
    
    def _load_default_tests(self) -> List[TestCase]:
        """Load default test cases"""
        return [
            TestCase(
                id="user_mgmt_1",
                query="How do I create a new user in RHEL?",
                expected_topics=["useradd", "user", "create", "password"],
                expected_pages=[159, 160, 161],
                category="user_management",
                difficulty="easy"
            ),
            TestCase(
                id="services_1",
                query="How to start a service with systemctl?",
                expected_topics=["systemctl", "start", "service", "enable"],
                expected_pages=[312, 315, 316],
                category="services",
                difficulty="easy"
            ),
            TestCase(
                id="firewall_1",
                query="How to configure firewalld rich rules?",
                expected_topics=["firewalld", "firewall-cmd", "rich rules", "zone"],
                expected_pages=[508, 509, 510],
                category="networking",
                difficulty="medium"
            ),
            TestCase(
                id="ssh_1",
                query="How to set up SSH key authentication?",
                expected_topics=["ssh", "key", "authentication", "ssh-keygen"],
                expected_pages=[335, 336, 337],
                category="security",
                difficulty="medium"
            ),
            TestCase(
                id="selinux_1",
                query="What is SELinux and how to check its status?",
                expected_topics=["selinux", "getenforce", "sestatus", "enforcing"],
                expected_pages=[225, 226, 227],
                category="security",
                difficulty="medium"
            ),
            TestCase(
                id="permissions_1",
                query="How to use chmod to change file permissions?",
                expected_topics=["chmod", "permission", "rwx", "ugo"],
                expected_pages=[95, 96, 97],
                category="filesystem",
                difficulty="easy"
            ),
            TestCase(
                id="packages_1",
                query="How to install packages with dnf?",
                expected_topics=["dnf", "install", "package", "repository"],
                expected_pages=[185, 186, 187],
                category="packages",
                difficulty="easy"
            ),
            TestCase(
                id="disk_1",
                query="How to check disk space usage?",
                expected_topics=["df", "du", "disk", "filesystem"],
                expected_pages=[125, 126],
                category="storage",
                difficulty="easy"
            ),
            TestCase(
                id="network_1",
                query="How to configure network with nmcli?",
                expected_topics=["nmcli", "network", "connection", "interface"],
                expected_pages=[485, 486, 487],
                category="networking",
                difficulty="hard"
            ),
            TestCase(
                id="processes_1",
                query="How to manage processes with ps and kill?",
                expected_topics=["ps", "kill", "process", "signal"],
                expected_pages=[75, 76, 77],
                category="processes",
                difficulty="medium"
            )
        ]
    
    def evaluate_retrieval(self, use_hybrid: bool = True) -> RetrievalMetrics:
        """Evaluate retrieval quality"""
        print("\n🔍 Evaluating Retrieval...")
        print("=" * 60)
        
        recalls_at_5 = []
        recalls_at_10 = []
        mrrs = []
        precisions_at_5 = []
        keyword_matches = []
        latencies = []
        
        for i, test in enumerate(self.test_cases, 1):
            print(f"[{i}/{len(self.test_cases)}] {test.id}: {test.query[:50]}...")
            
            start_time = time.time()
            results, method = hybrid_search(test.query, top_k=10, enable_hybrid=use_hybrid)
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)
            
            if not results:
                recalls_at_5.append(0)
                recalls_at_10.append(0)
                mrrs.append(0)
                precisions_at_5.append(0)
                keyword_matches.append(0)
                continue
            
            # Calculate keyword match rate
            content_text = " ".join([r.content.lower() for r in results[:5]])
            matched_keywords = sum(1 for kw in test.expected_topics if kw.lower() in content_text)
            keyword_match_rate = matched_keywords / len(test.expected_topics)
            keyword_matches.append(keyword_match_rate)
            
            # Calculate recall
            retrieved_pages = [r.page_start for r in results]
            relevant_at_5 = len(set(test.expected_pages) & set(retrieved_pages[:5]))
            relevant_at_10 = len(set(test.expected_pages) & set(retrieved_pages[:10]))
            
            recall_5 = relevant_at_5 / len(test.expected_pages)
            recall_10 = relevant_at_10 / len(test.expected_pages)
            
            recalls_at_5.append(recall_5)
            recalls_at_10.append(recall_10)
            
            # Calculate MRR
            rank = None
            for i, page in enumerate(retrieved_pages, 1):
                if page in test.expected_pages:
                    rank = i
                    break
            
            mrr = 1.0 / rank if rank else 0
            mrrs.append(mrr)
            
            # Calculate precision at 5
            precision_5 = relevant_at_5 / 5
            precisions_at_5.append(precision_5)
            
            print(f"  Recall@5: {recall_5:.2f}, MRR: {mrr:.2f}, Keywords: {keyword_match_rate:.2f}")
        
        return RetrievalMetrics(
            recall_at_5=sum(recalls_at_5) / len(recalls_at_5),
            recall_at_10=sum(recalls_at_10) / len(recalls_at_10),
            mrr=sum(mrrs) / len(mrrs),
            precision_at_5=sum(precisions_at_5) / len(precisions_at_5),
            keyword_match_rate=sum(keyword_matches) / len(keyword_matches),
            avg_latency_ms=sum(latencies) / len(latencies)
        )
    
    def evaluate_generation(self, sample_size: int = 3) -> GenerationMetrics:
        """Evaluate generation quality"""
        print("\n🤖 Evaluating Generation (LLM calls)...")
        print("=" * 60)
        
        import random
        sample_tests = random.sample(self.test_cases, min(sample_size, len(self.test_cases)))
        
        completeness_scores = []
        citation_scores = []
        token_counts = []
        latencies = []
        
        for i, test in enumerate(sample_tests, 1):
            print(f"[{i}/{len(sample_tests)}] {test.id}: {test.query[:50]}...")
            
            results, method = hybrid_search(test.query, top_k=5, enable_hybrid=True)
            if not results:
                continue
            
            context, sources = format_context(results)
            
            start_time = time.time()
            answer, cost_info, model = query_llm(test.query, context, MODEL_DEFAULT, method, len(results))
            latency_ms = (time.time() - start_time) * 1000
            latencies.append(latency_ms)
            
            tokens = 0
            if "Tokens:" in cost_info:
                try:
                    tokens = int(cost_info.split("Tokens:")[1].split()[0])
                except:
                    pass
            token_counts.append(tokens)
            
            # Check completeness
            answer_lower = answer.lower()
            matched = sum(1 for kw in test.expected_topics if kw.lower() in answer_lower)
            completeness = matched / len(test.expected_topics)
            completeness_scores.append(completeness)
            
            # Check citation accuracy
            import re
            pages_mentioned = re.findall(r'Page (\d+)', answer)
            pages_mentioned = [int(p) for p in pages_mentioned]
            
            if pages_mentioned:
                relevant_citations = len(set(pages_mentioned) & set(test.expected_pages))
                citation_acc = relevant_citations / len(pages_mentioned)
            else:
                citation_acc = 0
            citation_scores.append(citation_acc)
            
            print(f"  Completeness: {completeness:.2f}, Citations: {citation_acc:.2f}, Tokens: {tokens}")
        
        return GenerationMetrics(
            answer_completeness=sum(completeness_scores) / len(completeness_scores) if completeness_scores else 0,
            citation_accuracy=sum(citation_scores) / len(citation_scores) if citation_scores else 0,
            avg_tokens=sum(token_counts) / len(token_counts) if token_counts else 0,
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0
        )
    
    def run_evaluation(self, evaluate_gen: bool = False, save_results: bool = True) -> EvaluationResult:
        """Run complete evaluation"""
        print("\n" + "=" * 60)
        print("🧪 RedCortex RAG Evaluation Framework")
        print("=" * 60)
        print(f"Tests: {len(self.test_cases)}")
        print(f"Generation eval: {'Yes' if evaluate_gen else 'No'}")
        print("")
        
        retrieval_metrics = self.evaluate_retrieval()
        
        generation_metrics = None
        if evaluate_gen:
            generation_metrics = self.evaluate_generation()
        else:
            generation_metrics = GenerationMetrics(0, 0, 0, 0)
        
        result = EvaluationResult(
            timestamp=datetime.now().isoformat(),
            total_tests=len(self.test_cases),
            retrieval_metrics=retrieval_metrics,
            generation_metrics=generation_metrics
        )
        
        self._print_summary(result)
        
        if save_results:
            self._save_results(result)
        
        return result
    
    def _print_summary(self, result: EvaluationResult):
        """Print evaluation summary"""
        print("\n" + "=" * 60)
        print("📊 Evaluation Summary")
        print("=" * 60)
        
        print("\n🔍 Retrieval Metrics:")
        print(f"  Recall@5:        {result.retrieval_metrics.recall_at_5:.3f}")
        print(f"  Recall@10:       {result.retrieval_metrics.recall_at_10:.3f}")
        print(f"  MRR:             {result.retrieval_metrics.mrr:.3f}")
        print(f"  Precision@5:     {result.retrieval_metrics.precision_at_5:.3f}")
        print(f"  Keyword Match:   {result.retrieval_metrics.keyword_match_rate:.3f}")
        print(f"  Avg Latency:     {result.retrieval_metrics.avg_latency_ms:.0f}ms")
        
        if result.generation_metrics.avg_tokens > 0:
            print("\n🤖 Generation Metrics:")
            print(f"  Completeness:    {result.generation_metrics.answer_completeness:.3f}")
            print(f"  Citation Acc:    {result.generation_metrics.citation_accuracy:.3f}")
            print(f"  Avg Tokens:      {result.generation_metrics.avg_tokens:.0f}")
            print(f"  Avg Latency:     {result.generation_metrics.avg_latency_ms:.0f}ms")
        
        overall = (
            result.retrieval_metrics.recall_at_5 * 0.4 +
            result.retrieval_metrics.mrr * 0.3 +
            result.retrieval_metrics.keyword_match_rate * 0.3
        )
        print(f"\n🏆 Overall Score: {overall:.3f}")
        
        if overall >= 0.7:
            print("✅ System performing well!")
        elif overall >= 0.5:
            print("⚠️  System performing adequately")
        else:
            print("❌ System needs improvement")
    
    def _save_results(self, result: EvaluationResult):
        """Save results to file"""
        from pathlib import Path
        
        output_dir = Path("data/evaluation")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output_dir / f"evaluation_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": result.timestamp,
                "total_tests": result.total_tests,
                "retrieval_metrics": asdict(result.retrieval_metrics),
                "generation_metrics": asdict(result.generation_metrics)
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {filename}")


def main():
    """CLI for evaluation"""
    import argparse
    
    parser = argparse.ArgumentParser(description="RedCortex RAG Evaluation")
    parser.add_argument("--generation", action="store_true", help="Evaluate generation")
    parser.add_argument("--no-save", action="store_true", help="Don't save results")
    parser.add_argument("--compare", action="store_true", help="Compare hybrid vs vector-only")
    
    args = parser.parse_args()
    
    evaluator = RAGEvaluator()
    
    if args.compare:
        print("\n📊 Comparing Hybrid vs Vector-Only Search")
        print("=" * 60)
        
        print("\n🔍 Hybrid Search (BM25 + Vector):")
        hybrid_metrics = evaluator.evaluate_retrieval(use_hybrid=True)
        
        print("\n🔍 Vector-Only Search:")
        vector_metrics = evaluator.evaluate_retrieval(use_hybrid=False)
        
        print("\n" + "=" * 60)
        print("📈 Comparison Summary")
        print("=" * 60)
        print(f"{'Metric':<20} {'Hybrid':>12} {'Vector':>12} {'Improvement':>12}")
        print("-" * 60)
        
        metrics = [
            ("Recall@5", hybrid_metrics.recall_at_5, vector_metrics.recall_at_5),
            ("MRR", hybrid_metrics.mrr, vector_metrics.mrr),
            ("Keyword Match", hybrid_metrics.keyword_match_rate, vector_metrics.keyword_match_rate),
        ]
        
        for name, hybrid_val, vector_val in metrics:
            improvement = ((hybrid_val - vector_val) / vector_val * 100) if vector_val > 0 else 0
            print(f"{name:<20} {hybrid_val:>12.3f} {vector_val:>12.3f} {improvement:>11.1f}%")
    else:
        evaluator.run_evaluation(
            evaluate_gen=args.generation,
            save_results=not args.no_save
        )


if __name__ == "__main__":
    main()
