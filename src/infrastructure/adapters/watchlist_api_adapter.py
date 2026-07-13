"""Watchlist API adapter — simulated sanctions/PEP screening.

Implements the WatchlistPort interface with local mock data for development
and testing. In production, this would connect to real OFAC, EU, UN, and
PEP screening APIs. Integrates a circuit breaker for resilience.
"""

from __future__ import annotations

from datetime import datetime, timezone
from difflib import SequenceMatcher

from domain.ports.watchlist_port import WatchlistPort
from domain.schemas.sanctions import (
    WatchlistEntry,
    WatchlistMatch,
    WatchlistSearchResult,
)
from infrastructure.resilience.circuit_breaker import CircuitBreaker


# Simulated watchlist data for development/testing
_SIMULATED_WATCHLIST: list[dict] = [
    {
        "entity_name": "Viktor Bout",
        "entity_type": "individual",
        "source_list": "ofac_sdn",
        "list_date": "2004-03-01",
        "sanctions_programs": ["SDGT", "Arms Trafficking"],
        "match_identifiers": {"national_id": "RU-1234567890", "dob": "1967-01-13"},
    },
    {
        "entity_name": "Al-Rashid Trading Company",
        "entity_type": "organization",
        "source_list": "ofac_sdn",
        "list_date": "2019-06-15",
        "sanctions_programs": ["IRAN-EO13846"],
        "match_identifiers": {"registration_number": "IR-98765"},
    },
    {
        "entity_name": "Elena Petrov",
        "entity_type": "individual",
        "source_list": "eu_sanctions",
        "list_date": "2022-03-01",
        "sanctions_programs": ["EU Council Regulation 269/2014"],
        "match_identifiers": {"national_id": "EU-5551234", "dob": "1975-08-22"},
    },
    {
        "entity_name": "Ahmed Hassan",
        "entity_type": "individual",
        "source_list": "un_sanctions",
        "list_date": "2015-09-10",
        "sanctions_programs": ["UN-1267", "Al-Qaida Sanctions"],
        "match_identifiers": {"national_id": "SY-9876543", "dob": "1980-04-15"},
    },
    {
        "entity_name": "Jean-Pierre Moreau",
        "entity_type": "individual",
        "source_list": "pep",
        "list_date": "2020-01-20",
        "sanctions_programs": ["PEP-Level1"],
        "match_identifiers": {"national_id": "FR-1122334", "dob": "1960-11-30"},
    },
    {
        "entity_name": "Viktor Boutenko",
        "entity_type": "individual",
        "source_list": "eu_sanctions",
        "list_date": "2023-01-15",
        "sanctions_programs": ["EU Council Regulation 833/2014"],
        "match_identifiers": {"national_id": "UA-7654321", "dob": "1970-05-20"},
    },
]


