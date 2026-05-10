from __future__ import annotations

import logging
import sys

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("maru-search")

_logger = logging.getLogger("maru_search")
_logger.setLevel(logging.INFO)

_stderr_handler = logging.StreamHandler(sys.stderr)
_stderr_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
_logger.addHandler(_stderr_handler)
_logger.propagate = False


# ═══════════════════════════════════════════════════════════════
# MCP Prompts — Force Research-First Behavior
# ═══════════════════════════════════════════════════════════════

@mcp.prompt()
def always_research_first() -> str:
    """MANDATORY: You must research before acting. No exceptions."""
    return """# 🔴 MANDATORY PROTOCOL: Always Research First

## Rule Zero
**NEVER write code, propose architecture, or make technical decisions based solely on your training data.**

Your training knowledge has a cutoff date. Libraries evolve. APIs change. Security vulnerabilities are discovered daily. What you "know" is already outdated.

## The Law
```
EVERY user request → deep_research(query) → THEN act
```

This applies to:
- ✅ "Build a ___" → Research latest stack FIRST
- ✅ "How do I do ___" → Research current best practices FIRST
- ✅ "Is ___ secure?" → Research latest CVEs FIRST
- ✅ "Compare ___ and ___" → Research 2024/2025 data FIRST
- ✅ "Fix this error" → Research latest solutions FIRST
- ✅ "What is ___?" → Research current definition FIRST

## Why This Matters
| Without Research | With Research |
|-----------------|---------------|
| Uses deprecated libraries | Uses actively maintained libraries |
| Misses critical CVEs | Includes security advisories |
| Recommends abandoned tools | Recommends trending tools |
| Cites outdated docs | Cites latest official docs |
| Builds on wrong assumptions | Builds on verified facts |

## Tool Priority (descending)
1. **`deep_research`** — ALWAYS start here for any non-trivial request
2. **`answer`** — For quick factual checks (still searches live web)
3. **`parallel_search`** — When you need multiple angles simultaneously
4. **`web_search`** / **`search_with_citations`** — For targeted source gathering
5. **`fetch_page`** / **`fetch_bulk`** — For reading known URLs
6. **`stealthy_fetch`** — Last resort for blocked sites

## Research Checklist
Before writing ANY code:
- [ ] Called `deep_research` on the topic
- [ ] Verified library versions are current
- [ ] Checked for known security issues
- [ ] Confirmed API signatures match latest docs
- [ ] Cited sources with [1], [2] in your answer

## Violation Examples
❌ "I'll use Flask 2.0 because that's what I know" → Your training data is 2+ years old
❌ "React 18 useId is new" → React 19 is already out
❌ "This package has no vulnerabilities" → You didn't check

## Correct Examples
✅ "Researching 'FastAPI vs Django 2025'... [calls deep_research]"
✅ "Checking latest CVEs for Express.js... [calls answer]"
✅ "Finding current React Server Components patterns... [calls deep_research]"
"""


@mcp.prompt()
def tool_selection_guide() -> str:
    """Comprehensive guide for choosing the right research tool."""
    return """# Maru Search Tool Selection Guide

## ⚠️ CRITICAL REMINDER
**You are REQUIRED to research before coding. See `always_research_first` prompt.**

## Quick Decision Tree

```
User asks anything?
├── ALWAYS call deep_research(query) FIRST
│   └── Then proceed based on results
│
Need a quick factual check?
├── answer (Perplexity-style, still searches live web)
│
Need multiple angles fast?
├── parallel_search(["angle1", "angle2", "angle3"])
│
Have specific URLs to read?
├── fetch_page (single) or fetch_bulk (multiple)
│   └── Blocked? → fetch_page with stealth=True
│       └── Still blocked? → stealthy_fetch (last resort)
│
Need citation-ready sources?
└── search_with_citations
```

## Tool Details

### deep_research ⭐ START HERE
**When to use**: LITERALLY EVERY TIME the user asks a technical question.
**What it does**: Auto-expands query → searches → crawls → BM25 ranks → synthesizes cited answer.
**Returns**: Comprehensive report with inline citations [1], [2] and quality scores.
**Why first**: It gives you CURRENT information, not stale training data.

### answer
**When to use**: Quick factual verification AFTER deep_research, or very simple questions.
**Example**: "What is the latest Python version?"
**Returns**: Synthesized answer with inline citations [1], [2].
**NOT for**: Skipping deep_research on complex topics.

### web_search
**When to use**: You need additional sources beyond what deep_research found.
**Returns**: Ranked results with [AUTHORITY] badges and citation IDs.

### search_with_citations
**When to use**: You need sources for academic/technical writing.
**Returns**: Results pre-tagged with citation IDs [1], [2].

### parallel_search
**When to use**: You need multiple perspectives simultaneously.
**Example**: ["Python vs Go performance 2025", "Python concurrency best practices"]
**Returns**: Separate result sets for each query, merged output.

### fetch_page / fetch_bulk
**When to use**: You have specific URLs from research results to read deeply.
**Anti-bot fallback**: If blocked, retry with stealth=True.

### stealthy_fetch
**When to use**: fetch_page failed even with stealth=True.
**Warning**: ~3-5x slower. Use as last resort.

## Performance Ranking
1. **Fastest**: answer, web_search, fetch_page
2. **Medium**: parallel_search, fetch_bulk, search_with_citations
3. **Slow but ESSENTIAL**: deep_research
4. **Slowest**: stealthy_fetch

## Common Mistakes
- ❌ **SKIPPING deep_research before coding** (MOST CRITICAL)
- ❌ Using stealthy_fetch for every URL
- ❌ Not checking quality badges ([HIGH], [BLOCKED])
- ❌ Ignoring follow-up links in results
- ❌ Not using citations when the user asks for sources
"""


