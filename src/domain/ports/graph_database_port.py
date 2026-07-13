"""Port interface for graph database operations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class GraphDatabasePort(ABC):
    """Abstract interface for graph database operations (Neo4j/Neptune).

    Provides read-only access to the graph database for querying
    multi-hop neighborhoods and extracting relationship paths.
    """

    @abstractmethod
    async def neighbor_query(
        self, entity_id: str, entity_type: str, hop_depth: int = 2
    ) -> list[dict[str, object]]:
        """Return all entities within hop_depth traversals of source.

        Args:
            entity_id: Unique identifier of the source entity.
            entity_type: Label type of the source entity.
            hop_depth: Maximum traversal depth (default 2).

        Returns:
            List of entity dictionaries with properties.
        """
        ...

    @abstractmethod
    async def path_extraction(
        self, source_id: str, target_id: str
    ) -> list[dict[str, object]]:
        """Extract complete relationship path between two nodes.

        Args:
            source_id: Starting node entity_id.
            target_id: Ending node entity_id.

        Returns:
            Ordered list of nodes and edges forming the path.
        """
        ...

    @abstractmethod
    async def node_lookup(self, entity_id: str) -> dict[str, object] | None:
        """Look up a single node by entity_id.

        Args:
            entity_id: Unique identifier of the node.

        Returns:
            Node properties dict, or None if not found.
        """
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify connectivity to graph database.

        Returns:
            True if the database is reachable and responsive.
        """
        ...