class WatchlistAPIAdapter(WatchlistPort):
    """Adapter for watchlist/sanctions screening using simulated local data.

    In production, this adapter would call external screening APIs (OFAC SDN,
    EU Consolidated Sanctions, UN Security Council, PEP databases). For local
    development, it uses an in-memory dataset with fuzzy matching.

    Args:
        sources: List of watchlist sources to query (e.g., ["ofac_sdn", "eu_sanctions"]).
        failure_threshold: Circuit breaker failure threshold before opening.
        recovery_timeout_seconds: Seconds before circuit breaker attempts recovery.
    """

    def __init__(
        self,
        sources: list[str],
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
    ) -> None:
        """Initialize WatchlistAPIAdapter.

        Args:
            sources: List of watchlist sources to query.
            failure_threshold: Number of failures before circuit opens.
            recovery_timeout_seconds: Recovery timeout for circuit breaker.
        """
        self._sources = sources
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout_seconds=recovery_timeout_seconds,
            service_name="watchlist_api",
        )
        self._watchlist_data = [
            entry
            for entry in _SIMULATED_WATCHLIST
            if entry["source_list"] in self._sources
        ]

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        """Expose the circuit breaker for observability."""
        return self._circuit_breaker

    async def search_by_name(
        self,
        name: str,
        threshold: float = 0.85,
    ) -> WatchlistSearchResult:
        """Fuzzy search watchlist by entity name.

        Uses SequenceMatcher for similarity scoring. Returns all entries
        exceeding the similarity threshold.

        Args:
            name: Full name of the entity to search for.
            threshold: Minimum similarity score for matches (0.0 to 1.0).

        Returns:
            Aggregated search result containing matched entries and metadata.

        Raises:
            RuntimeError: If the circuit breaker is open.
        """
        self._check_circuit_breaker()

        try:
            matches: list[WatchlistMatch] = []
            normalized_name = name.strip().lower()

            for entry_data in self._watchlist_data:
                entity_name = entry_data["entity_name"].lower()
                similarity = SequenceMatcher(
                    None, normalized_name, entity_name
                ).ratio()

                if similarity >= threshold:
                    entry = WatchlistEntry(
                        entity_name=entry_data["entity_name"],
                        entity_type=entry_data["entity_type"],
                        source_list=entry_data["source_list"],
                        list_date=entry_data["list_date"],
                        sanctions_programs=entry_data["sanctions_programs"],
                        match_identifiers=entry_data["match_identifiers"],
                    )
                    matches.append(
                        WatchlistMatch(
                            matched_entity=entry,
                            similarity_score=round(similarity, 4),
                            matched_fields=["entity_name"],
                        )
                    )

            self._circuit_breaker.record_success()
            return WatchlistSearchResult(
                entries=matches,
                sources_queried=self._sources,
                query_timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )
        except Exception as exc:
            self._circuit_breaker.record_failure()
            raise RuntimeError(f"Watchlist search failed: {exc}") from exc

    async def search_by_national_id(
        self,
        national_id: str,
    ) -> WatchlistSearchResult:
        """Exact match search by national ID.

        Searches all configured watchlist sources for entries with a matching
        national_id in their match_identifiers.

        Args:
            national_id: National identification number to search for.

        Returns:
            Aggregated search result containing matched entries and metadata.

        Raises:
            RuntimeError: If the circuit breaker is open.
        """
        self._check_circuit_breaker()

        try:
            matches: list[WatchlistMatch] = []

            for entry_data in self._watchlist_data:
                identifiers = entry_data["match_identifiers"]
                if identifiers.get("national_id") == national_id:
                    entry = WatchlistEntry(
                        entity_name=entry_data["entity_name"],
                        entity_type=entry_data["entity_type"],
                        source_list=entry_data["source_list"],
                        list_date=entry_data["list_date"],
                        sanctions_programs=entry_data["sanctions_programs"],
                        match_identifiers=entry_data["match_identifiers"],
                    )
                    matches.append(
                        WatchlistMatch(
                            matched_entity=entry,
                            similarity_score=1.0,
                            matched_fields=["national_id"],
                        )
                    )

            self._circuit_breaker.record_success()
            return WatchlistSearchResult(
                entries=matches,
                sources_queried=self._sources,
                query_timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )
        except Exception as exc:
            self._circuit_breaker.record_failure()
            raise RuntimeError(f"Watchlist ID search failed: {exc}") from exc

    async def search_by_date_of_birth(
        self,
        date_of_birth: str,
        name: str,
    ) -> WatchlistSearchResult:
        """Combined search by date of birth and name.

        Filters entries by exact DOB match, then applies fuzzy name matching
        to produce combined similarity scores.

        Args:
            date_of_birth: Date of birth in ISO 8601 format (YYYY-MM-DD).
            name: Full name for combined matching.

        Returns:
            Aggregated search result containing matched entries and metadata.

        Raises:
            RuntimeError: If the circuit breaker is open.
        """
        self._check_circuit_breaker()

        try:
            matches: list[WatchlistMatch] = []
            normalized_name = name.strip().lower()

            for entry_data in self._watchlist_data:
                identifiers = entry_data["match_identifiers"]
                if identifiers.get("dob") != date_of_birth:
                    continue

                # DOB matched — compute name similarity
                entity_name = entry_data["entity_name"].lower()
                name_similarity = SequenceMatcher(
                    None, normalized_name, entity_name
                ).ratio()

                # Combined score: 50% DOB exact match + 50% name similarity
                combined_score = 0.5 + (name_similarity * 0.5)

                entry = WatchlistEntry(
                    entity_name=entry_data["entity_name"],
                    entity_type=entry_data["entity_type"],
                    source_list=entry_data["source_list"],
                    list_date=entry_data["list_date"],
                    sanctions_programs=entry_data["sanctions_programs"],
                    match_identifiers=entry_data["match_identifiers"],
                )
                matches.append(
                    WatchlistMatch(
                        matched_entity=entry,
                        similarity_score=round(min(combined_score, 1.0), 4),
                        matched_fields=["date_of_birth", "entity_name"],
                    )
                )

            self._circuit_breaker.record_success()
            return WatchlistSearchResult(
                entries=matches,
                sources_queried=self._sources,
                query_timestamp=datetime.now(tz=timezone.utc).isoformat(),
            )
        except Exception as exc:
            self._circuit_breaker.record_failure()
            raise RuntimeError(f"Watchlist DOB search failed: {exc}") from exc

    def _check_circuit_breaker(self) -> None:
        """Check circuit breaker state before executing a call.

        Raises:
            RuntimeError: If the circuit breaker is in OPEN state.
        """
        if not self._circuit_breaker.can_execute():
            raise RuntimeError(
                f"Circuit breaker OPEN for service '{self._circuit_breaker.service_name}'. "
                "Calls are being rejected to prevent cascading failures."
            )
