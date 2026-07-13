"""Port interface for watchlist/sanctions data source queries."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.schemas.sanctions import WatchlistSearchResult


class WatchlistPort(ABC):
    """Abstract interface for watchlist and sanctions database queries.

    Provides fuzzy and exact matching against international
    watchlists, sanctions registers, and PEP databases.
    """

    @abstractmethod
    async def search_by_name(
        self, name: str, threshold: float = 0.85
    ) -> WatchlistSearchResult:
        """Fuzzy search watchlist by entity name.

        Args:
            name: Entity name to search for.
            threshold: Minimum similarity score for matches.

        Returns:
            Search result with matched entries and metadata.
        """
        ...

    @abstractmethod
    async def search_by_national_id(
        self, national_id: str
    ) -> WatchlistSearchResult:
        """Exact match search by national ID.

        Args:
            national_id: National identifier to search.

        Returns:
            Search result with matched entries.
        """
        ...

    @abstractmethod
    async def search_by_date_of_birth(
        self, date_of_birth: str, name: str
    ) -> WatchlistSearchResult:
        """Combined search by date of birth and name.

        Args:
            date_of_birth: DOB in ISO format.
            name: Entity name for combined matching.

        Returns:
            Search result with matched entries.
        """
        ...
