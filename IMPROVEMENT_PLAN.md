# clco-deep-research-mcp Improvement Plan

## Executive Summary

This plan addresses 4 critical issues identified from test feedback:
1. **Token defaults too low** - Documents truncated prematurely
2. **Deep research output too large** - 100K+ characters overwhelm context windows
3. **Weak Korean sources** - Only 3 results for Korean tech community queries
4. **Unclear tool differentiation** - No guidance on stealthy_fetch vs fetch_page

**Priority Order**: Issue 1 → Issue 2 → Issue 4 → Issue 3 (by impact/effort ratio)

---

## Issue 1: Increase Token Defaults (Priority: HIGH)

### Problem
Current defaults truncate long documents too aggressively:
- `fetch_page`: 3000 tokens (12K chars) - insufficient for medium articles
- `fetch_bulk`: 1500 tokens (6K chars) - barely covers a short blog post
- `stealthy_fetch`: 3000 tokens - same as fetch_page
- `deep_research`: hardcoded 1500 tokens per source

### Solution
Increase defaults while keeping maximum bounds unchanged:

| Tool | Current | New | Max |
|------|---------|-----|-----|
| fetch_page | 3000 | **6000** | 8000 |
| fetch_bulk | 1500 | **3000** | 5000 |
| stealthy_fetch | 3000 | **6000** | 8000 |
| deep_research (per source) | 1500 (hardcoded) | **2500** (configurable) | N/A |

### Files to Modify

#### 1. `src/clco_deep_research/tools.py`

```python
# Line 92: fetch_page default
async def tool_fetch_page(url: str, stealth: bool = False, max_tokens: int = 6000) -> str:

# Line 165: fetch_bulk default
async def tool_fetch_bulk(
    urls: list[str],
    stealth: bool = False,
    max_concurrent: int = 5,
    max_tokens: int = 3000,
) -> str:

# Line 242: stealthy_fetch default
async def tool_stealthy_fetch(url: str, max_tokens: int = 6000) -> str:

# Lines 292-294: TOOL_REGISTRY fetch_page schema
"max_tokens": {"type": "integer", "default": 6000, "minimum": 500, "maximum": 8000,
               "description": "Approximate max output tokens"},

# Lines 304: TOOL_REGISTRY fetch_bulk schema
"max_tokens": {"type": "integer", "default": 3000, "minimum": 300, "maximum": 5000},

# Lines 327: TOOL_REGISTRY stealthy_fetch schema
"max_tokens": {"type": "integer", "default": 6000, "minimum": 500, "maximum": 8000},
```

#### 2. `src/clco_deep_research/server.py`

```python
# Line 33: fetch_page
async def fetch_page(url: str, stealth: bool = False, max_tokens: int = 6000) -> str:

# Line 44: fetch_bulk
async def fetch_bulk(
    urls: list[str],
    stealth: bool = False,
    max_concurrent: int = 5,
    max_tokens: int = 3000,
) -> str:

# Line 67: stealthy_fetch
async def stealthy_fetch(url: str, max_tokens: int = 6000) -> str:
```

#### 3. `src/clco_deep_research/research/deep.py`

```python
# Line 320: Make max_tokens_per_source configurable with higher default
def format_for_llm(result: ResearchResult, max_tokens_per_source: int = 2500) -> str:
```

### Test Cases

