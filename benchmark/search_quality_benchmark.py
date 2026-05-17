#!/usr/bin/env python3
"""Search Quality Benchmark for maru-deep-pro-search MCP tools.

Evaluates search result quality using TREC-standard IR metrics:
- Precision@K, Recall@K
- NDCG@K (Normalized Discounted Cumulative Gain)
- MRR (Mean Reciprocal Rank)
- Response time and engine failover rate

Inspired by:
- SWE-bench (Princeton/Stanford)
- TREC evaluation methodology
- MTEB Leaderboard metrics

Zero API keys required. Uses domain-based ground truth.
"""

from __future__ import annotations

import asyncio
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maru_deep_pro_search.engines.registry import SearchEngineRegistry

# ── Ground Truth Dataset ──────────────────────────────────────────
# Each query has a list of relevant domain patterns.
# A result URL is "relevant" if it matches ANY pattern.

GROUND_TRUTH: dict[str, list[str]] = {
    "FastAPI middleware documentation": [
        "fastapi.tiangolo.com",
    ],
    "urllib3 CVE-2026-44431 security advisory": [
        "github.com/urllib3/urllib3",
        "nvd.nist.gov",
        "cve.mitre.org",
    ],
    "Python asyncio semaphore example": [
        "docs.python.org",
    ],
    "sentence-transformers vs OpenAI embeddings benchmark": [
        "huggingface.co",
        "arxiv.org",
        "openai.com",
    ],
    "Python latest version 2026": [
        "python.org",
        "pypi.org",
    ],
    "pydantic v2 migration guide": [
        "docs.pydantic.dev",
    ],
    "httpx async client tutorial": [
        "python-httpx.org",
    ],
    "pytest asyncio fixture best practices": [
        "docs.pytest.org",
    ],
    "scrapling fetchers documentation": [
        "github.com/D4Vinci/Scrapling",
        "scrapling.readthedocs.io",
    ],
    "mcp model context protocol specification": [
        "modelcontextprotocol.io",
        "github.com/modelcontextprotocol",
    ],
}

# Answer-engine style queries (Korean consumer / price / recommendations)
ANSWER_GROUND_TRUTH: dict[str, list[str]] = {
    "갤럭시 중고폰 최신 시세 추천 2026": [
        "danawa.com",
        "naver.com",
        "coupang.com",
        "joongna.com",
    ],
    "아이폰 15 프로 중고 가격 비교": [
        "danawa.com",
        "naver.com",
        "apple.com",
    ],
    "서울 맛집 추천 강남역 2026": [
        "naver.com",
        "mangoplate.com",
        "diningcode.com",
    ],
}


@dataclass
class QueryResult:
    query: str
    engine: str
    results: list[dict[str, str]]  # [{"title": ..., "url": ..., "score": ...}]
    duration_ms: float
    fallback_used: bool


@dataclass
class MetricResult:
    query: str
    precision_at_5: float
    precision_at_10: float
    recall_at_10: float
    ndcg_at_5: float
    ndcg_at_10: float
    mrr: float
    duration_ms: float
    fallback_used: bool
    relevant_found: int
    total_relevant: int


def is_relevant(url: str, query: str) -> bool:
    patterns = GROUND_TRUTH.get(query) or ANSWER_GROUND_TRUTH.get(query, [])
    url_lower = url.lower()
    return any(pat.lower() in url_lower for pat in patterns)


def compute_precision_at_k(results: list[dict], query: str, k: int) -> float:
    if not results or k == 0:
        return 0.0
    top_k = results[:k]
    relevant = sum(1 for r in top_k if is_relevant(r.get("url", ""), query))
    return relevant / k


def compute_recall_at_k(results: list[dict], query: str, k: int) -> float:
    if not results:
        return 0.0
    total_relevant = sum(1 for r in results if is_relevant(r.get("url", ""), query))
    if total_relevant == 0:
        return 0.0
    top_k = results[:k]
    found = sum(1 for r in top_k if is_relevant(r.get("url", ""), query))
    return found / total_relevant


def compute_dcg(relevances: list[float], k: int) -> float:
    dcg = 0.0
    for i, rel in enumerate(relevances[:k], start=1):
        dcg += rel / math.log2(i + 1)
    return dcg


def compute_ndcg_at_k(results: list[dict], query: str, k: int) -> float:
    if not results:
        return 0.0
    # Binary relevance: 1.0 if relevant, 0.0 otherwise
    relevances = [1.0 if is_relevant(r.get("url", ""), query) else 0.0 for r in results]
    dcg = compute_dcg(relevances, k)
    ideal_relevances = sorted(relevances, reverse=True)
    idcg = compute_dcg(ideal_relevances, k)
    return dcg / idcg if idcg > 0 else 0.0


def compute_mrr(results: list[dict], query: str) -> float:
    for i, r in enumerate(results, start=1):
        if is_relevant(r.get("url", ""), query):
            return 1.0 / i
    return 0.0


