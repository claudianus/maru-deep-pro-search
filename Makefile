.PHONY: install test lint format build clean docs help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install package with dev dependencies
	uv pip install -e ".[dev,semantic]"

test: ## Run all tests
	pytest tests/ -v

test-cov: ## Run tests with coverage report
	pytest --cov=src/maru_deep_pro_search --cov-report=term-missing

lint: ## Run ruff linter
	ruff check src/ tests/

format: ## Format code with ruff
	ruff format src/ tests/

format-check: ## Check code formatting
	ruff format --check src/ tests/

typecheck: ## Run mypy type checker
	mypy src/maru_deep_pro_search --ignore-missing-imports

build: ## Build package for distribution
	rm -rf dist/
	uv build

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info .pytest_cache .coverage .mypy_cache

docs-serve: ## Serve documentation locally (if docs server exists)
	cd docs && python -m http.server 8080
