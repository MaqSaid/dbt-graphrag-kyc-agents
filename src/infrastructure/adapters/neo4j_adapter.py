"""Neo4j adapter implementing GraphDatabasePort.

Provides graph database operations using parameterized Cypher queries
with circuit breaker protection and retry logic.
"""

from __future__ import annotations

from neo4j import AsyncGraphDatabase, AsyncDriver

from src.domain.exceptions import GraphConnectionError
from src.domain.ports.graph_database_port import GraphDatabasePort
from src.infrastructure.resilience.circuit_breaker import CircuitBreaker


class Neo4jAdapter(GraphDatabasePort):
    """Concrete Neo4j implementation of GraphDatabasePort.

    All queries use parameterized Cypher ($param syntax) to prevent
    injection. Only read operations are permitted.

    Args:
        uri: Neo4j Bolt URI (e.g., bolt://localhost:7687).
        auth: Authentication tuple (username, password).
    """

    def __init__(self, uri: str, auth: tuple[str, str]) -> None:
        """Initialize Neo4j adapter with connection details."""
        self._uri = uri
        self._auth = auth
        self._driver: AsyncDriver | None = None
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout_seconds=60,
            service_name="neo4j",
        )

    async def _get_driver(self) -> AsyncDriver:
        """Get or create the async Neo4j driver."""
        if self._driver is None:
            self._driver = AsyncGraphDatabase.driver(self._uri, auth=self._auth)
        return self._driver

    async def neighbor_query(
        self, entity_id: str, entity_type: str, hop_depth: int = 2
    ) -> list[dict[str, object]]:
        """Return all entities within hop_depth traversals of source.

        Uses parameterized Cypher to traverse the graph from the source
        entity up to the specified hop depth.

        Args:
            entity_id: Unique identifier of the source entity.
            entity_type: Label type of the source entity.
            hop_depth: Maximum traversal depth (default 2).

        Returns:
            List of entity dictionaries with properties.

        Raises:
            GraphConnectionError: If Neo4j is unreachable.
        """
        if not self._circuit_breaker.can_execute():
            msg = "Neo4j circuit breaker is open"
            raise GraphConnectionError(msg)

        query = (
            f"MATCH (source:{entity_type} {{entity_id: $entity_id}})"
            f"-[*1..{hop_depth}]-(neighbor) "
            "RETURN DISTINCT neighbor.entity_id AS entity_id, "
            "labels(neighbor)[0] AS label, "
            "properties(neighbor) AS properties"
        )
        try:
            driver = await self._get_driver()
            async with driver.session() as session:
                result = await session.run(query, entity_id=entity_id)
                records = [dict(record) async for record in result]
            self._circuit_breaker.record_success()
            return records
        except Exception as exc:
            self._circuit_breaker.record_failure()
            msg = f"Neo4j neighbor query failed: {exc}"
            raise GraphConnectionError(msg) from exc

    async def path_extraction(
        self, source_id: str, target_id: str
    ) -> list[dict[str, object]]:
        """Extract complete relationship path between two nodes.

        Args:
            source_id: Starting node entity_id.
            target_id: Ending node entity_id.

        Returns:
            Ordered list of nodes and edges forming the path.

        Raises:
            GraphConnectionError: If Neo4j is unreachable.
        """
        if not self._circuit_breaker.can_execute():
            msg = "Neo4j circuit breaker is open"
            raise GraphConnectionError(msg)

        query = (
            "MATCH path = shortestPath("
            "(source {entity_id: $source_id})-[*..2]-(target {entity_id: $target_id})"
            ") "
            "RETURN [n IN nodes(path) | {entity_id: n.entity_id, label: labels(n)[0], properties: properties(n)}] AS nodes, "
            "[r IN relationships(path) | {source: startNode(r).entity_id, target: endNode(r).entity_id, type: type(r)}] AS edges"
        )
        try:
            driver = await self._get_driver()
            async with driver.session() as session:
                result = await session.run(
                    query, source_id=source_id, target_id=target_id
                )
                records = [dict(record) async for record in result]
            self._circuit_breaker.record_success()
            return records
        except Exception as exc:
            self._circuit_breaker.record_failure()
            msg = f"Neo4j path extraction failed: {exc}"
            raise GraphConnectionError(msg) from exc

    async def node_lookup(self, entity_id: str) -> dict[str, object] | None:
        """Look up a single node by entity_id.

        Args:
            entity_id: Unique identifier of the node.

        Returns:
            Node properties dict, or None if not found.

        Raises:
            GraphConnectionError: If Neo4j is unreachable.
        """
        if not self._circuit_breaker.can_execute():
            msg = "Neo4j circuit breaker is open"
            raise GraphConnectionError(msg)

        query = (
            "MATCH (n {entity_id: $entity_id}) "
            "RETURN n.entity_id AS entity_id, labels(n)[0] AS label, "
            "properties(n) AS properties LIMIT 1"
        )
        try:
            driver = await self._get_driver()
            async with driver.session() as session:
                result = await session.run(query, entity_id=entity_id)
                record = await result.single()
            self._circuit_breaker.record_success()
            return dict(record) if record else None
        except Exception as exc:
            self._circuit_breaker.record_failure()
            msg = f"Neo4j node lookup failed: {exc}"
            raise GraphConnectionError(msg) from exc

    async def health_check(self) -> bool:
        """Verify connectivity to Neo4j.

        Returns:
            True if the database is reachable and responsive.
        """
        try:
            driver = await self._get_driver()
            async with driver.session() as session:
                result = await session.run("RETURN 1 AS ping")
                await result.single()
            return True
        except Exception:
            return False

    async def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            await self._driver.close()
            self._driver = None
