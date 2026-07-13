"""Sanctions screening domain service.

Implements watchlist screening across multiple sources and classifies results
based on configurable thresholds for the Sanctions bounded context.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from domain.schemas.sanctions import (
    SanctionsScreeningResult,
    WatchlistMatch,
    WatchlistSearchResult,
)

if TYPE_CHECKING:
    from domain.ports.watchlist_port import WatchlistPort
    from domain.schemas.config import DecisionConfig


class SanctionsScreeningService:
    """Domain service for sanctions and PEP screening.

    Screens entities against watchlist sources via the WatchlistPort,
    aggregates match results, and classifies the outcome as clear, hit,
    or ambiguous based on configurable thresholds.

    Args:
        watchlist_port: Injected port for watchlist/sanctions queries.
    """

    def __init__(self, watchlist_port: WatchlistPort) -> None:
        """Initialize with injected WatchlistPort.

        Args:
            watchlist_port: Port implementation for watchlist data source queries.
        """
        self._watchlist_port = watchlist_port

    async def screen_entity(
        self,
        name: str,
        national_id: str,
        date_of_birth: str,
        config: DecisionConfig,
    ) -> SanctionsScreeningResult:
        """Screen an entity against all available watchlist sources.

        Calls all three watchlist methods (name search, national ID search,
        DOB + name search), aggregates unique matches, computes the highest
        match score, and classifies the result based on threshold configuration.

        Args:
            name: Full name of the entity to screen.
            national_id: National identification number.
            date_of_birth: Date of birth in ISO 8601 format (YYYY-MM-DD).
            config: Decision configuration with fuzzy match threshold and
                ambiguity bounds.

        Returns:
            Structured screening result with status, matches, score, and metadata.
        """
        start_time = time.perf_counter()

        # Execute all three watchlist searches
        name_result = await self._watchlist_port.search_by_name(
            name=name,
            threshold=config.fuzzy_match_threshold,
        )
        national_id_result = await self._watchlist_port.search_by_national_id(
            national_id=national_id,
        )
        dob_result = await self._watchlist_port.search_by_date_of_birth(
            date_of_birth=date_of_birth,
            name=name,
        )

        # Aggregate all matches and deduplicate by entity name + source list
        all_matches = self._aggregate_matches(
            name_result, national_id_result, dob_result,
        )

        # Collect all sources queried
        sources_screened = self._collect_sources(
            name_result, national_id_result, dob_result,
        )

        # Compute highest match score
        match_score = self._compute_match_score(all_matches)

        # Determine if there is a confirmed match (exact national ID hit)
        has_confirmed_match = self._has_confirmed_match(national_id_result)

        # Classify screening status based on thresholds
        status = self._classify_status(match_score, has_confirmed_match, config)

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return SanctionsScreeningResult(
            status=status,
            matches=all_matches,
            match_score=match_score,
            has_confirmed_match=has_confirmed_match,
            sources_screened=sources_screened,
            processing_time_ms=elapsed_ms,
        )

    @staticmethod
    def _aggregate_matches(
        *results: WatchlistSearchResult,
    ) -> list[WatchlistMatch]:
        """Aggregate and deduplicate matches from multiple search results.

        Deduplicates by (entity_name, source_list) keeping the highest
        similarity_score entry.

        Args:
            *results: Variable number of WatchlistSearchResult instances.

        Returns:
            Deduplicated list of WatchlistMatch instances.
        """
        seen: dict[tuple[str, str], WatchlistMatch] = {}

        for result in results:
            for match in result.entries:
                key = (
                    match.matched_entity.entity_name,
                    match.matched_entity.source_list,
                )
                if key not in seen or match.similarity_score > seen[key].similarity_score:
                    seen[key] = match

        return list(seen.values())

    @staticmethod
    def _collect_sources(
        *results: WatchlistSearchResult,
    ) -> list[str]:
        """Collect unique sources queried across all results.

        Args:
            *results: Variable number of WatchlistSearchResult instances.

        Returns:
            Deduplicated list of source identifiers.
        """
        sources: set[str] = set()
        for result in results:
            sources.update(result.sources_queried)
        return sorted(sources)

    @staticmethod
    def _compute_match_score(matches: list[WatchlistMatch]) -> float:
        """Compute the highest similarity score across all matches.

        Args:
            matches: List of aggregated watchlist matches.

        Returns:
            Highest similarity score, or 0.0 if no matches found.
        """
        if not matches:
            return 0.0
        return max(m.similarity_score for m in matches)

    @staticmethod
    def _has_confirmed_match(national_id_result: WatchlistSearchResult) -> bool:
        """Determine if a confirmed match exists based on national ID search.

        A confirmed match occurs when the national ID search returns any
        entries with a similarity score of 1.0 (exact match).

        Args:
            national_id_result: Result from national ID search.

        Returns:
            True if an exact national ID match was found.
        """
        return any(
            m.similarity_score >= 1.0 for m in national_id_result.entries
        )

    @staticmethod
    def _classify_status(
        match_score: float,
        has_confirmed_match: bool,
        config: DecisionConfig,
    ) -> str:
        """Classify screening outcome based on score and thresholds.

        Classification rules:
        - Confirmed match OR score >= denial_threshold → screening_hit
        - Score < fuzzy_match_threshold → screening_clear
        - Otherwise → screening_ambiguous

        Args:
            match_score: Highest match score across all sources.
            has_confirmed_match: Whether an exact national ID match was found.
            config: Decision configuration with thresholds.

        Returns:
            One of "screening_clear", "screening_hit", or "screening_ambiguous".
        """
        if has_confirmed_match or match_score >= config.denial_threshold:
            return "screening_hit"
        if match_score < config.fuzzy_match_threshold:
            return "screening_clear"
        return "screening_ambiguous"
