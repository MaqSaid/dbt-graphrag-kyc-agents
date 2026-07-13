"""Domain ports — abstract interfaces for external system interactions.

All ports are Python ABCs (Abstract Base Classes) following the Interface
Segregation principle with ≤ 5 methods per interface. Infrastructure adapters
implement these contracts to enable testability and swappable integrations.
"""

from domain.ports.audit_log_port import AuditLogPort
from domain.ports.customer_registry_port import CustomerRegistryPort
from domain.ports.graph_database_port import GraphDatabasePort
from domain.ports.llm_client_port import LLMClientPort
from domain.ports.warehouse_port import WarehousePort
from domain.ports.watchlist_port import WatchlistPort

__all__ = [
    "AuditLogPort",
    "CustomerRegistryPort",
    "GraphDatabasePort",
    "LLMClientPort",
    "WarehousePort",
    "WatchlistPort",
]
