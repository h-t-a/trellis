"""vMF Hyperspherical Vector vs BM25 Baseline Retrieval Benchmark ([REQ-TRL-29]).

Evaluates retrieval precision, Mean Reciprocal Rank (MRR), and Recall@K across the
canonical Trellis engineering standards corpus without external dependencies.
"""

from __future__ import annotations

import math
import unittest
from pathlib import Path
from typing import Any

from trellis_mcp.knowledge import (
    _build_tfidf_vectors,
    _collect_corpus_chunks,
    _cosine_sparse,
    _tokenize,
    _vectorize_query,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


class BM25Index:
    """Standard Okapi BM25 implementation for lexical keyword search benchmark ([REQ-TRL-29])."""

    def __init__(self, corpus: list[str], k1: float = 1.5, b: float = 0.75) -> None:
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_tokens: list[list[str]] = [_tokenize(doc) for doc in corpus]
        self.doc_lens: list[int] = [len(tokens) for tokens in self.doc_tokens]
        self.avg_doc_len = sum(self.doc_lens) / max(1, self.corpus_size)

        # Document frequencies
        self.df: dict[str, int] = {}
        for tokens in self.doc_tokens:
            for term in set(tokens):
                self.df[term] = self.df.get(term, 0) + 1

        # Inverse document frequency
        self.idf: dict[str, float] = {}
        for term, freq in self.df.items():
            self.idf[term] = math.log(((self.corpus_size - freq + 0.5) / (freq + 0.5)) + 1.0)

    def score(self, query: str) -> list[float]:
        q_tokens = _tokenize(query)
        scores = [0.0] * self.corpus_size
        for term in q_tokens:
            if term not in self.idf:
                continue
            term_idf = self.idf[term]
            for doc_idx, tokens in enumerate(self.doc_tokens):
                tf = tokens.count(term)
                if tf == 0:
                    continue
                doc_len = self.doc_lens[doc_idx]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / max(1.0, self.avg_doc_len)))
                scores[doc_idx] += term_idf * (numerator / denominator)
        return scores


# Benchmark question set targeting canonical standards
BENCHMARK_QUERIES: list[dict[str, Any]] = [
    {
        "query": "Root-cause analysis 9-step workflow and PII redaction",
        "target_keywords": ["rca-playbook", "rca"],
    },
    {
        "query": "Story-level Definition of Done and testing gates",
        "target_keywords": ["definition-of-done", "dod"],
    },
    {
        "query": "Little's Law concurrency and SLA latency percentiles",
        "target_keywords": ["performance-sla", "complexity-and-performance"],
    },
    {
        "query": "Zero secrets policy and API key handling",
        "target_keywords": ["security-baseline"],
    },
    {
        "query": "AI boundary Tier 1 Tier 2 Tier 3 autonomy boundaries",
        "target_keywords": ["ai-boundary"],
    },
    {
        "query": "Conventional Commits format and commit message rules",
        "target_keywords": ["git-convention"],
    },
    {
        "query": "Data classification tiers public internal confidential restricted",
        "target_keywords": ["data-classification"],
    },
    {
        "query": "Quota efficiency token budget and cost control",
        "target_keywords": ["quota-efficiency"],
    },
    {
        "query": "Algorithmic Big-O and I/O round trips",
        "target_keywords": ["complexity-and-performance"],
    },
    {
        "query": "Testing standard failing tests first and REQ tags",
        "target_keywords": ["testing-standard"],
    },
    {
        "query": "Multi-AI routing policy and on-prem residency",
        "target_keywords": ["ai-boundary", "ai-bom"],
    },
    {
        "query": "Trellis MCP server authentication and bearer tokens",
        "target_keywords": ["security-baseline", "deployment-guide"],
    },
    {
        "query": "Fast root cause analysis and post-mortem template",
        "target_keywords": ["rca-playbook"],
    },
    {
        "query": "Release-level Definition of Done and rollback plan",
        "target_keywords": ["definition-of-done"],
    },
    {
        "query": "Luhn PAN and credit card number detection",
        "target_keywords": ["security-baseline", "data-classification"],
    },
    {
        "query": "Cross-device skill mirroring and Antigravity parity",
        "target_keywords": ["definition-of-done", "documentation-standard"],
    },
    {
        "query": "Performance SLA sustained load acceptance testing",
        "target_keywords": ["performance-sla"],
    },
    {
        "query": "Micro-spec 4-section format for Class M tasks",
        "target_keywords": ["definition-of-done"],
    },
    {
        "query": "Approved MCP servers and least privilege scopes",
        "target_keywords": ["ai-boundary", "security-baseline"],
    },
    {
        "query": "Zero weakened assertions and test integrity",
        "target_keywords": ["testing-standard"],
    },
    {
        "query": "Myanmar NRC and phone number redaction",
        "target_keywords": ["security-baseline", "data-classification"],
    },
    {
        "query": "Token efficiency and context window management",
        "target_keywords": ["quota-efficiency"],
    },
    {
        "query": "HttpOnly session cookies and CSRF protection",
        "target_keywords": ["security-baseline"],
    },
    {
        "query": "vMF hyperspherical search and kappa confidence",
        "target_keywords": ["quota-efficiency", "testing-standard"],
    },
    {
        "query": "Code review gates before opening Pull Request",
        "target_keywords": ["definition-of-done"],
    },
]


