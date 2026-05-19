# 마케팅 패널·OG 이미지 재생성

GitHub Pages 본문은 **라이브 HTML 패널** (fixture → embed). **PNG는 `og:image` 한 장만** Playwright.

## 1. Fixture 캡처 (live, 네트워크)

```bash
uv run python scripts/capture_marketing_fixtures.py
```

출력: `docs/fixtures/raw/`, `synthesis/`, `manifest.json`

## 2. HTML 패널 임베드 (Pages 본문)

PNG `<img>` 블록이 남아 있으면 (main 복원 직후 등):

```bash
uv run python scripts/patch_index_markers.py
```

```bash
uv run python scripts/embed_marketing_panels.py
```

출력:

- `docs/partials/panels/{id}.html` — 조각 (재사용·디버그)
- `docs/assets/marketing/panels.css` — 스코프 CSS
- `docs/index.html` — `<!--@panel:ID@-->` 마커를 **인라인 HTML**로 치환

마커만 두고 fetch 로딩:

```bash
uv run python scripts/embed_marketing_panels.py --fetch
```

## 3. OG 카드 PNG (소셜 프리뷰만)

```bash
uv pip install playwright
playwright install chromium
uv run python scripts/render_marketing_screenshots.py
```

→ `docs/assets/screenshots/og-card@2x.png`

## 릴리스마다

1. fixture 캡처 → `embed_marketing_panels.py` → (선택) `render_marketing_screenshots.py`
2. `manifest.json` `captured_at` 확인
3. `ruff check scripts/marketing_panels.py scripts/embed_marketing_panels.py scripts/capture_marketing_fixtures.py`
