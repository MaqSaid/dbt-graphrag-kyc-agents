"""Dependency injection container for the KYC pipeline.

Constructs and wires all services, ports, and adapters at application startup.
Supports adapter swapping via configuration for different environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.domain.ports.audit_log_port import AuditLogPort
from src.domain.ports.customer_registry_port import CustomerRegistryPort
from src.domain.ports.graph_database_port import GraphDatabasePort
from src.domain.ports.llm_client_port import LLMClientPort
from src.domain.ports.warehouse_port import WarehousePort
from src.domain.ports.watchlist_port import WatchlistPort
from src.domain.schemas.config import AppConfig

if TYPE_CHECKING:
    pass


@dataclass(frozen=True)
class Container:
    """Dependency injection container holding all port implementations.

    All port dependencies are wired at startup. Services consume ports
    via constructor injection from this container.

    Attributes:
        graph_db: Graph database adapter (Neo4j/Neptune).
        llm_client: LLM provider adapter (Bedrock/OpenAI).
        watchlist: Watchlist/sanctions data adapter.
        audit_log: Audit log storage adapter.
        warehouse: DuckDB warehouse adapter.
        customer_registry: Government registry adapter.
        config: Application configuration.
    """

    graph_db: GraphDatabasePort
    llm_client: LLMClientPort
    watchlist: WatchlistPort
    audit_log: AuditLogPort
    warehouse: WarehousePort
    customer_registry: CustomerRegistryPort
    config: AppConfig


def build_container(config: AppConfig | None = None) -> Container:
    """Construct the DI container from configuration.

    Adapter selection is driven by configuration, enabling swapping between
    production adapters (Neo4j, Bedrock) and test adapters (InMemory mocks).

    Args:
        config: Application configuration. Uses defaults if None.

    Returns:
        Fully wired Container with all adapters instantiated.

    Raises:
        ValueError: If required configuration values are missing.
    """
    if config is None:
        config = AppConfig()

    # Import adapters (infrastructure layer)
    from src.infrastructure.adapters.bedrock_adapter import BedrockAdapter
    from src.infrastructure.adapters.duckdb_adapter import DuckDBAdapter
    from src.infrastructure.adapters.neo4j_adapter import Neo4jAdapter
    from src.infrastructure.adapters.registry_adapter import RegistryAdapter
    from src.infrastructure.adapters.s3_audit_log_adapter import S3AuditLogAdapter
    from src.infrastructure.adapters.watchlist_api_adapter import WatchlistAPIAdapter

    # Parse Neo4j auth
    neo4j_user, neo4j_pass = config.neo4j_auth.split("/", 1) if "/" in config.neo4j_auth else ("neo4j", config.neo4j_auth)

    return Container(
        graph_db=Neo4jAdapter(
            uri=config.neo4j_uri,
            username=neo4j_user,
            password=neo4j_pass,
        ),
        llm_client=BedrockAdapter(region=config.aws_region),
        watchlist=WatchlistAPIAdapter(sources=config.watchlist_sources),
        audit_log=S3AuditLogAdapter(bucket=config.audit_bucket),
        warehouse=DuckDBAdapter(db_path=config.duckdb_path),
        customer_registry=RegistryAdapter(endpoint=config.registry_endpoint),
        config=config,
    )


def build_test_container() -> Container:
    """Build a container with in-memory/mock adapters for testing.

    Returns:
        Container configured for unit and integration testing.
    """
    config = AppConfig(
        neo4j_uri="bolt://localhost:7688",
        neo4j_auth="neo4j/testpassword",
        duckdb_path=":memory:",
        audit_bucket="test-audit",
        registry_endpoint="http://localhost:8001/registry",
    )

    # For tests, use the same adapters but with test configuration
    return build_container(config)
