---
name: Targeted Web Search
id: web-search
description: >
  Fast targeted search with engine selection. Use for quick fact-checking,
  finding docs, or version checks. 2-3s vs deep_research's 5-15s.
triggers:
  - Quick fact-checking
  - Finding specific documentation pages
  - Discovering new tools or libraries
  - Checking latest versions of dependencies
  - Finding code examples for specific patterns
---

# Targeted Web Search

## How to Use

```python
results = await web_search(
    query="Python 3.12 new features",
    engine="duckduckgo_lite",  # or "auto", "bing", "google"
    max_results=5,
)
```

## Engine Selection

| Engine | Best For |
|--------|----------|
| `duckduckgo_lite` | General queries, default |
| `google` | Cutting-edge topics |
| `bing` | Region-specific queries |
| `startpage` | Privacy-sensitive searches |
| `baidu` / `naver` | Chinese / Korean content |

Use `engine="auto"` for automatic failover.

## vs deep_research

| | web_search | deep_research |
|---|-----------|---------------|
| Speed | 2-3s | 5-15s |
| Engines | 1 | Multiple + ranking |
| Use for | Quick lookup | Complex investigation |

## Anti-Patterns

- ❌ Using `web_search` when `deep_research` is needed
- ❌ Trusting results without `fetch_page` verification
- ❌ Not using citation IDs when referencing