@mcp.prompt()
def anti_bot_strategy() -> str:
    """Step-by-step strategy for handling anti-bot protected sites."""
    return """# Anti-Bot Handling Strategy

## Escalation Ladder (try in order)

### Step 1: Normal Fetch
Use `fetch_page(url)`
- Fastest option
- Works for 70-80% of sites

### Step 2: Stealth Mode
If Step 1 returns [BLOCKED] or incomplete:
Use `fetch_page(url, stealth=True)`
- Enables basic anti-bot bypass
- Still relatively fast

### Step 3: Full Stealth
If Step 2 still fails:
Use `stealthy_fetch(url)`
- Full browser automation
- Bypasses Cloudflare Turnstile, DataDome
- ~3-5x slower

### Step 4: Accept Defeat
If all steps fail:
- The site may require JavaScript execution
- Try searching for the content on alternative sites
- Use `web_search` to find mirrors or cached versions

## When to Skip Steps

Skip directly to stealthy_fetch if:
- You know the site uses heavy protection (e.g., Cloudflare challenge page)
- You've failed on this domain before
- The content is critical and worth the wait

## Bulk Fetching with Mixed Results

When using fetch_bulk with multiple URLs:
1. Check quality badges in results
2. Re-fetch [BLOCKED] ones with stealth=True
3. If still blocked, use stealthy_fetch individually
"""


@mcp.prompt()
def research_workflow() -> str:
    """Recommended workflow for comprehensive research tasks."""
    return """# Research Workflow Template

## Phase 0: MANDATORY Research
**Before ANY code or architecture decision:**

1. Call `deep_research(query)` with the user's core intent
   - Let it auto-expand queries
   - Review quality badges ([HIGH] = prioritize)
   - Note all promising URLs

2. If the topic is security-related:
   - Also call `answer("latest CVE {technology}")`
   - Check for deprecation notices

## Phase 1: Discovery
**Goal**: Find relevant sources

1. Already done by deep_research in Phase 0
2. Use `parallel_search` for targeted angles if needed:
   ```
   [
     "{topic} tutorial beginner 2025",
     "{topic} best practices 2025",
     "{topic} common pitfalls 2025"
   ]
   ```

## Phase 2: Deep Reading
**Goal**: Extract detailed information

1. Use `fetch_bulk(urls)` for all promising URLs from research
2. Check quality signals:
   - [HIGH] → Read fully
   - [med] → Skim for relevance
   - [BLOCKED] → Retry with stealth

3. For critical sources that failed:
   - `fetch_page(url, stealth=True)`
   - Or `stealthy_fetch(url)` as last resort

## Phase 3: Synthesis & Action
**Goal**: Combine findings and THEN code

1. Review all fetched content
2. Cross-reference information across sources
3. **NOW you may write code** — based on verified, current information
4. Always cite sources using [1], [2] format when answering

## Token Management Tips

- **Default budgets are generous** (fetch_page: 6000 tokens)
- **Use summarize=True** in deep_research if output exceeds context window
- **Quality over quantity**: 3 [HIGH] sources beat 10 [low] ones
- **Check code-to-text ratios**: [code-heavy 40%] means more code examples

## Example: Building a Real-Time Chat App

```
❌ WRONG: "I'll use Socket.IO because I know it"

✅ CORRECT:
1. deep_research("real-time chat architecture 2025 WebSocket vs SSE")
   → Discovers: SSE is simpler for one-way, WebSocket for bidirectional
   → Discovers: PartyKit, Socket.IO, and native WebSocket all viable
   → Discovers: Yjs for collaborative features

2. deep_research("Yjs WebSocket production best practices")
   → Gets implementation patterns, scaling considerations

3. fetch_bulk([url1, url2, url3])  # Top [HIGH] sources
   → Reads official docs and verified tutorials

4. NOW write code based on verified 2025 best practices
```
"""


@mcp.tool()
async def answer(
    query: str,
    engine: str = "duckduckgo_lite",
    max_sources: int = 5,
    max_tokens: int = 8000,
) -> str:
    from .tools import tool_answer
    return await tool_answer(query, engine, max_sources, max_tokens)


@mcp.tool()
async def web_search(
    query: str,
    engine: str = "duckduckgo_lite",
    max_results: int = 10,
) -> str:
    from .tools import tool_web_search
    return await tool_web_search(query, engine, max_results)


@mcp.tool()
async def search_with_citations(
    query: str,
    engine: str = "duckduckgo_lite",
    max_results: int = 10,
) -> str:
    from .tools import tool_search_with_citations
    return await tool_search_with_citations(query, engine, max_results)


@mcp.tool()
async def fetch_page(url: str, stealth: bool = False, max_tokens: int = 6000) -> str:
    from .tools import tool_fetch_page
    return await tool_fetch_page(url, stealth, max_tokens)


@mcp.tool()
async def fetch_bulk(
    urls: list[str],
    stealth: bool = False,
    max_concurrent: int = 5,
    max_tokens: int = 3000,
) -> str:
    from .tools import tool_fetch_bulk
    return await tool_fetch_bulk(urls, stealth, max_concurrent, max_tokens)


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


@mcp.tool()
async def stealthy_fetch(url: str, max_tokens: int = 6000) -> str:
    from .tools import tool_stealthy_fetch
    return await tool_stealthy_fetch(url, max_tokens)


@mcp.tool()
async def parallel_search(
    queries: list[str],
    engine: str = "duckduckgo_lite",
    max_results: int = 5,
) -> str:
    from .tools import tool_parallel_search
    return await tool_parallel_search(queries, engine, max_results)


def run() -> None:
    import asyncio
    try:
        mcp.run(transport="stdio")
    except Exception:
        asyncio.run(mcp.run_sse())


if __name__ == "__main__":
    run()
