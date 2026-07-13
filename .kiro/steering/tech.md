# Technical Stack Constraints

## Language & Runtime
- Python 3.11+ (required for modern type syntax)
- uv as package manager (pyproject.toml with PEP 621)

## Core Frameworks
- **FastAPI** — API layer (async, Pydantic v2 native)
- **LangGraph** — Orchestration state machine (StateGraph, conditional edges)
- **Strands Agents SDK** — Worker agents with @tool decorator pattern
- **Pydantic v2** — All data contracts (strict=True, custom validators)
- **pydantic-settings** — Configuration from environment variables

## Data Infrastructure
- **Neo4j 5** — Graph database for fraud network (Cypher queries, APOC)
- **DuckDB** — Analytical warehouse for ELT staging
- **dbt-core + dbt-duckdb** — Data transformation pipeline

## Cloud (Production)
- **AWS ECS Fargate** — Container hosting
- **Amazon Neptune** (or Neo4j Aura) — Managed graph database
- **Amazon Bedrock** — LLM provider (Claude, Titan)
- **Amazon S3** — Raw data staging and audit log storage
- **Terraform** — Infrastructure as Code

## Quality Tooling
- **Ruff** — Linting and formatting (strict rule set)
- **Mypy** — Static type checking (strict mode)
- **pytest** — Testing framework
- **Hypothesis** — Property-based testing
- **pytest-archon** — Architecture boundary enforcement

## Constraints
- Domain layer imports ONLY stdlib and pydantic
- All external I/O goes through Port interfaces
- No openai package — use httpx for OpenAI-compatible APIs
- All Cypher queries must be parameterized (no string interpolation)
- LLM tool execution restricted to read-only operations