def run_standards_benchmark(repo_root: Path) -> dict[str, Any]:
    """Execute retrieval benchmark over standards chunks comparing vMF and BM25 ([REQ-TRL-29])."""
    chunks = _collect_corpus_chunks(repo_root)
    if not chunks:
        raise ValueError(f"No corpus chunks found under {repo_root}")

    doc_texts = [c["text"] for c in chunks]

    # 1. Build vMF TF-IDF vectors
    vmf_vectors, vmf_idf, _ = _build_tfidf_vectors(doc_texts)

    # 2. Build BM25 Index
    bm25 = BM25Index(doc_texts)

    vmf_rr_list: list[float] = []
    bm25_rr_list: list[float] = []
    vmf_hits_at_3 = 0
    bm25_hits_at_3 = 0

    for item in BENCHMARK_QUERIES:
        query = item["query"]
        targets = [t.lower() for t in item["target_keywords"]]

        # Evaluate vMF / cosine
        q_vec = _vectorize_query(query, vmf_idf)
        vmf_scores = [_cosine_sparse(q_vec, d_vec) for d_vec in vmf_vectors]
        vmf_ranked = sorted(range(len(chunks)), key=lambda i: vmf_scores[i], reverse=True)

        vmf_rank = 0
        for rank, doc_idx in enumerate(vmf_ranked[:10], start=1):
            source = str(chunks[doc_idx].get("source", "")).lower()
            text = chunks[doc_idx]["text"].lower()
            if any(t in source or t in text for t in targets):
                vmf_rank = rank
                break
        vmf_rr = (1.0 / vmf_rank) if vmf_rank > 0 else 0.0
        vmf_rr_list.append(vmf_rr)
        if 0 < vmf_rank <= 3:
            vmf_hits_at_3 += 1

        # Evaluate BM25
        bm25_scores = bm25.score(query)
        bm25_ranked = sorted(range(len(chunks)), key=lambda i: bm25_scores[i], reverse=True)

        bm25_rank = 0
        for rank, doc_idx in enumerate(bm25_ranked[:10], start=1):
            source = str(chunks[doc_idx].get("source", "")).lower()
            text = chunks[doc_idx]["text"].lower()
            if any(t in source or t in text for t in targets):
                bm25_rank = rank
                break
        bm25_rr = (1.0 / bm25_rank) if bm25_rank > 0 else 0.0
        bm25_rr_list.append(bm25_rr)
        if 0 < bm25_rank <= 3:
            bm25_hits_at_3 += 1

    q_count = len(BENCHMARK_QUERIES)
    return {
        "query_count": q_count,
        "corpus_chunks": len(chunks),
        "vmf_mrr": sum(vmf_rr_list) / q_count,
        "bm25_mrr": sum(bm25_rr_list) / q_count,
        "vmf_recall_at_3": vmf_hits_at_3 / q_count,
        "bm25_recall_at_3": bm25_hits_at_3 / q_count,
    }


class TestVmfBm25Benchmark(unittest.TestCase):
    """Regression test suite for retrieval benchmark execution ([REQ-TRL-29])."""

    def test_standards_retrieval_benchmark_executes_and_meets_quality_thresholds(self) -> None:
        """[REQ-TRL-29] Verify standards corpus benchmark passes with >=20 queries and MRR > 0.40."""
        metrics = run_standards_benchmark(REPO_ROOT)
        self.assertGreaterEqual(metrics["query_count"], 20)
        self.assertGreater(metrics["vmf_mrr"], 0.40)
        self.assertGreater(metrics["bm25_mrr"], 0.40)
        self.assertGreaterEqual(metrics["vmf_recall_at_3"], 0.50)
        self.assertGreaterEqual(metrics["bm25_recall_at_3"], 0.50)


if __name__ == "__main__":
    unittest.main()
