"""Infrastructure adapters — concrete implementations of domain port interfaces.

Each adapter implements a domain Port ABC, encapsulating all infrastructure
concerns (network calls, database drivers, file I/O) behind the port contract.

Adapters:
    - DuckDBAdapter: WarehousePort implementation using embedded DuckDB.
    - RegistryAdapter: CustomerRegistryPort implementation with simulated registry.
    - S3AuditLogAdapter: AuditLogPort implementation with SHA-256 hash chain.
    - WatchlistAPIAdapter: WatchlistPort implementation with simulated screening data.
"""

from infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from infrastructure.adapters.registry_adapter import RegistryAdapter
from infrastructure.adapters.s3_audit_log_adapter import S3AuditLogAdapter
from infrastructure.adapters.watchlist_api_adapter import WatchlistAPIAdapter

__all__ = [
    "DuckDBAdapter",
    "RegistryAdapter",
    "S3AuditLogAdapter",
    "WatchlistAPIAdapter",
]
