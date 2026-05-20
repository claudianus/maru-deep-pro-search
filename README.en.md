# maru-deep-pro-search

A Model Context Protocol (MCP) server that empowers AI agents to perform real-time web research and inject fresh, contextual knowledge before writing code. With zero API key setup, it aggregates results from 9 search engines, applies hybrid ranking (RRF + BM25), and performs local semantic re-ranking using the Granite 97M model.

[🇰🇷 한국어](./README.md)

[![PyPI](https://img.shields.io/pypi/v/maru-deep-pro-search?style=flat-square&color=blue)](https://pypi.org/project/maru-deep-pro-search/)
[![Validate](https://github.com/claudianus/maru-deep-pro-search/actions/workflows/validate.yml/badge.svg)](https://github.com/claudianus/maru-deep-pro-search/actions/workflows/validate.yml)
[![Python](https://img.shields.io/pypi/pyversions/maru-deep-pro-search?style=flat-square)](https://pypi.org/project/maru-deep-pro-search/)
[![License](https://img.shields.io/badge/license-MIT-brightgreen?style=flat-square)](https://github.com/claudianus/maru-deep-pro-search/blob/main/LICENSE)

[Website](https://claudianus.github.io/maru-deep-pro-search/) · [Prompt Templates](https://claudianus.github.io/maru-deep-pro-search/#prompts) · [PyPI Package](https://pypi.org/project/maru-deep-pro-search/) · [GitHub Repository](https://github.com/claudianus/maru-deep-pro-search)

---

## Key Features

- **Hybrid Multi-Engine Search**: Aggregates from 9 search sources (including DuckDuckGo and Bing) with automatic engine failover.
- **Local Semantic Re-ranking**: Integrates the `ibm-granite/granite-embedding-97m-multilingual-r2` model to run embedding-based re-ranking locally.
- **Citations Pipeline**: Enforces strict `[N]` reference mappings linked to source URLs to prevent hallucinations.
- **Broad Agent Support**: Compatible with 21 major AI developer environments including Cursor, Claude Code, Cline, and Aider.
- **100% Free**: No proprietary search API keys required.

## Core MCP Tools

| Tool | Description |
|:---|:---|
| `answer` | Quickly answers general queries, retrieves market trends, and resolves basic lookups. |
| `deep_research` | Performs extensive information gathering and clustering for CVE security analysis, architecture planning, and library comparisons (includes Research Trace). |
| `fetch_page` | Extracts and sanitizes webpage/document content, filtering out prompt-injection attacks. |

- **Detailed Tools Guide**: See [Website Tools](https://claudianus.github.io/maru-deep-pro-search/#tools)
- **Supported Agents**: See [Website Agents](https://claudianus.github.io/maru-deep-pro-search/#agents)

---

## Installation and Setup

### Step 1: Run the Installation Script

**macOS / Linux:**
```bash
curl -sSL https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.sh | bash
```

**Windows:**
```powershell
irm https://raw.githubusercontent.com/claudianus/maru-deep-pro-search/main/scripts/install.ps1 | iex
```

**Manual installation via Pip/Hatch:**
```bash
pip install --user maru-deep-pro-search
maru-deep-pro-search setup
```

**Using uv:**
```bash
uv tool install --python 3.12 maru-deep-pro-search
```

> [!NOTE]
> The Granite 97M weight files are downloaded from Hugging Face on the first search run. To prevent initial cold start latency, prefetch the embeddings with the following command:
> ```bash
> maru-deep-pro-search warmup-embeddings -q
> maru-deep-pro-search setup --check
> ```

### Step 2: Configure the Agent

After installation, **fully restart** your agent application (e.g., Cursor).

#### Claude Code MCP Configuration (`~/.claude/settings.json`)
```json
{
  "mcpServers": {
    "maru-deep-pro-search": {
      "command": "python3",
      "args": ["-m", "maru_deep_pro_search.server"]
    }
  }
}
```

---

## Usage

Provide guidelines in your system prompts (User Rules) or within the chat:

- `"Search the web to verify the latest API specs before writing code. Always cite your sources as [1], [2]."`
- `"Find the latest fixes for Next.js 15 App Router Server Action revalidate errors and apply them."`
- `"Look up the official security advisory for CVE-2026-40347 and verify if our current package version is safe."`

---

## Feature Comparison

| Feature | maru | Tavily MCP | Perplexity MCP |
|:---|:---|:---|:---|
| **Cost** | **Free ($0)** | Limited Free / Paid | $5+/month |
| **Search Engines** | **9 Engines + Auto Failover** | Single API | Single API |
| **Research Enforcement** | **3-Layer Gate** | No | No |
| **Research Trace** | **Detailed Trace & Insights** | No | No |

---

## Performance Benchmark

Measured search quality metrics under the TREC (Text REtrieval Conference) standards over 10 complex test queries.

| Metric | Single Engine Baseline | Multi-Engine (maru) |
|:---|:---|:---|
| **Precision@5** | baseline | **+86%** |
| **NDCG@10** | baseline | **+36%** |
| **MRR** | baseline | **+25%** |

*Trade-off: Aggregating 9 search engines may double the search latency compared to a single-engine request. (Run `uv run python benchmark/search_quality_benchmark.py` to reproduce).*

---

## Primary Configuration

Control server behavior using system environment variables:

| Environment Variable | Default | Description |
|:---|:---|:---|
| `MARU_STRICT_QUERY` | `1` | Normalizes or rejects vague/malformed search queries. |
| `MARU_EMBEDDING_MODEL` | Granite 97M R2 | Model identifier for document semantic re-ranking. |
| `MARU_BENCHMARK_SUITE` | — | Runs stress benchmarking when set to `stress`. |

- **Full Configuration Details**: See [Website Config](https://claudianus.github.io/maru-deep-pro-search/#config)

---

## Troubleshooting

| Symptom | Resolution |
|:---|:---|
| MCP server not detected by agent | Run `maru-deep-pro-search setup` and fully restart the agent application. |
| Slow initial search query | Prefetch the Hugging Face weights by running `maru-deep-pro-search warmup-embeddings -q`. |
| Configuration changes not applied | Run `maru-deep-pro-search update --with-setup` or `setup --repair` to refresh hooks. |
| Intermittent engine failures | Run the `engine_health` tool to verify the live status of the integrated search engines. |

---

## Contributing and License

- **Contributing**: Contributions are welcome! Refer to [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
- **License**: Licensed under the MIT License. See [LICENSE](LICENSE) for details.
