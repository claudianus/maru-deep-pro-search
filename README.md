<p align="center">
  <a href="https://claudianus.github.io/clco-deep-research-mcp/">🌐 Website</a> •
  <a href="https://pypi.org/project/clco-deep-research-mcp/">📦 PyPI</a> •
  <a href="https://github.com/claudianus/clco-deep-research-mcp">⭐ GitHub</a>
</p>

<p align="center">
  <img src="https://img.shields.io/pypi/v/clco-deep-research-mcp?color=blue&label=PyPI" alt="PyPI">
  <img src="https://img.shields.io/pypi/pyversions/clco-deep-research-mcp?color=green" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-purple" alt="License">
  <img src="https://img.shields.io/badge/MCP-native-blue" alt="MCP Native">
  <img src="https://img.shields.io/badge/engines-4-orange" alt="4 Search Engines">
  <img src="https://img.shields.io/badge/cost-free-brightgreen" alt="Free">
</p>

<h1 align="center">clco-deep-research-mcp</h1>

<p align="center">
  <strong>🇰🇷 코딩 에이전트를 위한 묣은 딥리서치 MCP</strong> | <strong>🇺🇸 Free Deep Research MCP for Coding Agents</strong>
</p>

<p align="center">
  Claude Code의 <code>web_search</code>를 완전히 대체합니다 | Replaces Claude Code's built-in <code>web_search</code><br>
  API 키 불필요, 완전 묣이 | Zero API keys required, completely free
</p>

---

## 🚀 Quick Start | 빠른 시작

```bash
# Install globally | 전역 설치
pip install clco-deep-research-mcp

# Run | 실행
python3 -m clco_deep_research.server
```

---

## 🔧 Client Configuration | 클라이언트 설정

### Claude Code (`~/.claude.json`)

```json
{
  "mcpServers": {
    "clco-deep-research": {
      "command": "python3",
      "args": ["-m", "clco_deep_research.server"]
    }
  }
}
```

### Cursor (`.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "clco-deep-research": {
      "command": "python3",
      "args": ["-m", "clco_deep_research.server"]
    }
  }
}
```

### VS Code (`.vscode/mcp.json`)

```json
{
  "servers": {
    "clco-deep-research": {
      "type": "stdio",
      "command": "python3",
      "args": ["-m", "clco_deep_research.server"]
    }
  }
}
```

### Windsurf (`.windsurf/mcp_config.json`)

```json
{
  "mcpServers": {
    "clco-deep-research": {
      "command": "python3",
      "args": ["-m", "clco_deep_research.server"]
    }
  }
}
```

---

## 🛠️ Tools | 도구 (6)

| Tool | 🇰🇷 설명 | 🇺🇸 Description | Key Feature |
|------|---------|------------------|-------------|
| `web_search` | 검색엔진 직접 스크래핑 | Scrape search engines directly | Content type hints + authority badges |
| `fetch_page` | URL에서 깨끗한 콘텐츠 추출 | Extract clean content from any URL | trafilatura + code-aware metadata |
| `fetch_bulk` | 병렬 다중 URL fetch | Parallel multi-URL fetch | Quality signals for LLM prioritization |
| `deep_research` | 쿼리 확장이 있는 전체 파이프라인 | Full pipeline with query expansion | Multi-angle research + synthesis |
| `stealthy_fetch` | 완전한 안티봇 우회 | Full anti-bot bypass | Cloudflare Turnstile, DataDome |
| `parallel_search` | 병렬 다중 쿼리 검색 | Multiple queries in parallel | Multi-engine scatter-gather |

---

## 🔄 Deep Research Pipeline | 딥리서치 파이프라인

```
Query | 쿼리
  ↓
[Query Expansion | 쿼리 확장] → 3-5 orthogonal subqueries | 직교 하위 쿼리
  ↓
[Parallel Search | 병렬 검색] → Execute across engines | 다중 엔진 실행
  ↓
[Deduplication | 중복 제거] → URL normalization + content hashing
  ↓
[Relevance Scoring | 관련성 스코어링] → Authority + type + freshness + position
  ↓
[Multi-Pass Crawling | 다중 패스 크롤링] → BFS with depth limit | 깊이 제한 BFS
  ↓
[Content Extraction | 콘텐츠 추출] → trafilatura + code-aware + structured data
  ↓
[Synthesis | 종합] → Aggregate by topic with confidence scores | 주제별 신뢰도 점수
  ↓
