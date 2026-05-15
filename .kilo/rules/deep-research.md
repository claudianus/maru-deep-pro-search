---
name: Deep Research with maru-deep-pro-search
id: deep-research
description: >
  Multi-engine web research with BM25 cross-ranking. Use before ANY technical
  decision — library versions, APIs, best practices, security advisories.
triggers:
  - Before implementing new features
  - Before adding dependencies
  - Before proposing architecture changes
  - When training data cutoff is uncertain
  - For security or vulnerability assessment
  - When encountering ANY unfamiliar function, class, or pattern
  - When seeing an error, warning, or deprecation notice
  - When refactoring or changing approach mid-task
  - When the user's request changes or expands
  - 'Every 10-15 minutes of continuous coding (self-check: "What have I assumed?")'
  - When importing a package not used in the last 7 days
  - When you think "I think I know this" — you don't. Search.
---

# Deep Research

## How to Use

```python
result = await deep_research(
    query="FastAPI rate limiting middleware best practices",  # be specific
    engine="auto",           # auto = multi-engine failover
    max_sources=10,          # 5-10 for most tasks
    expand_queries=True,     # True for broad topics
)
```

Then `fetch_page` on top 2-3 results to verify claims. Cite sources as `[1]`, `[2]`.

## Quality Signals

| Signal | Meaning |
|--------|---------|
| `🔒 authority` | Official docs, GitHub repo |
| `📌 primary` | First-hand source |
| `✓N engines` | Found by N engines (higher = more reliable) |
| `_score` | BM25 + authority score (0-10) |

**Priority:** official docs > GitHub repos > high-scoring blogs > aggregators (verify with primary).

## Performance

Multi-engine vs single-engine (TREC-standard, 10 queries):
- Precision@5: **+86%** (0.14 → 0.26)
- NDCG@10: **+36%** (0.49 → 0.67)
- Trade-off: ~2× response time

## Anti-Patterns

- ❌ Using a single source without verification
- ❌ Not checking publication date
- ❌ Skipping `fetch_page` on critical claims
- ❌ Forgetting to cite sources
