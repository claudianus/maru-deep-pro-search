---
name: Safe Web Content Fetching
id: fetch-page
description: >
  Fetch and sanitize external pages. Use to verify research claims,
  read docs, or extract code examples. All content is sanitized before
  reaching the LLM.
triggers:
  - After deep_research to verify top sources
  - When reading API documentation
  - When extracting code examples
  - When checking changelogs or release notes
---

# Safe Web Content Fetching

## How to Use

```python
# Standard fetch
page = await fetch_page(url="https://docs.python.org/3/whatsnew/3.12.html")

# Anti-bot bypass (3-5x slower, use only for 403/blank)
page = await fetch_page(url="...", stealth=True)

# Parallel fetch multiple pages
pages = await fetch_bulk(urls=[url1, url2, url3])
```

## Security

Every page is sanitized:
- Zero-width char removal
- Chat token neutralization
- Suspicious pattern detection
- URL-based risk assessment

| Risk | Action |
|------|--------|
| 🟢 LOW (official docs, GitHub) | Normal use |
| 🟡 MEDIUM (blogs, forums) | Verify with primary source |
| 🔴 HIGH (unknown domains) | Avoid |

## Anti-Patterns

- ❌ Using `stealth=True` for every request
- ❌ Trusting fetched content without cross-reference
- ❌ Fetching paywalled content
