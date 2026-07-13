"""Graph network analysis domain schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GraphNode(BaseModel):
    """A node in the Neo4j graph database."""

    model_config = ConfigDict(strict=True)

    entity_id: str
    label: Literal["Customer", "Address", "IPAddress", "PhoneNumber", "WatchlistEntity"]
    properties: dict[str, str | int | float]


class GraphEdge(BaseModel):
    """An edge (relationship) in the Neo4j graph database."""

    model_config = ConfigDict(strict=True)

    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, str | int | float] = Field(default_factory=dict)


class FraudPath(BaseModel):
    """A discovered path connecting a customer to a flagged entity."""

    model_config = ConfigDict(strict=True)

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    path_length: int = Field(ge=1, le=2)
    terminal_entity_risk_flag: Literal["HIGH", "MEDIUM", "LOW"]


class GraphAnalysisResult(BaseModel):
    """Complete result of graph network analysis."""

    model_config = ConfigDict(strict=True)

    status: Literal["graph_clear", "fraud_connections_found"]
    discovered_paths: list[FraudPath] = Field(default_factory=list)
    network_risk_score: float = Field(ge=0.0, le=1.0, default=0.0)
    connected_flagged_entities: list[GraphNode] = Field(default_factory=list)
    has_confirmed_fraud_ring: bool = False
    traversal_metadata: dict[str, int] = Field(default_factory=dict)
    processing_time_ms: int = Field(ge=0)
