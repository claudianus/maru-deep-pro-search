# Roadmap

This document outlines planned features and improvements. For the latest shipped changes, see [CHANGELOG.md](./CHANGELOG.md).

## Short Term (0.9.x)

- [x] **3-layer real research enforcement** — Server gate + client hooks + tool dependency (Layer 1 & 2 done)
- [ ] **Layer 3 tool dependency** — `generate_code(research_id=...)` requiring valid research tokens
- [ ] **Browser automation engine** — Playwright-based engine for JavaScript-heavy sites
- [ ] **Result caching TTL** — Configurable cache expiration in KnowledgeStore
- [ ] **Search result previews** — Inline snippet preview in CLI output
- [ ] **More agent adapters** — VS Code native, VIM/Neovim plugins, Emacs

## Medium Term (0.10.x)

- [ ] **Plugin marketplace** — Community-contributed search engines and adapters
- [ ] **Distributed knowledge** — Sync KnowledgeStore across team members
- [ ] **Result clustering** — Group related results by topic automatically
- [ ] **Custom ranking models** — User-defined scoring weights per project
- [ ] **GraphRAG integration** — Knowledge graph construction from search results

## Long Term (1.0.0)

- [ ] **Stable API** — Freeze public interfaces, semantic versioning guarantee
- [ ] **Full test coverage** — >90% code coverage across all modules
- [ ] **Performance benchmarks** — Published benchmark suite against Perplexity, SerpAPI
- [ ] **Enterprise features** — SSO, audit log streaming, centralized policy management

## Under Consideration

- [ ] **LLM-based query expansion** — Use local LLM for smarter query reformulation
- [ ] **Multi-modal search** — Image and video result support
- [ ] **Real-time search** — WebSocket-based live result streaming
- [ ] **Mobile app** — iOS/Android companion for on-the-go research

## Completed ✅

- [x] 10-engine failover cluster
- [x] Academic search engine (ArXiv + Semantic Scholar)
- [x] 72-layer prompt injection defense
- [x] MCP audit logging with anomaly detection
- [x] Docker sandbox support
- [x] 19 agent adapters
- [x] 3-layer real research enforcement (server + client hooks)
- [x] KnowledgeStore SQLite caching
- [x] BM25 + semantic hybrid ranking