```python
# Token defaults verification

class TestTokenDefaults:
    def test_fetch_page_default_increased(self):
        import inspect
        sig = inspect.signature(tool_fetch_page)
        default = sig.parameters['max_tokens'].default
        assert default == 6000, f"Expected 6000, got {default}"
    
    def test_fetch_bulk_default_increased(self):
        import inspect
        sig = inspect.signature(tool_fetch_bulk)
        default = sig.parameters['max_tokens'].default
        assert default == 3000, f"Expected 3000, got {default}"
    
    def test_stealthy_fetch_default_increased(self):
        import inspect
        sig = inspect.signature(tool_stealthy_fetch)
        default = sig.parameters['max_tokens'].default
        assert default == 6000, f"Expected 6000, got {default}"
    
    def test_format_for_llm_default_increased(self):
        import inspect
        sig = inspect.signature(format_for_llm)
        default = sig.parameters['max_tokens_per_source'].default
        assert default == 2500, f"Expected 2500, got {default}"
    
    def test_maximum_bounds_unchanged(self):
        # Verify we can't exceed max bounds
        schema = TOOLS["fetch_page"][2]["properties"]["max_tokens"]
        assert schema["maximum"] == 8000
        schema = TOOLS["fetch_bulk"][2]["properties"]["max_tokens"]
        assert schema["maximum"] == 5000
```

---

## Issue 2: Deep Research Output Optimization (Priority: HIGH)

### Problem
- `format_for_llm()` produces 100K+ characters for 8 sources
- Hardcoded 1500 tokens per source with no budget management
- No summarization - full content for every source
- No quality-based filtering - low-quality sources consume tokens

### Solution: Smart Token Management Pipeline

Add three mechanisms:
1. **Output budget**: `max_total_tokens` parameter (default: 20000)
2. **Dynamic allocation**: High-quality sources get more tokens
3. **Extractive summarization**: Optional `summarize=True` reduces content size
4. **Quality filtering**: Drop low-quality sources if over budget

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Deep Research Output Pipeline                              │
├─────────────────────────────────────────────────────────────┤
│  1. Calculate total budget: max_total_tokens                │
│  2. Score and rank sources by quality + relevance           │
│  3. Allocate tokens dynamically:                            │
│     - HIGH quality: 100% of per-source limit                │
│     - MEDIUM quality: 70% of per-source limit               │
│     - LOW quality: 40% of per-source limit                  │
│  4. If over budget:                                         │
│     a. Drop sources below relevance threshold               │
│     b. Apply extractive summarization                       │
│     c. Truncate to hard limit                               │
│  5. Format with metadata                                    │
└─────────────────────────────────────────────────────────────┘
```

### Files to Modify

#### 1. `src/clco_deep_research/research/deep.py`

Add new parameters and functions:

```python
# Add to deep_research() signature (line 70)
async def deep_research(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 8,
    follow_links: bool = False,
    stealth: bool = False,
    expand_queries: bool = True,
    max_tokens_per_source: int = 2500,  # NEW
    max_total_tokens: int = 20000,       # NEW
    summarize: bool = False,             # NEW
) -> ResearchResult:

# Add to ResearchResult dataclass (line 56)
@dataclass
class ResearchResult:
    query: str
    engine: str
    total_sources: int
    sources: list[Source] = field(default_factory=list)
    elapsed_ms: float = 0.0
    high_quality_count: int = 0
    blocked_count: int = 0
    subqueries: list[str] = field(default_factory=list)
    # NEW: Token management metadata
    total_tokens_used: int = 0           # NEW
    tokens_allocated: int = 0            # NEW
    sources_summarized: int = 0          # NEW
    sources_dropped: int = 0             # NEW
```

Add smart allocation function:

```python
def _allocate_tokens(
    sources: list[Source],
    max_tokens_per_source: int,
    max_total_tokens: int,
    summarize: bool,
) -> tuple[list[tuple[Source, int]], int, int]:
    """Allocate tokens to sources based on quality scores.
    
    Returns:
        (source_allocation, sources_summarized, sources_dropped)
        where source_allocation is list of (source, token_budget) tuples
    """
    if not sources:
        return [], 0, 0
    
    # Sort by quality and relevance
    quality_weights = {"high": 1.0, "medium": 0.7, "low": 0.4, "empty": 0.2, "blocked": 0.0}
    scored_sources = [
        (src, quality_weights.get(src.quality, 0.5) * (1 + src.relevance_score))
        for src in sources
    ]
    scored_sources.sort(key=lambda x: x[1], reverse=True)
    
    allocations = []
    total_allocated = 0
    sources_summarized = 0
    sources_dropped = 0
    
    for src, score in scored_sources:
        if src.quality == "blocked":
            continue
            
        # Calculate token budget based on quality
        quality_mult = quality_weights.get(src.quality, 0.5)
        budget = int(max_tokens_per_source * quality_mult)
        
        # Check if we'd exceed total budget
        if total_allocated + budget > max_total_tokens:
            # Try with summarization if enabled
            if summarize and src.quality in ("medium", "low"):
                budget = int(budget * 0.5)  # Half for summarized
                if total_allocated + budget <= max_total_tokens:
                    allocations.append((src, budget))
                    total_allocated += budget
                    sources_summarized += 1
                    continue
            
            # Drop source if still over budget
            sources_dropped += 1
            continue
        
        allocations.append((src, budget))
        total_allocated += budget
    
    return allocations, sources_summarized, sources_dropped