async def run_single_query_web_search(
    query: str, engine_name: str = "duckduckgo_lite", max_results: int = 10
) -> QueryResult:
    start = time.monotonic()
    fallback_used = False
    results: list[dict] = []

    try:
        engine = SearchEngineRegistry.create(engine_name)
        raw_results = await engine.search(query, max_results=max_results)
        results = [
            {
                "title": r.title,
                "url": r.url,
                "score": getattr(r, "score", 0.0),
            }
            for r in raw_results
        ]
    except Exception:
        fallback_used = True
        try:
            fallback = SearchEngineRegistry.recommend_engines(query, exclude=[engine_name])[0]
            raw_results = await fallback.search(query, max_results=max_results)
            results = [
                {
                    "title": r.title,
                    "url": r.url,
                    "score": getattr(r, "score", 0.0),
                }
                for r in raw_results
            ]
        except Exception:
            results = []

    duration_ms = (time.monotonic() - start) * 1000
    return QueryResult(
        query=query,
        engine=engine_name,
        results=results,
        duration_ms=duration_ms,
        fallback_used=fallback_used,
    )


async def run_single_query_deep_research(query: str, max_results: int = 10) -> QueryResult:
    """Run deep_research which uses multi-engine + BM25 + authority ranking."""
    start = time.monotonic()
    results: list[dict] = []

    try:
        from maru_deep_pro_search.research.deep import deep_research

        result = await deep_research(
            query=query,
            engine="duckduckgo_lite",
            max_sources=max_results,
            expand_queries=False,
        )
        # ResearchResult has .sources: list[CitedSource] with .url
        unique_urls = []
        seen = set()
        for src in result.sources:
            if src.url not in seen:
                seen.add(src.url)
                unique_urls.append(src.url)
        results = [
            {
                "title": getattr(result.sources[i], "title", f"Result {i + 1}"),
                "url": url,
                "score": getattr(result.sources[i], "relevance_score", 0.0),
            }
            for i, url in enumerate(unique_urls[:max_results])
        ]
    except Exception as exc:
        print(f"deep_research error: {exc}")
        results = []

    duration_ms = (time.monotonic() - start) * 1000
    return QueryResult(
        query=query,
        engine="deep_research",
        results=results,
        duration_ms=duration_ms,
        fallback_used=False,
    )


def evaluate_query(result: QueryResult) -> MetricResult:
    all_results = result.results
    total_relevant = sum(1 for r in all_results if is_relevant(r.get("url", ""), result.query))

    return MetricResult(
        query=result.query,
        precision_at_5=compute_precision_at_k(all_results, result.query, 5),
        precision_at_10=compute_precision_at_k(all_results, result.query, 10),
        recall_at_10=compute_recall_at_k(all_results, result.query, 10),
        ndcg_at_5=compute_ndcg_at_k(all_results, result.query, 5),
        ndcg_at_10=compute_ndcg_at_k(all_results, result.query, 10),
        mrr=compute_mrr(all_results, result.query),
        duration_ms=result.duration_ms,
        fallback_used=result.fallback_used,
        relevant_found=sum(
            1 for r in all_results[:10] if is_relevant(r.get("url", ""), result.query)
        ),
        total_relevant=total_relevant,
    )


def print_report(metrics: list[MetricResult]) -> None:
    print("\n" + "=" * 80)
    print("SEARCH QUALITY BENCHMARK REPORT")
    print("=" * 80)

    total = len(metrics)
    avg_p5 = sum(m.precision_at_5 for m in metrics) / total
    avg_p10 = sum(m.precision_at_10 for m in metrics) / total
    avg_r10 = sum(m.recall_at_10 for m in metrics) / total
    avg_ndcg5 = sum(m.ndcg_at_5 for m in metrics) / total
    avg_ndcg10 = sum(m.ndcg_at_10 for m in metrics) / total
    avg_mrr = sum(m.mrr for m in metrics) / total
    avg_time = sum(m.duration_ms for m in metrics) / total
    fallback_rate = sum(1 for m in metrics if m.fallback_used) / total * 100

    print(f"\n{'Metric':<25} {'Average':>10} {'Target':>10} {'Status':>8}")
    print("-" * 55)

    def status(val, target):
        return "PASS" if val >= target else "FAIL"

    print(f"{'Precision@5':<25} {avg_p5:>10.3f} {'0.400':>10} {status(avg_p5, 0.4):>8}")
    print(f"{'Precision@10':<25} {avg_p10:>10.3f} {'0.350':>10} {status(avg_p10, 0.35):>8}")
    print(f"{'Recall@10':<25} {avg_r10:>10.3f} {'0.500':>10} {status(avg_r10, 0.5):>8}")
    print(f"{'NDCG@5':<25} {avg_ndcg5:>10.3f} {'0.500':>10} {status(avg_ndcg5, 0.5):>8}")
    print(f"{'NDCG@10':<25} {avg_ndcg10:>10.3f} {'0.450':>10} {status(avg_ndcg10, 0.45):>8}")
    print(f"{'MRR':<25} {avg_mrr:>10.3f} {'0.500':>10} {status(avg_mrr, 0.5):>8}")
    print(
        f"{'Avg Response Time (ms)':<25} {avg_time:>10.0f} {'3000':>10} {status(3000 / avg_time if avg_time else 1, 1):>8}"
    )
    print(
        f"{'Fallback Rate (%)':<25} {fallback_rate:>10.1f} {'20.0':>10} {status(20 / fallback_rate if fallback_rate else 1, 1):>8}"
    )

    print(f"\n{'Query':<45} {'P@5':>6} {'NDCG@5':>8} {'MRR':>6} {'ms':>6} {'FB':>3}")
    print("-" * 80)
    for m in metrics:
        fb = "Y" if m.fallback_used else "N"
        print(
            f"{m.query[:44]:<45} {m.precision_at_5:>6.2f} {m.ndcg_at_5:>8.3f} {m.mrr:>6.2f} {m.duration_ms:>6.0f} {fb:>3}"
        )

    # Save JSON
    report_path = Path("benchmark/search_quality_report.json")
    report_path.write_text(
        json.dumps(
            {
                "summary": {
                    "queries": total,
                    "precision_at_5": avg_p5,
                    "precision_at_10": avg_p10,
                    "recall_at_10": avg_r10,
                    "ndcg_at_5": avg_ndcg5,
                    "ndcg_at_10": avg_ndcg10,
                    "mrr": avg_mrr,
                    "avg_response_ms": avg_time,
                    "fallback_rate_pct": fallback_rate,
                },
                "results": [asdict(m) for m in metrics],
            },
            indent=2,
        )
    )
    print(f"\nReport saved: {report_path}")


