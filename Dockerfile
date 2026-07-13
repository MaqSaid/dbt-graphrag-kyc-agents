# Base stage with dependencies
FROM python:3.11-slim AS base
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-dev --no-editable 2>/dev/null || uv sync --no-dev

COPY src/ ./src/
COPY dbt_kyc/ ./dbt_kyc/

# Production stage
FROM base AS production
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import httpx; r = httpx.get('http://localhost:8000/api/v1/health'); r.raise_for_status()" || exit 1
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# Test stage
FROM base AS test
RUN uv sync --frozen 2>/dev/null || uv sync
COPY tests/ ./tests/
CMD ["pytest", "tests/", "-v", "--cov=src", "--cov-report=term-missing"]