```

Add extractive summarization:

```python
def _extractive_summarize(markdown: str, max_tokens: int) -> str:
    """Create extractive summary using headings and key paragraphs."""
    from ..extraction.content import extract_headings, estimate_token_count
    
    if estimate_token_count(markdown) <= max_tokens:
        return markdown
    
    # Extract headings
    headings = extract_headings(markdown)
    
    # Build summary from headings + first paragraph after each heading
    summary_parts = []
    lines = markdown.split('\n')
    current_section = []
    in_section = False
    
    for line in lines:
        if line.startswith('#'):
            # Save previous section
            if current_section:
                summary_parts.extend(current_section[:2])  # Heading + first paragraph
                current_section = []
            in_section = True
            current_section.append(line)
        elif in_section and line.strip() and not line.startswith('#'):
            current_section.append(line)
            if len(current_section) >= 3:  # Heading + 2 paragraphs max
                in_section = False
    
    # Add last section
    if current_section:
        summary_parts.extend(current_section[:2])
    
    summary = '\n\n'.join(summary_parts)
    
    # Ensure we don't exceed token limit
    if estimate_token_count(summary) > max_tokens:
        summary = truncate_for_llm(summary, max_tokens)
    
    return summary + "\n\n_[Content summarized for brevity]_"
```

Update `format_for_llm()`:

```python
def format_for_llm(
    result: ResearchResult,
    max_tokens_per_source: int = 2500,
    max_total_tokens: int = 20000,
    summarize: bool = False,
) -> str:
    """Format research results into token-efficient markdown.
    
    Uses smart token allocation:
    - High-quality sources get full token budget
    - Medium/low sources get reduced budget
    - Optional summarization for over-budget scenarios
    - Low-relevance sources dropped if necessary
    """
    if not result.sources:
        return f"No results found for: '{result.query}' ({result.engine})"
    
    # Smart token allocation
    allocations, sources_summarized, sources_dropped = _allocate_tokens(
        result.sources,
        max_tokens_per_source,
        max_total_tokens,
        summarize,
    )
    
    # Update result metadata
    result.sources_summarized = sources_summarized
    result.sources_dropped = sources_dropped
    result.tokens_allocated = sum(budget for _, budget in allocations)
    
    # ... rest of formatting with allocated budgets
```

#### 2. `src/clco_deep_research/tools.py`

Update `tool_deep_research()`:

```python
async def tool_deep_research(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 8,
    follow_links: bool = False,
    expand_queries: bool = True,
    max_tokens_per_source: int = 2500,    # NEW
    max_total_tokens: int = 20000,         # NEW
    summarize: bool = False,               # NEW
) -> str:
    """End-to-end deep research pipeline with query expansion.
    
    Token Management:
    - max_tokens_per_source: Budget per source (default: 2500)
    - max_total_tokens: Total output budget (default: 20000)
    - summarize: Enable extractive summarization for over-budget (default: False)
    
    Smart allocation gives more tokens to high-quality sources.
    """
    # ... existing validation
    
    result = await deep_research(
        query=query,
        engine=engine,
        max_sources=max_sources,
        follow_links=follow_links,
        expand_queries=expand_queries,
        max_tokens_per_source=max_tokens_per_source,
        max_total_tokens=max_total_tokens,
        summarize=summarize,
    )
    return format_for_llm(
        result,
        max_tokens_per_source=max_tokens_per_source,
        max_total_tokens=max_total_tokens,
        summarize=summarize,
    )