async def run_benchmark_mode(queries: list[str], mode: str) -> list[MetricResult]:
    print(f"\n{'=' * 60}")
    print(f"MODE: {mode.upper()}")
    print(f"{'=' * 60}")

    query_results: list[QueryResult] = []
    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] {query[:50]}...", end=" ", flush=True)
        if mode == "deep_research":
            result = await run_single_query_deep_research(query)
        else:
            # Use bing for web_search to avoid duckduckgo circuit breaker
            result = await run_single_query_web_search(query, engine_name="bing")
        query_results.append(result)
        print(f"({len(result.results)} results, {result.duration_ms:.0f}ms)")

    return [evaluate_query(r) for r in query_results]


async def main() -> int:
    queries = list(GROUND_TRUTH.keys())
    print(f"Running search quality benchmark with {len(queries)} queries...")
    print("Comparing web_search (single engine) vs deep_research (multi-engine)")

    # Run both modes (use bing for web_search to avoid duckduckgo circuit breaker)
    web_metrics = await run_benchmark_mode(queries, "web_search")
    # Wait for duckduckgo circuit breaker recovery before deep_research
    print("\n  [recovery] Waiting 5s for circuit breaker recovery...")
    await asyncio.sleep(5)
    deep_metrics = await run_benchmark_mode(queries, "deep_research")

    print("\n" + "=" * 80)
    print("COMPARATIVE REPORT: web_search vs deep_research")
    print("=" * 80)

    def summarize(metrics: list[MetricResult]) -> dict[str, float]:
        n = len(metrics)
        return {
            "precision_at_5": sum(m.precision_at_5 for m in metrics) / n,
            "precision_at_10": sum(m.precision_at_10 for m in metrics) / n,
            "recall_at_10": sum(m.recall_at_10 for m in metrics) / n,
            "ndcg_at_5": sum(m.ndcg_at_5 for m in metrics) / n,
            "ndcg_at_10": sum(m.ndcg_at_10 for m in metrics) / n,
            "mrr": sum(m.mrr for m in metrics) / n,
            "avg_time_ms": sum(m.duration_ms for m in metrics) / n,
        }

    web = summarize(web_metrics)
    deep = summarize(deep_metrics)

    print(f"\n{'Metric':<25} {'web_search':>12} {'deep_research':>15} {'Delta':>10}")
    print("-" * 65)
    for key in web:
        delta = deep[key] - web[key]
        delta_str = f"+{delta:.3f}" if delta >= 0 else f"{delta:.3f}"
        print(f"{key:<25} {web[key]:>12.3f} {deep[key]:>15.3f} {delta_str:>10}")

    # Save comparative report
    report_path = Path("benchmark/search_quality_report.json")
    report_path.write_text(
        json.dumps(
            {
                "web_search": {"summary": web, "results": [asdict(m) for m in web_metrics]},
                "deep_research": {"summary": deep, "results": [asdict(m) for m in deep_metrics]},
            },
            indent=2,
        )
    )
    print(f"\nReport saved: {report_path}")

    answer_queries = list(ANSWER_GROUND_TRUTH.keys())
    if answer_queries:
        print(f"\n{'=' * 80}")
        print(f"ANSWER-MODE QUERIES ({len(answer_queries)} Korean consumer / price queries)")
        print(f"{'=' * 80}")
        print("\n  [recovery] Waiting 5s before answer-mode benchmark...")
        await asyncio.sleep(5)
        answer_metrics = await run_benchmark_mode(answer_queries, "deep_research")
        answer_summary = summarize(answer_metrics)
        print(f"\n{'Metric':<25} {'answer_pipeline':>15}")
        print("-" * 42)
        for key, val in answer_summary.items():
            print(f"{key:<25} {val:>15.3f}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
