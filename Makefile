.PHONY: install lint format build clean docs help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## Install package with dev dependencies
	uv pip install -e ".[dev]"

lint: ## Run ruff linter
	ruff check src/

format: ## Format code with ruff
	ruff format src/

format-check: ## Check code formatting
	ruff format --check src/

typecheck: ## Run mypy type checker
	mypy src/maru_deep_pro_search --ignore-missing-imports

build: ## Build package for distribution
	rm -rf dist/
	uv build

clean: ## Remove build artifacts
	rm -rf dist/ build/ *.egg-info .mypy_cache

docs-serve: ## Serve documentation locally (if docs server exists)
	cd docs && python -m http.server 8080
