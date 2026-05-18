"""Intelligent ranking engine for multi-source search results.

Combines BM25 relevance scoring with metadata-based quality signals
to produce Perplexity-level result ranking."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from ..config import DEFAULT_CONFIG
from ..engines.base import ContentType, PageContent, SearchResult
from ..research.expander import extract_keywords
from ..utils.url import get_domain, is_authority_domain, normalize_url
from .signals import SourceSignals, source_signals

logger = logging.getLogger(__name__)

# Metadata scoring weights
_AUTHORITY_BOOST = 2.0
_FRESHNESS_BOOST = 1.5
_DOCS_TYPE_BOOST = 1.5
_ARTICLE_TYPE_BOOST = 1.0
_CODE_TYPE_BOOST = 0.8
_FORUM_TYPE_BOOST = 0.6
_CROSS_ENGINE_BOOST = 0.5
_SNIPPET_QUALITY_BOOST = 1.0
_POSITION_DECAY = 0.1
_RRF_K = 60


@dataclass
class RankedResult:
    """A search result with comprehensive ranking metadata."""

    result: SearchResult
    bm25_score: float = 0.0
    metadata_score: float = 0.0
    semantic_score: float = 0.0
    final_score: float = 0.0
    citation_id: int = 0


def _compute_bm25_scores(query: str, results: list[SearchResult]) -> dict[str, float]:
    """Compute BM25 scores for results against the query."""
    try:
        from rank_bm25 import BM25Okapi
    except ImportError:
        logger.debug("rank-bm25 not available, skipping BM25 scoring")
        return {normalize_url(r.url): 0.0 for r in results}

    if not results:
        return {}

    # Tokenize query and documents
    query_tokens = extract_keywords(query)
    if not query_tokens:
        query_tokens = query.lower().split()

    corpus = []
    url_map = {}
    for r in results:
        doc = f"{r.title} {r.snippet} {r.domain}".lower()
        tokens = extract_keywords(doc) or doc.split()
        corpus.append(tokens)
        url_map[normalize_url(r.url)] = len(corpus) - 1

    try:
        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)
    except Exception as exc:
        logger.warning("BM25 scoring failed: %s", exc)
        return {normalize_url(r.url): 0.0 for r in results}

    return {normalize_url(r.url): scores[url_map.get(normalize_url(r.url), 0)] for r in results}


# Inline authority/spam lists to avoid circular imports
_TIER1_DOMAINS = {
    "github.com",
    "gitlab.com",
    "stackoverflow.com",
    "docs.python.org",
    "developer.mozilla.org",
    "react.dev",
    "nextjs.org",
    "nodejs.org",
    "go.dev",
    "pkg.go.dev",
    "doc.rust-lang.org",
    "learn.microsoft.com",
    "postgresql.org",
    "kubernetes.io",
    "docs.djangoproject.com",
    "vuejs.org",
    "svelte.dev",
    "angular.io",
    "astro.build",
    "remix.run",
    "nuxt.com",
    "trpc.io",
    "prisma.io",
    "orm.drizzle.team",
    "turso.tech",
    "neon.tech",
    "planetscale.com",
    "vercel.com",
    "cloudflare.com",
    "workers.cloudflare.com",
    "aws.amazon.com",
    "openai.com",
    "platform.openai.com",
    "anthropic.com",
    "claude.ai",
    "docs.anthropic.com",
    "ai.google.dev",
    "arxiv.org",
    "semanticscholar.org",
    "scholar.google.com",
    "ieee.org",
    "acm.org",
    "usenix.org",
    "npmjs.com",
    "pypi.org",
    "crates.io",
    "huggingface.co",
    "paperswithcode.com",
}

_SPAM_DOMAINS_LOCAL = {
    "nucamp.co",
    "pillaiinfotech.com",
    "indiit.com",
    "cloudbuzz.ai",
    "acemindtech.com",
    "solutionsuggest.com",
    "geeksforgeeks.org",
    "tutorialspoint.com",
    "javatpoint.com",
    "w3schools.com",
    "simplilearn.com",
    "intellipaat.com",
    "edureka.co",
}


def _query_freshness_boost(query: str, result: SearchResult) -> float:
    """Boost when snippet/URL mentions a year explicitly requested in the query."""
    years = re.findall(r"20\d{2}", query)
    if not years:
        return 0.0
    haystack = f"{result.url} {result.snippet or ''}".lower()
    if any(year in haystack for year in years):
        return _FRESHNESS_BOOST * DEFAULT_CONFIG.freshness_weight
    return 0.0


def _compute_rrf_scores(
    engine_results: dict[str, list[SearchResult]],
    search_runs: list[tuple[str, list[SearchResult]]] | None = None,
) -> dict[str, float]:
    """Reciprocal rank fusion across independent SERP runs."""
    scores: dict[str, float] = {}
    runs = search_runs if search_runs is not None else list(engine_results.items())
    for _run_id, results in runs:
        for rank, result in enumerate(results, start=1):
            norm = normalize_url(result.url)
            scores[norm] = scores.get(norm, 0.0) + 1.0 / (_RRF_K + rank)
    return scores


def _score_metadata(
    result: SearchResult,
    query: str = "",
    signals: SourceSignals | None = None,
) -> float:
    """Score a result based on metadata quality signals."""
    cfg = DEFAULT_CONFIG
    auth_w = cfg.authority_weight
    snippet_w = cfg.snippet_weight
    pos_w = cfg.position_weight
    score = 0.0
    domain = get_domain(result.url)

    # Authority boost — stronger for tier-1 domains
    if any(d in domain for d in _TIER1_DOMAINS):
        score += auth_w * 2.0
    elif is_authority_domain(result.url):
        score += auth_w

    # Spam / SEO blog penalty
    if any(d in domain for d in _SPAM_DOMAINS_LOCAL):
        score -= 3.0
    # Medium penalty — most Medium posts are low-quality SEO content
    if "medium.com" in domain:
        score -= 1.5
    # Generic blog penalty
    if domain.startswith("blog.") or ".blog" in domain:
        score -= 0.5

    # Content type preference
    if result.likely_content_type == ContentType.DOCUMENTATION:
        score += _DOCS_TYPE_BOOST
    elif result.likely_content_type == ContentType.ARTICLE:
        score += _ARTICLE_TYPE_BOOST
    elif result.likely_content_type == ContentType.CODE:
        score += _CODE_TYPE_BOOST
    elif result.likely_content_type == ContentType.FORUM:
        score += _FORUM_TYPE_BOOST

    # URL suggests docs
    if result.url_suggests_docs:
        score += 1.0

    # Snippet quality (length heuristic)
    if result.snippet:
        score += min(len(result.snippet) / 500, 1.0) * _SNIPPET_QUALITY_BOOST * snippet_w

    # Position bonus with decay
    score += max(0, (10 - result.position) / 10) * (1 - result.position * _POSITION_DECAY) * pos_w

    # Cross-engine confirmation boost
    if len(result.engines_found) > 1:
        score += _CROSS_ENGINE_BOOST * min(len(result.engines_found), 3)

    if query:
        score += _query_freshness_boost(query, result)
    if signals is not None:
        score += signals.proximity_boost
        score -= signals.noise_penalty
        if signals.access_risk == "paywall_likely":
            score -= 0.5
        elif signals.access_risk == "paywall_possible":
            score -= 0.25
        elif signals.access_risk == "blocked_likely":
            score -= 1.5
        elif signals.access_risk == "dynamic_likely":
            score -= 0.25
        if signals.query_coverage < 0.25 and not result.is_primary:
            score -= 0.8

    return score


def _normalize_text(text: str) -> set[str]:
    """Normalize text for fuzzy comparison."""
    if not text:
        return set()
    # Lowercase, remove punctuation, split into words
    cleaned = "".join(c if c.isalnum() or c.isspace() else " " for c in text.lower())
    return {w for w in cleaned.split() if len(w) > 2}


def _jaccard_similarity(a: str, b: str) -> float:
    """Compute Jaccard similarity between two texts."""
    set_a = _normalize_text(a)
    set_b = _normalize_text(b)
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union) if union else 0.0


def _fuzzy_dedupe(results: list[SearchResult], threshold: float = 0.72) -> list[SearchResult]:
    """Remove results with highly similar titles or snippets even if URLs differ.

    Hybrid Jaccard + semantic dedupe catches Medium mirrors, StackOverflow
    copy-paste blogs, aggregator sites, and paraphrased duplicates.
    """
    unique: list[SearchResult] = []

    # Pre-compute semantic similarities if available
    semantic_sims: dict[tuple[int, int], float] = {}
    try:
        from .semantic_ranker import SemanticRanker

        if SemanticRanker.available() and len(results) > 1:
            texts = [f"{r.title} {r.snippet[:200]}" for r in results]
            sim_matrix = SemanticRanker.sentence_similarity(texts)
            if sim_matrix:
                for i in range(len(results)):
                    for j in range(i):
                        semantic_sims[(j, i)] = float(sim_matrix[i][j])
    except Exception:
        pass

    unique_indices: list[int] = []
    for i, r in enumerate(results):
        is_dup = False
        for j, u in enumerate(unique):
            # Title similarity (high weight — same title = likely duplicate)
            title_sim = _jaccard_similarity(r.title, u.title)
            # Snippet similarity (check first 200 chars)
            snippet_sim = _jaccard_similarity(r.snippet[:200], u.snippet[:200])
            # Semantic similarity (catches paraphrased duplicates)
            # Use original result index, not position in unique list
            orig_j = unique_indices[j]
            sem_sim = semantic_sims.get((orig_j, i), 0.0)

            # Duplicates: Jaccard high OR semantic very high
            if title_sim > threshold or snippet_sim > threshold or sem_sim > 0.95:
                is_dup = True
                engines = sorted(set(u.engines_found) | set(r.engines_found))
                r_better = (
                    (r.is_primary and not u.is_primary)
                    or (r.url_suggests_docs and not u.url_suggests_docs)
                    or (
                        r.is_primary == u.is_primary
                        and r.url_suggests_docs == u.url_suggests_docs
                        and len(r.snippet) > len(u.snippet) * 1.5
                    )
                )
                if r_better:
                    r.engines_found = engines
                    unique[j] = r
                    unique_indices[j] = i
                else:
                    u.engines_found = engines
                break

        if not is_dup:
            unique.append(r)
            unique_indices.append(i)

    logger.debug("Hybrid dedupe: %d -> %d results", len(results), len(unique))
    return unique


def merge_results(
    engine_results: dict[str, list[SearchResult]],
    query: str,
    search_runs: list[tuple[str, list[SearchResult]]] | None = None,
) -> list[RankedResult]:
    """Merge results from multiple engines, deduplicate, and rank.

    Args:
        engine_results: Dict mapping engine name -> list of SearchResult.
        query: Original query for BM25 scoring.

    Returns:
        List of RankedResult sorted by final_score descending.
    """
    # Phase 1: URL-level deduplicate and track which engines found each URL
    url_to_result: dict[str, SearchResult] = {}
    url_to_engines: dict[str, set[str]] = {}

    for engine_name, results in engine_results.items():
        for r in results:
            norm = normalize_url(r.url)
            if norm not in url_to_result:
                url_to_result[norm] = r
                url_to_engines[norm] = set()
            url_to_engines[norm].add(engine_name)

    # Update results with cross-engine metadata
    merged: list[SearchResult] = []
    for norm, r in url_to_result.items():
        r.engines_found = sorted(url_to_engines.get(norm, set()))
        merged.append(r)

    # Phase 2: Fuzzy dedupe — catch same content on different URLs
    merged = _fuzzy_dedupe(merged)

    # Phase 2b: Auto-classify source type for results missing it
    signals_by_url: dict[str, SourceSignals] = {}
    for r in merged:
        if r.source_type.value == "unknown" or not r.is_primary:
            from ..engines.base import guess_source_type_and_primary

            st, prim = guess_source_type_and_primary(r.url, r.snippet)
            r.source_type = st
            r.is_primary = prim
        norm_url = normalize_url(r.url)
        signals = source_signals(query, r.title, r.snippet, r.url)
        signals_by_url[norm_url] = signals
        r.query_coverage = signals.query_coverage
        r.access_risk = signals.access_risk
        r.access_reasons = signals.access_reasons
        r.noise_penalty = signals.noise_penalty

    # Phase 3: Compute BM25 scores
    bm25_scores = _compute_bm25_scores(query, merged)
    rrf_scores = _compute_rrf_scores(engine_results, search_runs)

    # Phase 3b: Compute semantic scores (optional, lazy-loaded)
    semantic_scores: dict[str, float] = {}
    try:
        from .semantic_ranker import SemanticRanker

        if SemanticRanker.available():
            sims = SemanticRanker.score_results(query, merged)
            for r, sim in zip(merged, sims, strict=False):
                semantic_scores[normalize_url(r.url)] = sim
    except Exception:
        pass  # Graceful fallback when sentence-transformers not installed

    # Phase 4: Build ranked results
    ranked: list[RankedResult] = []
    for r in merged:
        norm_url = normalize_url(r.url)
        bm25 = bm25_scores.get(norm_url, 0.0)
        signals = signals_by_url[norm_url]
        meta = _score_metadata(r, query, signals)
        semantic = semantic_scores.get(norm_url, 0.0)
        rrf = rrf_scores.get(norm_url, 0.0)
        # Normalize BM25 to be comparable with metadata score
        # (BM25 scores can be 0-30+, we compress to 0-5 range)
        normalized_bm25 = min(bm25 / 5.0, 5.0) if bm25 > 0 else 0.0
        # RRF typically 0-0.15 per engine; scale to ~0-3
        rrf_component = min(rrf * 20.0, 3.0)
        # Semantic similarity is [0,1]; scale to [0,2] to match BM25 weight
        final = normalized_bm25 + meta + semantic * 2.0 + rrf_component

        ranked.append(
            RankedResult(
                result=r,
                bm25_score=normalized_bm25,
                metadata_score=meta,
                semantic_score=semantic,
                final_score=final,
            )
        )

    # Sort by final score descending
    ranked.sort(key=lambda x: x.final_score, reverse=True)

    # Assign citation IDs
    for i, rr in enumerate(ranked, 1):
        rr.citation_id = i
        rr.result.citation_id = i

    logger.debug(
        "Merged %d results from %d engines, top score: %.2f",
        len(ranked),
        len(engine_results),
        ranked[0].final_score if ranked else 0,
    )

    return ranked


def rank_pages(pages: list[PageContent], query: str) -> list[PageContent]:
    """Rank fetched pages by quality and relevance.

    Args:
        pages: List of fetched PageContent.
        query: Original query.

    Returns:
        Pages sorted by combined quality+relevance score.
    """
    query_keywords = set(extract_keywords(query))

    # Semantic scores (optional, lazy-loaded)
    semantic_scores: dict[str, float] = {}
    try:
        from .semantic_ranker import SemanticRanker

        if SemanticRanker.available() and pages:
            texts = [f"{p.title} {p.text[:300]}" for p in pages]
            sims = SemanticRanker.query_sentence_similarity_batch(query, texts)
            for p, sim in zip(pages, sims, strict=False):
                semantic_scores[normalize_url(p.url)] = sim
    except Exception:
        pass

    scored_pages: list[tuple[PageContent, float]] = []
    for p in pages:
        score = 0.0

        # Quality score
        if p.quality.value == "high":
            score += 3.0
        elif p.quality.value == "medium":
            score += 1.5
        elif p.quality.value == "low":
            score += 0.5

        # Authority
        if is_authority_domain(p.url):
            score += 2.0

        # Keyword overlap in title/content
        text = f"{p.title} {p.text[:500]}".lower()
        overlap = sum(1 for kw in query_keywords if kw in text)
        score += overlap * 0.5

        # Semantic relevance
        semantic = semantic_scores.get(normalize_url(p.url), 0.0)
        score += semantic * 2.0

        # Content type preference
        if p.content_type == ContentType.DOCUMENTATION:
            score += 1.0
        elif p.content_type == ContentType.ARTICLE:
            score += 0.5

        # Freshness
        if p.freshness_days is not None and p.freshness_days < 30:
            score += 1.0
        elif p.freshness_days is not None and p.freshness_days < 90:
            score += 0.5

        # Code richness (for dev queries)
        if p.code_to_text_ratio > 0.2:
            score += 0.5

        scored_pages.append((p, score))

    scored_pages.sort(key=lambda x: x[1], reverse=True)
    return [p for p, _ in scored_pages]