```

Update TOOL_REGISTRY:

```python
"deep_research": (tool_deep_research,
    "Full pipeline: expand query → search → crawl → extract → structure for LLM. Includes query expansion, relevance scoring, and code-aware metadata. Smart token management prevents context overflow.", {
    "type": "object",
    "properties": {
        "query": {"type": "string", "description": "Research question or topic"},
        "engine": {"type": "string", "enum": SEARCH_ENGINES, "default": "duckduckgo_lite"},
        "max_sources": {"type": "integer", "default": 8, "minimum": 1, "maximum": 15},
        "follow_links": {"type": "boolean", "default": False,
                         "description": "Also crawl external links found on result pages"},
        "expand_queries": {"type": "boolean", "default": True,
                           "description": "Generate subqueries for broader coverage"},
        "max_tokens_per_source": {"type": "integer", "default": 2500, "minimum": 500, "maximum": 5000,
                                   "description": "Token budget per source"},
        "max_total_tokens": {"type": "integer", "default": 20000, "minimum": 2000, "maximum": 50000,
                              "description": "Total output token budget"},
        "summarize": {"type": "boolean", "default": False,
                       "description": "Enable extractive summarization for over-budget scenarios"},
    },
    "required": ["query"],
}),
```

#### 3. `src/clco_deep_research/server.py`

```python
@mcp.tool()
async def deep_research(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 8,
    follow_links: bool = False,
    expand_queries: bool = True,
    max_tokens_per_source: int = 2500,
    max_total_tokens: int = 20000,
    summarize: bool = False,
) -> str:
    from .tools import tool_deep_research
    
    return await tool_deep_research(
        query, engine, max_sources, follow_links, expand_queries,
        max_tokens_per_source, max_total_tokens, summarize,
    )
```

### Test Cases

```python
# Deep research token verification

class TestTokenAllocation:
    def test_high_quality_gets_full_budget(self):
        sources = [
            Source(quality="high", relevance_score=5.0, markdown="x" * 10000),
            Source(quality="low", relevance_score=1.0, markdown="x" * 10000),
        ]
        allocations, _, _ = _allocate_tokens(sources, 2500, 20000, False)
        
        high_budget = next(budget for src, budget in allocations if src.quality == "high")
        low_budget = next(budget for src, budget in allocations if src.quality == "low")
        
        assert high_budget > low_budget
    
    def test_total_budget_respected(self):
        sources = [Source(quality="high", relevance_score=5.0, markdown="x" * 10000) for _ in range(10)]
        allocations, _, dropped = _allocate_tokens(sources, 2500, 5000, False)
        
        total = sum(budget for _, budget in allocations)
        assert total <= 5000
        assert dropped > 0  # Some should be dropped
    
    def test_summarize_reduces_size(self):
        long_text = "# Heading\n\n" + "Paragraph text. " * 1000
        summary = _extractive_summarize(long_text, 500)
        
        assert len(summary) < len(long_text)
        assert "Heading" in summary
        assert "[Content summarized" in summary
    
    def test_blocked_sources_skipped(self):
        sources = [
            Source(quality="blocked", relevance_score=0.0),
            Source(quality="high", relevance_score=5.0, markdown="content"),
        ]
        allocations, _, _ = _allocate_tokens(sources, 2500, 20000, False)
        
        assert len(allocations) == 1
        assert allocations[0][0].quality == "high"

