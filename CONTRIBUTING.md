# Contributing to maru-deep-pro-search

Thank you for your interest in contributing! This document provides guidelines for participating in the project.

## Development Setup

```bash
# Clone the repository
git clone https://github.com/claudianus/maru-deep-pro-search.git
cd maru-deep-pro-search

# Install with dev dependencies
uv pip install -e ".[dev]"

# Or use the install script
bash scripts/install.sh
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/maru_deep_pro_search --cov-report=term-missing

# Run specific test file
pytest tests/test_sanitize.py -v
```

## Code Style

- Python 3.10+ syntax: use `| None` instead of `Optional`, `list[str]` instead of `List[str]`
- Follow PEP 8 with line length 100
- Add type hints for all public functions
- Docstrings use Google style

## Adding a New Search Engine

1. Create `src/maru_deep_pro_search/engines/<name>.py`
2. Inherit from `BaseEngine` and implement `search()` and `fetch()`
3. Register in `engines/registry.py` `_register_builtins()`
4. Add tests in `tests/test_engines.py`
5. Update README.md engine table and docs/index.html

## Adding a New Agent Adapter

1. Create `src/maru_deep_pro_search/cli/agents/<name>.py`
2. Inherit from `BaseAgentAdapter` and implement `install()`, `inject_rules()`, `detect()`
3. Register in `cli/setup.py` `ADAPTER_REGISTRY`
4. Update README.md architecture diagram and docs/index.html

## Adding Security Signatures

1. Add regex patterns to `utils/sanitize.py` `_compile_signatures()`
2. Include multi-language variants where relevant
3. Add test cases in `tests/test_sanitize.py`
4. Update README.md signature count

## Pull Request Process

1. Fork the repository and create a feature branch
2. Make your changes with clear commit messages
3. Ensure all tests pass
4. Update documentation (README.md, docs/index.html, CHANGELOG.md)
5. Submit a PR using the provided template

## Release Process

> ⚠️ **Do NOT manually publish to PyPI.** All releases are automated via GitHub Actions.

To create a release:
1. Update `CHANGELOG.md` with the new version
2. Update version in `pyproject.toml`
3. Push a git tag: `git tag v0.x.x && git push origin v0.x.x`
4. GitHub Actions will build and publish to PyPI automatically

## Questions?

Open a [GitHub Discussion](https://github.com/claudianus/maru-deep-pro-search/discussions) or reach out via issues.
