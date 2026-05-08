# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2026-05-08

### Added
- Query expansion: 3-5 orthogonal subqueries for broader coverage
- Relevance scoring: Authority + content type + freshness + position
- Structured exception hierarchy: 7 exception classes with retry hints
- Fault-tolerant CSS selectors with multiple fallbacks
- Package detection: Extract package/library references from code
- URL normalization and filtering utilities
- Exponential backoff retry mechanism
- 21 language detection (up from 16)
- New test suite: 68 tests (up from 35)
- GitHub Pages website

### Changed
- Improved deep research pipeline with multi-pass crawling
- Enhanced error handling with engine fallback
- Better content extraction with trafilatura
- Updated README with v0.3.0 features

## [0.2.2] - 2025-05-07

### Added
- Initial test suite (35 tests)
- Code-aware analysis module
- DuckDuckGo SERP scraping
- Basic deep research pipeline

## [0.2.0] - 2025-05-07

### Added
- Initial release
- 6 MCP tools: web_search, fetch_page, fetch_bulk, deep_research, stealthy_fetch, parallel_search
- Scrapling integration
- trafilatura content extraction
