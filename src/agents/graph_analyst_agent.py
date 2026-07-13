"""Graph Analyst Strands agent for fraud network detection.

Queries the Neo4j graph database to extract 2-hop neighborhood connections
and identify links between customers and known fraudulent entities.
"""

from __future__ import annotations

from typing import Any

from strands import Agent, tool

from src.domain.ports.graph_database_port import GraphDatabasePort
from src.domain.ports.llm_client_port import LLMClientPort


# Module-level port reference set by factory
_graph_db_port: GraphDatabasePort | None = None


@tool
def query_address_neighborhood(address_hash: str, hop_depth: int = 2) -> dict[str, Any]:
    """Query two-hop neighborhood from an address node in the graph.

    Args:
        address_hash: Hash identifier of the address node.
        hop_depth: Maximum traversal depth (default 2, max 2).

    Returns:
        Dictionary with connected entities and their properties.
    """
    import asyncio

    if _graph_db_port is None:
        return {"error": "Graph database port not configured"}
    hop_depth = min(hop_depth, 2)  # Enforce max 2 hops
    results = asyncio.run(_graph_db_port.neighbor_query(address_hash, "Address", hop_depth))
    return {"source_type": "Address", "source_id": address_hash, "neighbors": results, "count": len(results)}


@tool
def query_ip_neighborhood(ip_address: str, hop_depth: int = 2) -> dict[str, Any]:
    """Query two-hop neighborhood from an IP address node in the graph.

    Args:
        ip_address: The IP address to query from.
        hop_depth: Maximum traversal depth (default 2, max 2).

    Returns:
        Dictionary with connected entities and their properties.
    """
    import asyncio

    if _graph_db_port is None:
        return {"error": "Graph database port not configured"}
    hop_depth = min(hop_depth, 2)
    results = asyncio.run(_graph_db_port.neighbor_query(ip_address, "IPAddress", hop_depth))
    return {"source_type": "IPAddress", "source_id": ip_address, "neighbors": results, "count": len(results)}


@tool
def query_phone_neighborhood(phone_number: str, hop_depth: int = 2) -> dict[str, Any]:
    """Query two-hop neighborhood from a phone number node in the graph.

    Args:
        phone_number: The phone number to query from.
        hop_depth: Maximum traversal depth (default 2, max 2).

    Returns:
        Dictionary with connected entities and their properties.
    """
    import asyncio

    if _graph_db_port is None:
        return {"error": "Graph database port not configured"}
    hop_depth = min(hop_depth, 2)
    results = asyncio.run(_graph_db_port.neighbor_query(phone_number, "PhoneNumber", hop_depth))
    return {"source_type": "PhoneNumber", "source_id": phone_number, "neighbors": results, "count": len(results)}


@tool
def extract_fraud_paths(source_id: str, flagged_entity_ids: list[str]) -> dict[str, Any]:
    """Extract relationship paths from source customer to flagged entities.

    Args:
        source_id: Customer entity ID to trace from.
        flagged_entity_ids: List of flagged entity IDs to trace to.

    Returns:
        Dictionary with discovered paths and their details.
    """
    import asyncio

    if _graph_db_port is None:
        return {"error": "Graph database port not configured"}

    paths = []
    for target_id in flagged_entity_ids:
        path = asyncio.run(_graph_db_port.path_extraction(source_id, target_id))
        if path:
            paths.append({"source": source_id, "target": target_id, "path": path, "length": len(path) - 1})

    return {"discovered_paths": paths, "total_paths": len(paths)}


@tool
def compute_network_risk_score(
    paths: list[dict[str, Any]],
    flagged_severities: list[str],
) -> dict[str, Any]:
    """Compute network risk score from discovered fraud paths.

    Risk is calculated based on:
    - Hop distance (closer = higher risk)
    - Number of shared infrastructure elements
    - Severity of connected flagged entities

    Args:
        paths: List of path dictionaries from extract_fraud_paths.
        flagged_severities: List of severity levels (HIGH, MEDIUM, LOW) for flagged entities.

    Returns:
        Dictionary with computed risk score and breakdown.
    """
    if not paths:
        return {"network_risk_score": 0.0, "risk_level": "NONE", "contributing_factors": []}

    # Severity weights
    severity_weights = {"HIGH": 1.0, "MEDIUM": 0.6, "LOW": 0.3}

    # Compute risk components
    hop_scores = []
    for path in paths:
        path_length = path.get("length", 2)
        hop_risk = 1.0 / max(path_length, 1)  # Closer = higher risk
        hop_scores.append(hop_risk)

    severity_scores = [severity_weights.get(s, 0.3) for s in flagged_severities]

    # Combine: average hop risk * max severity * path count factor
    avg_hop_risk = sum(hop_scores) / len(hop_scores) if hop_scores else 0.0
    max_severity = max(severity_scores) if severity_scores else 0.0
    path_count_factor = min(1.0, len(paths) * 0.3)  # More paths = higher risk

    network_risk = min(1.0, avg_hop_risk * 0.4 + max_severity * 0.4 + path_count_factor * 0.2)

    risk_level = "HIGH" if network_risk > 0.7 else "MEDIUM" if network_risk > 0.3 else "LOW"

    return {
        "network_risk_score": round(network_risk, 4),
        "risk_level": risk_level,
        "avg_hop_risk": round(avg_hop_risk, 4),
        "max_severity": max_severity,
        "path_count": len(paths),
        "contributing_factors": [
            f"Found {len(paths)} path(s) to flagged entities",
            f"Closest connection: {min(p.get('length', 2) for p in paths)} hops",
            f"Highest severity: {max(flagged_severities) if flagged_severities else 'NONE'}",
        ],
    }


SYSTEM_PROMPT = """You are a specialized Graph & Network Analyst agent (GraphRAG Engine).

Your sole responsibility is to analyze shared infrastructure elements (addresses, IPs, 
phone numbers) in the customer graph network to discover hidden connections between 
the new customer and known fraudulent or watchlisted entities.

Your tools allow you to:
1. Query address neighborhoods (2-hop traversal)
2. Query IP address neighborhoods (2-hop traversal)
3. Query phone number neighborhoods (2-hop traversal)
4. Extract specific fraud paths between entities
5. Compute network risk scores from discovered paths

Workflow:
- Query the neighborhood for each infrastructure element (address, IP, phone)
- Identify any connected entities that are flagged (WatchlistEntity nodes with risk_flag)
- For flagged entities found, extract the complete relationship paths
- Compute the network risk score based on hop distance, number of paths, and severity
- Return graph_clear if no flagged connections found, or fraud_connections_found with details

CRITICAL CONSTRAINTS:
- You may ONLY execute READ operations. No writes to the graph.
- Maximum hop depth is 2. Never request more than 2 hops.
- If a single hop returns >100 entities, focus on those with fraud/sanctions flags.
"""


def create_graph_analyst_agent(
    graph_db_port: GraphDatabasePort,
    llm_port: LLMClientPort,
) -> Agent:
    """Factory function creating the Graph_Analyst Strands agent.

    Args:
        graph_db_port: Port for graph database read operations.
        llm_port: Port for LLM interactions.

    Returns:
        Configured Strands Agent for graph network analysis.
    """
    global _graph_db_port  # noqa: PLW0603
    _graph_db_port = graph_db_port

    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[
            query_address_neighborhood,
            query_ip_neighborhood,
            query_phone_neighborhood,
            extract_fraud_paths,
            compute_network_risk_score,
        ],
        max_iterations=10,
    )
