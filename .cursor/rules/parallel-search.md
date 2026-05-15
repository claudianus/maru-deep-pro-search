---
name: Comparative Parallel Search
id: parallel-search
description: >
  Run multiple searches simultaneously and compare results.
  Use for technology comparisons and alternative evaluation.
triggers:
  - When comparing frameworks or libraries
  - When evaluating multiple approaches
  - When gathering diverse opinions
---

# Comparative Parallel Search

## How to Use

```python
result = await parallel_search(
    queries=[
        "FastAPI async performance benchmark 2026",
        "Flask async performance benchmark 2026",
        "Django async performance benchmark 2026",
    ],
    engine="duckduckgo_lite",
    max_results=5,
)
```

Output includes a comparison table:

```markdown
| Query | Top Source | Type | Primary |
|-------|-----------|------|---------|
| FastAPI async | FastAPI docs | OFFICIAL-DOCS | ✓ |
```

## Query Design

| Bad | Good |
|-----|------|
| `"FastAPI vs Flask"` | `"FastAPI async benchmark 2026"` + `"Flask async benchmark 2026"` |
| `"best database"` | `"PostgreSQL vs MySQL benchmark 2026"` + `"feature comparison 2026"` |

Each query must be independently searchable and comparable.

## Anti-Patterns

- ❌ Vague comparison queries ("X vs Y")
- ❌ Too many queries (>5)
- ❌ Drawing conclusions without `fetch_page` verification