[Formatting | 포맷팅] → Markdown with quality badges + relevance scores
```

---

## 🏗️ Architecture | 아키텍처

```
src/clco_deep_research/
├── server.py              # MCP server (stdio) | MCP 서버
├── exceptions.py          # Structured error hierarchy | 구조화된 예외 계층
├── tools.py               # 6 MCP tools | 6개 MCP 도구
├── engines/
│   ├── base.py            # Abstract engine interface | 추상 엔진 인터페이스
│   └── duckduckgo.py      # DuckDuckGo (improved selectors) | 개선된 선택자
├── extraction/
│   ├── content.py         # trafilatura wrapper | trafilatura 래퍼
│   └── code.py            # Code-aware analysis (21 languages) | 코드 인식 분석
├── research/
│   ├── deep.py            # Deep research pipeline | 딥리서치 파이프라인
│   └── expander.py        # Query expansion | 쿼리 확장
└── utils/
    ├── retry.py           # Exponential backoff | 지수 백오프
    └── url.py             # URL normalization/filtering | URL 정규화/필터링
```

---

## 🎯 Code-Aware Metadata | 코드 인식 메타데이터

Every fetched page is analyzed for coding-agent relevance | 가져온 모든 페이지는 코딩 에이전트 관련성을 위해 분석됩니다:

```markdown
### [1] Async Context Managers in Python [HIGH] [API-REF] [python] [code-heavy 32%] [293d ago] [AUTHORITY]
URL: https://dev.to/...
_relevance: 5.3_
_APIs: async def __aenter__(self):; async def __aexit__(...):_
_Packages: aiohttp (python), fastapi (python)_
```

| Signal | 🇰🇷 의미 | 🇺🇸 Meaning |
|--------|---------|------------|
| `[HIGH]` | trafilatura 품질 점수 — 이 소스 우선순위 지정 | trafilatura quality score — prioritize this source |
| `[API-REF]` | 콘텐츠 유형 분류 | Content type classification |
| `[python]` | 코드 블록에서 감지된 언어 | Detected languages from code blocks |
| `[code-heavy 32%]` | 코드-텍스트 비율 — 훑어보기 vs 깊이 읽기 | Code-to-text ratio — skim vs deep-read |
| `[293d ago]` | 최신성 — 1년 이상 지난 경우 경고 | Freshness — warn if >1yr stale |
| `[AUTHORITY]` | 알려진 고품질 도메인에서 | From known high-quality domain |
| `APIs:` | 빠른 스캔을 위한 함수/클스 시그니처 | Function/class signatures for quick scanning |
| `Packages:` | 언어가 포함된 패키지/라이브러리 참조 | Package/library references with language |

---

## 🧪 Testing | 테스트

```bash
# Run all tests | 모든 테스트 실행
pytest tests/ -v

# Run specific test file | 특정 테스트 파일 실행
pytest tests/test_query_expansion.py -v
```

**Current coverage | 현재 커버리지**: 68 tests, all passing | 68개 테스트, 모두 통과

---

## 📦 Tech Stack | 기술 스택

| Library | Version | 🇰🇷 목적 | 🇺🇸 Purpose |
|---------|---------|---------|------------|
| [Scrapling](https://github.com/D4Vinci/Scrapling) | ≥0.2.0 | 브라우저/HTTP 가져오기, 안티봇 | Browser/HTTP fetching, anti-bot |
| [trafilatura](https://trafilatura.readthedocs.io/) | ≥2.0.0 | 주요 콘텐츠 추출 (SOTA) | Main content extraction (SOTA) |
| [htmldate](https://htmldate.readthedocs.io/) | ≥1.9.4 | 게시 날짜 추출 | Publication date extraction |
| [Pygments](https://pygments.org/) | ≥2.20.0 | 구문 강조 (참조) | Syntax highlighting (reference) |
| [MCP SDK](https://github.com/modelcontextprotocol/python-sdk) | ≥1.0.0 | Model Context Protocol 서버 | Model Context Protocol server |

---

## ⚠️ Error Handling | 오류 처리

Structured exceptions help the LLM decide what to do | 구조화된 예외는 LLM이 무엇을 할지 결정하도록 돕습니다:

```python
NetworkError("timeout")        # retryable=True, auto-retry with backoff | 자동 재시도
BlockedError("captcha")        # retryable=True, fallback to duckduckgo_lite | 대체 엔진
ParseError("selectors broken") # retryable=True, fallback to duckduckgo_lite | 대체 엔진
NoResultsError("empty")        # retryable=False, suggest query refinement | 쿼리 개선 제안
```

---

## 📄 License | 라이선스

MIT — use it, fork it, ship it. Built for the coding agent era.

MIT — 사용하고, 포크하고, 배포하세요. 코딩 에이전트 시대를 위해 만들어졌습니다.

---

<p align="center">
  <sub>Made for <a href="https://github.com/claudianus/clco-helper">clco-helper</a> — the Claude Code power tool | Claude Code 파워 툴</sub>
</p>
