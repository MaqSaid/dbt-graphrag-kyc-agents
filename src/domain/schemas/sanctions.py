"""Sanctions screening domain schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class WatchlistEntry(BaseModel):
    """A single entity from a watchlist/sanctions database."""

    model_config = ConfigDict(strict=True)

    entity_name: str
    entity_type: Literal["individual", "organization"]
    source_list: str
    list_date: str
    sanctions_programs: list[str]
    match_identifiers: dict[str, str]


class WatchlistMatch(BaseModel):
    """A potential match between a customer and a watchlist entity."""

    model_config = ConfigDict(strict=True)

    matched_entity: WatchlistEntry
    similarity_score: float = Field(ge=0.0, le=1.0)
    matched_fields: list[str]


class WatchlistSearchResult(BaseModel):
    """Result of searching watchlist sources."""

    model_config = ConfigDict(strict=True)

    entries: list[WatchlistMatch] = Field(default_factory=list)
    sources_queried: list[str]
    query_timestamp: str


class SanctionsScreeningResult(BaseModel):
    """Complete result of sanctions/PEP screening process."""

    model_config = ConfigDict(strict=True)

    status: Literal["screening_clear", "screening_hit", "screening_ambiguous"]
    matches: list[WatchlistMatch] = Field(default_factory=list)
    match_score: float = Field(ge=0.0, le=1.0, default=0.0)
    has_confirmed_match: bool = False
    sources_screened: list[str]
    processing_time_ms: int = Field(ge=0)
