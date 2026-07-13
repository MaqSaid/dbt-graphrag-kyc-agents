"""Port interface for DuckDB warehouse operations."""

from __future__ import annotations

from abc import ABC, abstractmethod


class WarehousePort(ABC):
    """Abstract interface for analytical warehouse operations.

    Provides data loading, querying, and export capabilities
    for the ELT pipeline using DuckDB.
    """

    @abstractmethod
    async def load_raw_data(self, file_path: str, table_name: str) -> int:
        """Load CSV data into a raw table.

        Args:
            file_path: Path to the CSV file.
            table_name: Target table name in the warehouse.

        Returns:
            Number of rows loaded.
        """
        ...

    @abstractmethod
    async def execute_query(self, query: str) -> list[dict[str, object]]:
        """Execute a read query and return results.

        Args:
            query: SQL query string.

        Returns:
            List of row dictionaries.
        """
        ...

    @abstractmethod
    async def export_to_csv(self, query: str, output_path: str) -> str:
        """Export query results to CSV for graph import.

        Args:
            query: SQL query to export.
            output_path: Destination file path.

        Returns:
            Path to the exported file.
        """
        ...
