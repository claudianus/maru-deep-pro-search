# maru-search

Universal AI search MCP server. Zero API keys. Scrapes search engines directly and returns cited answers.

범용 AI 검색 MCP 서버. API 키 없이 검색엔진을 직접 스크래핑하고 인출 기반 답변을 반환합니다.

[Website](https://claudianus.github.io/maru-search/) · [PyPI](https://pypi.org/project/maru-search/) · [GitHub](https://github.com/claudianus/maru-search)

```bash
pip install maru-search
```

## Install / 설치

```bash
pip install maru-search
```

## Connect / 연결

**Claude Code:**
```bash
claude mcp add maru-search pip:maru-search
```

**Cursor / VS Code / Windsurf:**
```json
{
  "mcpServers": {
    "maru-search": {
      "command": "python3",
      "args": ["-m", "maru_search.server"]
    }
  }
}
```

## Tools / 도구

| Tool | English | 한국어 |
|------|---------|--------|
| `answer` | Direct cited answer | 인출 기반 직접 답변 |
| `web_search` | Scrape search engines, ranked results with citation IDs | 검색엔진 스크래핑, 인출 ID 포함 순위 결과 |
| `search_with_citations` | Search with pre-numbered citations | 사전 번호 인출 검색 |
| `fetch_page` | Extract clean content from a single URL | 단일 URL 콘텐츠 추출 |
| `fetch_bulk` | Fetch multiple URLs in parallel | 다중 URL 병렬 페치 |
| `deep_research` | Auto-expand query, crawl top results, synthesize with citations | 쿼리 자동 확장, 상위 결과 크롤링, 인출 기반 종합 |
| `stealthy_fetch` | Full anti-bot bypass for protected sites | 보호된 사이트용 안티봇 우회 |
| `parallel_search` | Run multiple searches simultaneously | 다중 검색 동시 실행 |

**Quick decision tree:**
- Need a quick answer? / 빠른 답변이 필요한가? → `answer`
- Need sources? / 출처가 필요한가? → `web_search` or / 또는 `search_with_citations`
- Have URLs? / URL이 이미 있는가? → `fetch_page` or / 또는 `fetch_bulk`
- Blocked? / 차단되었는가? → `fetch_page` with `stealth=True`, then / 그래도 안되면 `stealthy_fetch`
- Deep dive? / 심층 분석이 필요한가? → `deep_research`

## What makes it different / 차별점

- **100% free / 묣은 API 없음** — No OpenAI, no Google API, no Bing API. Only direct scraping. 오직 직접 스크래핑만 사용.
- **Citations / 인출** — Every result gets a `[1]`, `[2]` ID. 모든 결과에 인출 ID 부여.
- **Multi-engine / 다중 엔진** — `SearchEngineRegistry` makes adding new scrapers trivial. 새 스크래퍼 추가가 간단함.
- **BM25 ranking / BM25 순위** — Local relevance scoring + authority/freshness metadata. 로컬 관련성 점수 + 권위도/최신성 메타데이터.
- **Code-aware / 코드 인식** — Detects 21 languages, extracts API signatures. 21개 언어 감지, API 시그니처 추출.

## Architecture / 아키텍처

```
src/maru_search/
├── server.py        # MCP server (8 tools, 3 prompts)
├── config.py        # Runtime config via env vars
├── tools.py         # Tool implementations + registry
├── engines/
│   ├── registry.py  # SearchEngineRegistry (factory)
│   ├── base.py      # SearchEngine ABC
│   └── duckduckgo.py
├── research/
│   ├── deep.py      # Deep research + answer synthesis
│   ├── ranker.py    # BM25 + metadata ranking
│   └── expander.py  # Query expansion
├── extraction/
│   ├── code.py      # 21-language detection
│   └── content.py   # Token-aware truncation
└── utils/
    ├── url.py       # URL normalize / filter / dedupe
    └── retry.py     # Exponential backoff
```

## Configuration / 설정

Environment variables / 환경 변수 (all optional / 모두 선택적):

| Variable / 변수 | Default / 기본값 | Description / 설명 |
|-----------------|------------------|--------------------|
| `MARU_SEARCH_ENGINE` | `duckduckgo_lite` | Default search engine / 기본 검색 엔진 |
| `MARU_SEARCH_MAX_RESULTS` | `10` | Max results per query / 쿼리당 최대 결과 |
| `MARU_SEARCH_MAX_CONCURRENT` | `5` | Parallel fetch limit / 병렬 페치 제한 |
| `MARU_SEARCH_MAX_TOKENS_SOURCE` | `2500` | Token budget per source / 소스당 토큰 예산 |
| `MARU_SEARCH_MAX_TOKENS_TOTAL` | `20000` | Total output token budget / 총 출력 토큰 예산 |
| `MARU_SEARCH_TIMEOUT` | `30.0` | Fetch timeout (seconds) / 페치 타임아웃 (초) |
| `MARU_SEARCH_RETRIES` | `3` | Retry attempts / 재시도 횟수 |

## Testing / 테스트

```bash
pytest tests/ -v
```

124 tests, all passing / 124개 테스트 전부 통과.

## Dependencies / 의존성

- [Scrapling](https://github.com/D4Vinci/Scrapling) — browser/HTTP fetching / 브라우저/HTTP 페치
- [trafilatura](https://trafilatura.readthedocs.io/) — content extraction / 콘텐츠 추출
- [htmldate](https://htmldate.readthedocs.io/) — publication dates / 게시 날짜 추출
- [rank-bm25](https://github.com/dorianbrown/rank_bm25) — local relevance scoring / 로컬 관련성 점수
- [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) — MCP protocol / MCP 프로토콜

## License / 라이선스

MIT
