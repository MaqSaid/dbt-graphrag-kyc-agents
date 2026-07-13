"""DuckDB warehouse adapter — analytical data warehouse operations.

Implements the WarehousePort interface using the duckdb Python package
for CSV loading, SQL querying, and data export operations.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

from domain.ports.warehouse_port import WarehousePort


class DuckDBAdapter(WarehousePort):
    """Adapter for DuckDB warehouse operations.

    Provides ELT data loading from CSV files, SQL query execution,
    and CSV export capabilities using the embedded DuckDB engine.

    Args:
        db_path: Path to the DuckDB database file. Use ":memory:" for
            an in-memory database (useful for testing).
    """

    def __init__(self, db_path: str) -> None:
        """Initialize DuckDBAdapter.

        Args:
            db_path: Path to the DuckDB database file. Use ":memory:"
                for an in-memory database.
        """
        self._db_path = db_path
        self._connection: duckdb.DuckDBPyConnection = duckdb.connect(db_path)

    @property
    def db_path(self) -> str:
        """Return the configured database path."""
        return self._db_path

    @property
    def connection(self) -> duckdb.DuckDBPyConnection:
        """Return the underlying DuckDB connection (for testing/inspection)."""
        return self._connection

    async def load_raw_data(self, file_path: str, table_name: str) -> int:
        """Load CSV into raw table.

        Creates or replaces the target table with data from the CSV file.
        DuckDB auto-detects column types from the CSV content.

        Args:
            file_path: Path to the CSV file to ingest.
            table_name: Target table name in the warehouse.

        Returns:
            Number of rows loaded.

        Raises:
            FileNotFoundError: If the CSV file does not exist.
            duckdb.Error: If there is a DuckDB-level error during loading.
        """
        csv_path = Path(file_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        # Use DuckDB's native CSV reader with auto-detection
        self._connection.execute(
            f"CREATE OR REPLACE TABLE {table_name} AS "  # noqa: S608
            f"SELECT * FROM read_csv_auto('{csv_path.as_posix()}')"
        )

        # Get row count
        result = self._connection.execute(
            f"SELECT COUNT(*) FROM {table_name}"  # noqa: S608
        ).fetchone()

        return result[0] if result else 0

    async def execute_query(self, query: str) -> list[dict]:
        """Execute read query and return results.

        Executes the given SQL query against the DuckDB instance and
        returns results as a list of dictionaries.

        Args:
            query: SQL query string to execute.

        Returns:
            List of dictionaries representing query result rows.

        Raises:
            duckdb.Error: If there is a DuckDB-level error during execution.
        """
        result = self._connection.execute(query)
        columns = [desc[0] for desc in result.description]
        rows = result.fetchall()

        return [dict(zip(columns, row)) for row in rows]

    async def export_to_csv(self, query: str, output_path: str) -> str:
        """Export query results to CSV for graph import.

        Executes the query and writes the results to a CSV file at the
        specified output path.

        Args:
            query: SQL query whose results will be exported.
            output_path: File path where the CSV will be written.

        Returns:
            The output file path of the exported CSV.

        Raises:
            duckdb.Error: If there is a DuckDB-level error during export.
        """
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)

        self._connection.execute(
            f"COPY ({query}) TO '{output.as_posix()}' (HEADER, DELIMITER ',')"
        )

        return str(output)

    def close(self) -> None:
        """Close the DuckDB connection.

        Should be called when the adapter is no longer needed to release
        database resources.
        """
        self._connection.close()