class TestFormatForLLM:
    def test_output_within_budget(self):
        result = ResearchResult(
            query="test",
            engine="duckduckgo_lite",
            total_sources=5,
            sources=[
                Source(
                    quality="high",
                    relevance_score=5.0,
                    markdown="# Test\n\nContent here. " * 500,
                    title=f"Source {i}",
                    url=f"https://example.com/{i}",
                )
                for i in range(5)
            ],
        )
        
        output = format_for_llm(result, max_total_tokens=5000)
        token_count = estimate_token_count(output)
        
        assert token_count <= 5000 * 1.1  # Allow 10% margin for metadata
```

---

## Issue 3: Korean Source Enhancement (Priority: MEDIUM)

### Problem
- "Korean tech community" queries return only 3 results
- No Korean-specific query optimization
- No Korean authority domain recognition
- DuckDuckGo has limited Korean content coverage

### Solution: Two-Phase Approach

**Phase 1 (Quick Win)**: Optimize existing DuckDuckGo for Korean queries
**Phase 2 (Future)**: Add Naver/Daum search engine

### Phase 1: Query Optimization

#### 1. `src/clco_deep_research/research/expander.py`

Add Korean-specific templates:

```python
# Add to _QUERY_TEMPLATES
_QUERY_TEMPLATES = {
    # ... existing templates ...
    "korean_community": [
        "{query} 한국 개발자 커뮤니티",
        "{query} 국내 개발 블로그",
        "{query} 한국어 튜토리얼",
        "{query} 네이버 블로그",
        "{query} 티스토리",
    ],
    "korean_docs": [
        "{query} 한국어 문서",
        "{query} 한글 설명서",
        "{query} 국내 번역",
    ],
}
```

Update `_select_angles()`:

```python
def _select_angles(query: str) -> list[str]:
    """Select relevant expansion angles based on query content."""
    lower = query.lower()
    angles = []
    
    # Check for Korean language indicators
    has_korean = any('\uac00' <= char <= '\ud7a3' for char in query)
    korean_keywords = ["한국", "국내", "korean", "한글", "한국어"]
    is_korean_query = has_korean or any(kw in lower for kw in korean_keywords)
    
    if is_korean_query:
        angles.extend(["korean_community", "korean_docs", "recent"])
        return angles
    
    # ... rest of existing logic ...
```

#### 2. `src/clco_deep_research/utils/url.py`

Add Korean authority domains:

```python
# Add to _AUTHORITY_DOMAINS
_KOREAN_AUTHORITY_DOMAINS = {
    "velog.io",           # Korean developer blog platform
    "tistory.com",        # Popular Korean blog platform
    "naver.com",          # Naver (search, blog, cafe)
    "daum.net",           # Daum/Kakao
    "github.com",         # Already in list
    "stackoverflow.com",  # Already in list
}

_AUTHORITY_DOMAINS.update(_KOREAN_AUTHORITY_DOMAINS)
```

#### 3. `src/clco_deep_research/engines/duckduckgo.py`

Add Korean content type detection:

```python
def _guess_content_type(url: str, snippet: str = "") -> ContentType:
    """Guess content type from URL and snippet."""
    lower = (url + " " + snippet).lower()
    domain = urlparse(url).netloc.lower()
    
    # Korean-specific detection
    korean_indicators = ["velog.io", "tistory.com", "naver.com/blog", "brunch.co.kr"]
    if any(ind in domain for ind in korean_indicators):
        if "github.com" in domain:
            return ContentType.CODE
        return ContentType.ARTICLE
    
    # ... rest of existing logic ...
```

### Phase 2: Naver Engine (Future)

Create `src/clco_deep_research/engines/naver.py`:

```python
"""Naver search engine implementation using Naver Open API."""

from __future__ import annotations

import os
from urllib.parse import quote
import aiohttp

from .base import SearchEngine, SearchResult, PageContent


