"""Graph network analysis domain service.

Implements fraud ring detection through multi-hop graph traversal and
risk scoring for the Graph Analysis bounded context.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from domain.schemas.graph_analysis import (
    FraudPath,
    GraphAnalysisResult,
    GraphEdge,
    GraphNode,
)

if TYPE_CHECKING:
    from domain.ports.graph_database_port import GraphDatabasePort


class GraphAnalysisService:
    """Domain service for graph-based fraud network analysis.

    Queries the graph database for neighborhood connections around customer
    infrastructure elements (address, IP, phone), identifies flagged entities,
    extracts relationship paths, and computes a network risk score.

    Args:
        graph_db_port: Injected port for graph database operations.
    """

    #: Risk weights for flagged entity severity levels
    _SEVERITY_WEIGHTS: dict[str, float] = {
        "HIGH": 1.0,
        "MEDIUM": 0.6,
        "LOW": 0.3,
    }

    #: Maximum hops to traverse in neighborhood queries
    _MAX_HOP_DEPTH: int = 2

    def __init__(self, graph_db_port: GraphDatabasePort) -> None:
        """Initialize with injected GraphDatabasePort.

        Args:
            graph_db_port: Port implementation for graph database queries.
        """
        self._graph_db_port = graph_db_port

    async def analyze_network(
        self,
        address: str,
        ip_address: str,
        phone: str,
    ) -> GraphAnalysisResult:
        """Analyze customer network for fraud connections.

        Queries the two-hop neighborhood for each infrastructure element
        (address, IP, phone), filters for flagged entities, extracts
        relationship paths to those entities, and computes a network risk
        score based on hop distance and severity.

        Args:
            address: Customer address identifier (hash or canonical form).
            ip_address: Customer IP address.
            phone: Customer phone number.

        Returns:
            Structured graph analysis result with discovered paths,
            flagged entities, risk score, and traversal metadata.
        """
        start_time = time.perf_counter()

        # Query neighborhoods for each infrastructure element
        address_neighbors = await self._graph_db_port.neighbor_query(
            entity_id=address,
            entity_type="Address",
            hop_depth=self._MAX_HOP_DEPTH,
        )
        ip_neighbors = await self._graph_db_port.neighbor_query(
            entity_id=ip_address,
            entity_type="IPAddress",
            hop_depth=self._MAX_HOP_DEPTH,
        )
        phone_neighbors = await self._graph_db_port.neighbor_query(
            entity_id=phone,
            entity_type="PhoneNumber",
            hop_depth=self._MAX_HOP_DEPTH,
        )

        # Combine all neighbors
        all_neighbors = address_neighbors + ip_neighbors + phone_neighbors

        # Filter for flagged entities
        flagged_entities = self._filter_flagged_entities(all_neighbors)

        # Extract paths to flagged entities
        source_ids = [address, ip_address, phone]
        discovered_paths = await self._extract_fraud_paths(
            source_ids, flagged_entities,
        )

        # Compute network risk score
        network_risk_score = self._compute_network_risk_score(discovered_paths)

        # Determine if there is a confirmed fraud ring (multiple HIGH-severity paths)
        has_confirmed_fraud_ring = self._detect_fraud_ring(discovered_paths)

        # Determine status
        status = (
            "fraud_connections_found" if flagged_entities else "graph_clear"
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        # Build traversal metadata
        traversal_metadata = {
            "address_neighbors_count": len(address_neighbors),
            "ip_neighbors_count": len(ip_neighbors),
            "phone_neighbors_count": len(phone_neighbors),
            "total_neighbors_evaluated": len(all_neighbors),
            "flagged_entities_found": len(flagged_entities),
        }

        return GraphAnalysisResult(
            status=status,
            discovered_paths=discovered_paths,
            network_risk_score=network_risk_score,
            connected_flagged_entities=flagged_entities,
            has_confirmed_fraud_ring=has_confirmed_fraud_ring,
            traversal_metadata=traversal_metadata,
            processing_time_ms=elapsed_ms,
        )

    @staticmethod
    def _filter_flagged_entities(neighbors: list[dict]) -> list[GraphNode]:
        """Filter neighbor results for entities with risk flags.

        A neighbor is considered flagged if it has a 'risk_flag' property
        or its label is 'WatchlistEntity'.

        Args:
            neighbors: Raw neighbor query results from graph database.

        Returns:
            List of GraphNode instances representing flagged entities.
        """
        flagged: list[GraphNode] = []
        seen_ids: set[str] = set()

        for neighbor in neighbors:
            entity_id = neighbor.get("entity_id", "")
            if entity_id in seen_ids:
                continue

            label = neighbor.get("label", "")
            properties = neighbor.get("properties", {})

            is_flagged = (
                label == "WatchlistEntity"
                or "risk_flag" in properties
            )

            if is_flagged and label in (
                "Customer",
                "Address",
                "IPAddress",
                "PhoneNumber",
                "WatchlistEntity",
            ):
                seen_ids.add(entity_id)
                flagged.append(
                    GraphNode(
                        entity_id=entity_id,
                        label=label,
                        properties=properties,
                    ),
                )

        return flagged

    async def _extract_fraud_paths(
        self,
        source_ids: list[str],
        flagged_entities: list[GraphNode],
    ) -> list[FraudPath]:
        """Extract relationship paths from source nodes to flagged entities.

        Args:
            source_ids: Customer infrastructure element identifiers.
            flagged_entities: Previously identified flagged neighbor nodes.

        Returns:
            List of FraudPath instances connecting sources to flagged entities.
        """
        paths: list[FraudPath] = []

        for source_id in source_ids:
            for flagged_node in flagged_entities:
                path_segments = await self._graph_db_port.path_extraction(
                    source_id=source_id,
                    target_id=flagged_node.entity_id,
                )

                if not path_segments:
                    continue

                # Build path nodes and edges from segments
                nodes, edges = self._build_path_components(path_segments)

                # Only include paths within max hop depth
                path_length = len(edges)
                if path_length < 1 or path_length > self._MAX_HOP_DEPTH:
                    continue

                # Determine terminal entity risk flag
                risk_flag = self._get_entity_risk_flag(flagged_node)

                paths.append(
                    FraudPath(
                        nodes=nodes,
                        edges=edges,
                        path_length=path_length,
                        terminal_entity_risk_flag=risk_flag,
                    ),
                )

        return paths

    @staticmethod
    def _build_path_components(
        path_segments: list[dict],
    ) -> tuple[list[GraphNode], list[GraphEdge]]:
        """Build GraphNode and GraphEdge lists from raw path segments.

        Args:
            path_segments: Raw path data from graph database.

        Returns:
            Tuple of (nodes list, edges list).
        """
        nodes: list[GraphNode] = []
        edges: list[GraphEdge] = []
        seen_node_ids: set[str] = set()

        for segment in path_segments:
            # Extract source node
            source = segment.get("source", {})
            source_id = source.get("entity_id", "")
            if source_id and source_id not in seen_node_ids:
                seen_node_ids.add(source_id)
                nodes.append(
                    GraphNode(
                        entity_id=source_id,
                        label=source.get("label", "Customer"),
                        properties=source.get("properties", {}),
                    ),
                )

            # Extract target node
            target = segment.get("target", {})
            target_id = target.get("entity_id", "")
            if target_id and target_id not in seen_node_ids:
                seen_node_ids.add(target_id)
                nodes.append(
                    GraphNode(
                        entity_id=target_id,
                        label=target.get("label", "Customer"),
                        properties=target.get("properties", {}),
                    ),
                )

            # Extract edge
            if source_id and target_id:
                edges.append(
                    GraphEdge(
                        source_id=source_id,
                        target_id=target_id,
                        relationship_type=segment.get("relationship_type", "CONNECTED_TO"),
                        properties=segment.get("edge_properties", {}),
                    ),
                )

        return nodes, edges

    @staticmethod
    def _get_entity_risk_flag(node: GraphNode) -> str:
        """Extract risk flag from a flagged entity node.

        Args:
            node: Graph node representing a flagged entity.

        Returns:
            Risk flag level ("HIGH", "MEDIUM", or "LOW").
        """
        risk_flag = node.properties.get("risk_flag", "LOW")
        if isinstance(risk_flag, str) and risk_flag in ("HIGH", "MEDIUM", "LOW"):
            return risk_flag
        return "LOW"

    def _compute_network_risk_score(
        self,
        paths: list[FraudPath],
    ) -> float:
        """Compute network risk score from discovered fraud paths.

        Score is computed as the weighted average of path contributions,
        where each path's weight is determined by:
        - Terminal entity severity (HIGH=1.0, MEDIUM=0.6, LOW=0.3)
        - Inverse hop distance (1-hop paths contribute more than 2-hop)

        The final score is clamped to [0.0, 1.0].

        Args:
            paths: Discovered fraud paths with severity flags.

        Returns:
            Network risk score between 0.0 and 1.0.
        """
        if not paths:
            return 0.0

        total_weight = 0.0
        for path in paths:
            severity_weight = self._SEVERITY_WEIGHTS.get(
                path.terminal_entity_risk_flag, 0.3,
            )
            # Closer paths (fewer hops) contribute more risk
            distance_factor = 1.0 / path.path_length
            total_weight += severity_weight * distance_factor

        # Normalize: cap at a reasonable max (e.g., 5 high-severity 1-hop paths = 1.0)
        max_expected_weight = 5.0
        score = min(total_weight / max_expected_weight, 1.0)

        return round(score, 4)

    @staticmethod
    def _detect_fraud_ring(paths: list[FraudPath]) -> bool:
        """Determine if discovered paths indicate a confirmed fraud ring.

        A fraud ring is confirmed when there are at least 2 distinct paths
        with HIGH-severity terminal entities.

        Args:
            paths: Discovered fraud paths.

        Returns:
            True if a fraud ring pattern is detected.
        """
        high_severity_paths = [
            p for p in paths if p.terminal_entity_risk_flag == "HIGH"
        ]
        return len(high_severity_paths) >= 2
