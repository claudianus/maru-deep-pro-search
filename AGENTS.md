# Agent Instructions for clco-deep-research-mcp

> **CRITICAL REMINDER**: PyPI deployment is handled **automatically by GitHub Actions**. Do NOT attempt manual PyPI uploads via `twine`.

## Deployment Workflow

### PyPI Publishing (AUTOMATED)

The project uses **GitHub Actions** with **trusted publishing** to deploy to PyPI automatically:

- **Trigger**: Push a git tag starting with `v` (e.g., `v0.4.0`)
- **Workflow**: `.github/workflows/publish.yml`
- **Method**: Trusted publishing (no API tokens needed)

**To release a new version:**

```bash
# 1. Update version in pyproject.toml
# 2. Update CHANGELOG.md
# 3. Commit and push to main
git add -A && git commit -m "feat: v0.4.0 - description"
git push origin main

# 4. Create and push a version tag (this triggers PyPI deployment)
git tag v0.4.0
git push origin v0.4.0
```

**What happens next:**
1. GitHub Actions workflow `publish.yml` triggers automatically
2. Builds sdist and wheel with `uv build`
3. Publishes to PyPI with `uv publish --trusted-publishing always`
4. Package appears on https://pypi.org/project/clco-deep-research-mcp/

### DO NOT

- ❌ Run `twine upload` manually
- ❌ Store PyPI API tokens locally
- ❌ Create `.pypirc` files
- ❌ Attempt direct uploads from local machine

### GitHub Pages Deployment

GitHub Pages is automatically deployed from the `docs/` directory on every push to `main`.

## Version Bump Checklist

Before creating a new release tag:

- [ ] Update `version` in `pyproject.toml`
- [ ] Update `CHANGELOG.md` with new version section
- [ ] Update version badge in `docs/index.html` (hero badge)
- [ ] Update test count in `docs/index.html` if changed
- [ ] Update test count in `README.md` if changed
- [ ] Run full test suite: `pytest tests/ -v` (all must pass)
- [ ] Commit all changes
- [ ] Push to `main`
- [ ] Create and push version tag: `git tag vX.Y.Z && git push origin vX.Y.Z`
- [ ] Verify GitHub Actions workflow succeeds
- [ ] Verify PyPI page shows new version

## Project Structure Reminders

```
src/clco_deep_research/
├── server.py              # MCP server + prompts
├── tools.py               # 6 MCP tools + TOOL_GUIDANCE
├── engines/               # Search engine implementations
├── extraction/            # Content extraction utilities
├── research/              # Deep research pipeline
└── utils/                 # URL, retry utilities
```

## Testing

Always run tests before committing:

```bash
source .venv/bin/activate
pytest tests/ -v
```

**Current requirement**: 113 tests, all passing.

## Key Architecture Decisions

1. **No manual PyPI uploads** — GitHub Actions handles this
2. **Trusted publishing** — Modern secure PyPI authentication (no tokens)
3. **uv for build/publish** — Fast, reliable Python packaging
4. **Tag-based releases** — Semantic versioning via git tags
