"""Application and decision configuration schemas."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings


class DecisionConfig(BaseModel):
    """Configurable decision thresholds and scoring weights."""

    model_config = ConfigDict(strict=True)

    approval_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    denial_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    identity_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    sanctions_weight: float = Field(default=0.4, ge=0.0, le=1.0)
    network_weight: float = Field(default=0.3, ge=0.0, le=1.0)
    fuzzy_match_threshold: float = Field(default=0.85, ge=0.0, le=1.0)
    ambiguity_lower_bound: float = Field(default=0.70, ge=0.0, le=1.0)


class AppConfig(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = ConfigDict(env_prefix="KYC_", env_nested_delimiter="__")

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_auth: str = "neo4j/development"

    # AWS
    aws_region: str = "us-east-1"
    audit_bucket: str = "kyc-audit-logs"

    # DuckDB
    duckdb_path: str = "./data/warehouse.duckdb"

    # LLM
    default_llm_model: str = "anthropic.claude-sonnet-4-20250514"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    token_budget_per_evaluation: int = 50000

    # Registry
    registry_endpoint: str = "http://localhost:8001/registry"

    # Watchlist sources
    watchlist_sources: list[str] = Field(
        default=["ofac_sdn", "eu_sanctions", "un_sanctions", "pep"]
    )

    # Timeouts (seconds)
    identity_timeout: int = 10
    sanctions_timeout: int = 15
    graph_timeout: int = 20
    report_timeout: int = 30

    # Rate limiting
    rate_limit_per_minute: int = 100
    max_payload_size_bytes: int = 1_048_576  # 1MB

    # Resilience
    max_retries: int = 3
    circuit_breaker_threshold: int = 5
    circuit_breaker_recovery_seconds: int = 60

    # Decision config
    decision: DecisionConfig = Field(default_factory=DecisionConfig)