class NaverEngine(SearchEngine):
    """Naver search engine using Open API.
    
    Requires NAVER_CLIENT_ID and NAVER_CLIENT_SECRET environment variables.
    """
    
    name = "naver"
    supports_stealth = False
    
    def __init__(self):
        self.client_id = os.getenv("NAVER_CLIENT_ID")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET")
        if not self.client_id or not self.client_secret:
            raise ValueError("NAVER_CLIENT_ID and NAVER_CLIENT_SECRET required")
    
    async def search(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search Naver web documents."""
        url = "https://openapi.naver.com/v1/search/webkr.json"
        headers = {
            "X-Naver-Client-Id": self.client_id,
            "X-Naver-Client-Secret": self.client_secret,
        }
        params = {
            "query": query,
            "display": min(max_results, 100),
            "start": 1,
            "sort": "sim",  # sim (relevance) or date
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                data = await resp.json()
        
        results = []
        for i, item in enumerate(data.get("items", [])):
            results.append(SearchResult(
                title=item["title"],
                url=item["link"],
                snippet=item["description"],
                position=i + 1,
                likely_content_type=ContentType.ARTICLE,
                domain="naver.com",
                engine="naver",
            ))
        
        return results
    
    async def fetch(self, url: str, stealth: bool = False) -> PageContent:
        """Fetch page content - delegates to DuckDuckGo fetch."""
        # Reuse DuckDuckGo's fetch logic
        from .duckduckgo import DuckDuckGoEngine
        engine = DuckDuckGoEngine()
        return await engine.fetch(url, stealth=stealth)
```

### Test Cases

```python
# Korean support verification

class TestKoreanQueryExpansion:
    def test_korean_query_detected(self):
        subqueries = expand_query("파이썬 asyncio 한국", max_subqueries=5)
        # Should include Korean-specific angles
        assert any("한국" in sq or "국내" in sq for sq in subqueries)
    
    def test_korean_angles_selected(self):
        angles = _select_angles("한국 개발자 커뮤니티")
        assert "korean_community" in angles
    
    def test_korean_domains_recognized(self):
        from clco_deep_research.utils.url import is_authority_domain
        assert is_authority_domain("https://velog.io/@user/post")
        assert is_authority_domain("https://user.tistory.com/123")

class TestKoreanContentType:
    def test_velog_detected_as_article(self):
        from clco_deep_research.engines.duckduckgo import _guess_content_type
        from clco_deep_research.engines.base import ContentType
        
        result = _guess_content_type("https://velog.io/@user/python-async")
        assert result == ContentType.ARTICLE
```

---

## Issue 4: Documentation Improvements (Priority: MEDIUM)

### Problem
- No documentation on when to use `stealthy_fetch` vs `fetch_page`
- Tool descriptions lack usage context
- No decision tree for tool selection

### Solution

#### 1. Enhanced Docstrings in `tools.py`

```python
async def tool_fetch_page(url: str, stealth: bool = False, max_tokens: int = 6000) -> str:
    """Fetch a page via Scrapling and extract clean, LLM-optimized content.
    
    Use Cases:
    - General web pages, blogs, documentation
    - Sites without anti-bot protection
    - When you need fast fetching (uses lightweight DynamicFetcher)
    
    When to use stealth=True parameter instead of stealthy_fetch:
    - Site returns CAPTCHA or access denied
    - Content appears incomplete (missing articles, blocked sections)
    - You suspect anti-bot measures but want to try fast path first
    
    When to use stealthy_fetch instead:
    - You already know the site has strong protection (Cloudflare, DataDome)
    - Previous fetch_page attempts failed
    - You need guaranteed access and can accept slower fetching
    
    Returns structured markdown with quality signals, content type,
    and link suggestions for follow-up research.
    """

async def tool_stealthy_fetch(url: str, max_tokens: int = 6000) -> str:
    """Fetch a URL with full StealthyFetcher anti-bot bypass.
    
    Use Cases:
    - Sites behind Cloudflare Turnstile, DataDome, or PerimeterX
    - When fetch_page returns [BLOCKED] or incomplete content
    - High-value sources where access certainty matters
    
    Trade-offs:
    - Slower: ~3-5x slower than fetch_page due to browser automation
    - More resource intensive: Uses headless browser
    - May still fail on the most advanced protections
    
    Recommendation: Try fetch_page first, fall back to stealthy_fetch
    only if needed.
    
    Automatically adapts browser fingerprint per site for maximum
    compatibility.
    """
```

#### 2. Decision Tree in README

```markdown
## Tool Selection Guide

```
Need to search?
├── Yes → web_search (general) or parallel_search (multiple queries)
│
Need to fetch a specific URL?
├── Is it a known protected site (Cloudflare, etc.)?
│   ├── Yes → stealthy_fetch
│   └── No → fetch_page
│       └── Failed or blocked?
│           └── Yes → stealthy_fetch (retry)
│
Need to fetch multiple URLs?
└── Yes → fetch_bulk
    └── Any failures?
        └── Yes → Re-fetch failed ones with stealthy_fetch

Need comprehensive research?
└── Yes → deep_research
    └── Too much output?
        └── Yes → Use summarize=True parameter
```
```

### Test Cases

```python
# Documentation verification

class TestDocumentation:
    def test_fetch_page_docstring_has_stealth_guidance(self):
        assert "stealthy_fetch" in tool_fetch_page.__doc__
        assert "When to use" in tool_fetch_page.__doc__
    
    def test_stealthy_fetch_docstring_has_tradeoffs(self):
        assert "Trade-offs" in tool_stealthy_fetch.__doc__
        assert "slower" in tool_stealthy_fetch.__doc__.lower()
```

---

## Implementation Order

### Sprint 1: Token Defaults (1-2 hours)
1. Update defaults in `tools.py`
2. Update defaults in `server.py`
3. Update `format_for_llm()` default
4. Write tests
5. Run test suite
6. **Commit**: `feat: increase default token limits for better content coverage`

### Sprint 2: Smart Token Management (3-4 hours)
1. Add parameters to `deep_research()`
2. Implement `_allocate_tokens()`
3. Implement `_extractive_summarize()`
4. Update `format_for_llm()`
5. Update `tool_deep_research()` and TOOL_REGISTRY
6. Update `server.py`
7. Write tests
8. Run test suite
9. **Commit**: `feat: add smart token management to deep_research`

### Sprint 3: Summarization (2-3 hours)
1. Polish extractive summarization
2. Add `summarize` parameter integration
3. Write tests
4. Run test suite
5. **Commit**: `feat: add extractive summarization for deep_research`

### Sprint 4: Korean Support (2-3 hours)
1. Add Korean query templates
2. Add Korean domain recognition
3. Add Korean content type detection
4. Write tests
5. Run test suite
6. **Commit**: `feat: enhance Korean query support`

### Sprint 5: Documentation (1-2 hours)
1. Enhance tool docstrings
2. Update README with decision tree
3. Write documentation tests
4. **Commit**: `docs: improve tool documentation and usage guidance`

---

## Test Strategy

### Running Tests

```bash
# All tests
ruff check . && ruff format --check . && mypy src/

# Specific test files
ruff check src/
ruff check src/
ruff check src/
ruff check src/

# With coverage


# Integration tests (hits network)
ruff check . && ruff format --check . && mypy src/
```

### Test Checklist

- [ ] All existing tests still pass
- [ ] New tests for token defaults
- [ ] New tests for token allocation
- [ ] New tests for summarization
- [ ] New tests for Korean support
- [ ] New tests for documentation
- [ ] Integration tests pass (if applicable)
- [ ] No regression in existing functionality

---

## Rollback Plan

If issues arise:

1. **Token defaults too high causing timeouts**: Revert to 4500/2000
2. **Summarization losing critical info**: Adjust extractive algorithm or disable by default
3. **Korean queries worse**: Revert query templates, keep domain recognition
4. **Breaking changes**: Each commit is atomic and can be reverted independently

---

## Success Metrics

- [ ] fetch_page returns 2x more content on average
- [ ] deep_research output stays under 25K tokens (50K chars) by default
- [ ] Korean tech queries return 5+ results (vs current 3)
- [ ] Users can choose appropriate tool without confusion
- [ ] All 68+ existing tests pass
- [ ] 20+ new tests added and passing
