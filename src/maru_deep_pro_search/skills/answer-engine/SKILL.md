---
name: Answer Engine with maru-deep-pro-search
id: answer-engine
description: >
  Perplexity-style live web answer mode. Use for general factual questions,
  current prices, consumer recommendations, Korean market searches, news/current
  facts, and simple how-to questions.
triggers:
  - General web questions
  - Current facts, latest prices, or recommendations
  - Korean consumer searches such as 중고폰 시세, 노트북 추천, 요즘 가격
  - When the user expects an answer, not just a list of links
---

# Answer Engine

Use `answer` as the default entrypoint for general search questions.

```python
result = await answer(
    query="갤럭시 중고폰 최신 시세 추천 2026",
    mode="balanced",
    max_sources=8,
)
```

## Modes

| Mode | Use For |
|------|---------|
| `fast` | Quick source-backed answer packet with fewer sources |
| `balanced` | Default: ranked sources plus fetched evidence |
| `deep` | Higher-stakes recommendation or broad investigation |

## Output Contract

The tool returns an evidence packet. The host agent must synthesize the final
answer, cite factual claims as `[1]`, `[2]`, and state uncertainty when sources
disagree.

## Tool Choice

- Use `answer` for normal user questions and recommendations.
- Use `parallel_search` for explicit A vs B comparisons.
- Use `deep_research` for coding, architecture, security, or deep technical work.
- Use `fetch_page` when the user gives a URL.
