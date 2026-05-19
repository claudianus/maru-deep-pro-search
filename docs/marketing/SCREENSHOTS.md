# 마케팅 스크린샷 재생성

실제 MCP 출력 → HTML 템플릿 → Playwright PNG (WebP 미지원 시 PNG 사용).

## 요구 사항

- Python 3.10+, 네트워크 (fixture 캡처)
- `uv sync --all-groups` 후:

```bash
uv pip install playwright
playwright install chromium
```

또는:

```bash
pip install -r scripts/requirements-marketing.txt
playwright install chromium
```

## 1. Fixture 캡처 (live)

```bash
uv run python scripts/capture_marketing_fixtures.py
```

출력:

- `docs/fixtures/raw/{id}.md`
- `docs/fixtures/synthesis/{id}.md`
- `docs/fixtures/manifest.json`

실패한 ID만:

```bash
uv run python scripts/capture_marketing_fixtures.py --only embedding
```

## 2. 스크린샷 렌더

```bash
uv run python scripts/render_marketing_screenshots.py
```

출력 (`docs/assets/screenshots/`):

| 파일 | 용도 |
|------|------|
| `tech_compare@2x.png` | Hero, Research Trace |
| `korean_market@2x.png` | answer 카드 |
| `quality_signals@2x.png` | 출처 메타 |
| `embedding@2x.png` | Granite |
| `setup_flow@2x.png` | install / warmup |
| `compare_split@2x.png` | vs 내장 검색 |
| `og-card@2x.png` | og:image (1200×630) |

## 3. Pages 반영

`docs/index.html`에서 `<img src="assets/screenshots/...">` 경로 확인 후 `main` 머지 → GitHub Pages workflow.

## 릴리스마다

1. `manifest.json` `captured_at` 갱신 확인
2. 스크린샷 내 `[N]`·도메인이 raw fixture와 일치하는지 눈으로 검수
3. `ruff check scripts/capture_marketing_fixtures.py scripts/render_marketing_screenshots.py`
