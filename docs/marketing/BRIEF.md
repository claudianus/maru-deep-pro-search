# 마케팅 브리프 (내부)

> 톤: 전문 · 수치 · $0 · API 키 없음. 과장·허위 벤치 금지.

## 포지셔닝

**코딩 전 리서치를 기술적으로 강제하는** 무료 MCP 하네스. Perplexity/Tavily 대체가 아니라 **에이전트가 소비하는 조사 패킷** 공급.

## v0.22.1 핵심 메시지

1. **Granite 97M R2** — 기본 임베딩 `ibm-granite/granite-embedding-97m-multilingual-r2`, opt-out 없음.
2. **install 시 warmup** — `install.sh` / `setup` → `warmup-embeddings`로 HF 가중치 선다운로드.
3. **Research Trace · Insights · Clusters** — 호스트 LLM이 종합할 구조화 패킷 (서버 LLM 없음).
4. **9엔진 · P@5 +86%** — README/CHANGELOG 벤치 수치와 일치할 때만 사용.

## IA (GitHub Pages)

| 섹션 | 카피 담당 | 스크린샷 |
|------|-----------|----------|
| Hero | Brand | `@panel:tech_compare` (live HTML) |
| Product tour | Product Mkt | 6 panels (trace, answer, signals, granite, warmup, compare) |
| Compare | TPM | `compare_split`, `quality_signals` panels |
| Playbook | UX | `korean_market` panel + synthesis 발췌 |
| Install | UX | `setup_flow` panel |
| OG / Twitter | Brand | `og-card@2x.png` only (Playwright) |
| What's new | TPM | `embedding` |

## 금지

- fixture에 없는 URL·점수·인용 invent
- “항상 Perplexity보다 낫다” 류 절대 표현
- v0.20 이하 버전 번호 잔존

## KO/EN

`docs/index.html` `toggleLang()` — 신규 문단은 `.ko` / `.en.hidden` 쌍 필수.
