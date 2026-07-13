.PHONY: help install lint format typecheck test test-unit test-integration test-property test-architecture test-security test-quality test-e2e test-all build run docker-up docker-down docker-test dbt-run dbt-test clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install all dependencies (dev included)
	uv sync

lint: ## Run Ruff linter
	uv run ruff check src/ tests/

format: ## Format code with Ruff
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

typecheck: ## Run Mypy strict type checking
	uv run mypy src/ --strict

test: ## Run unit tests with coverage
	uv run pytest tests/unit/ --cov=src --cov-report=term-missing

test-unit: ## Run unit tests only
	uv run pytest tests/unit/ -v

test-integration: ## Run integration tests (requires Docker)
	uv run pytest tests/integration/ -v

test-property: ## Run property-based tests
	uv run pytest tests/property/ -v --hypothesis-seed=0

test-architecture: ## Run architecture boundary tests
	uv run pytest tests/architecture/ -v

test-security: ## Run security guardrail tests
	uv run pytest tests/security/ -v

test-quality: ## Run code quality assertion tests
	uv run pytest tests/quality/ -v

test-e2e: ## Run end-to-end pipeline tests
	uv run pytest tests/e2e/ -v

test-all: ## Run complete test suite with coverage
	uv run pytest tests/ --cov=src --cov-report=term-missing --cov-report=html

build: ## Build Docker production image
	docker build --target production -t kyc-pipeline:latest .

run: ## Run the application locally
	uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

docker-up: ## Start development services (Neo4j)
	docker compose up -d
	@echo "Neo4j Browser: http://localhost:7474"
	@echo "Bolt: bolt://localhost:7687"

docker-down: ## Stop development services
	docker compose down

docker-test: ## Start test infrastructure
	docker compose -f docker-compose.test.yml up -d
	@echo "Test Neo4j Bolt: bolt://localhost:7688"

dbt-run: ## Execute dbt transformations
	cd dbt_kyc && uv run dbt run

dbt-test: ## Run dbt tests
	cd dbt_kyc && uv run dbt test

clean: ## Remove build artifacts and caches
	rm -rf dist/ build/ *.egg-info .coverage htmlcov/ .mypy_cache/ .ruff_cache/ .hypothesis/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
