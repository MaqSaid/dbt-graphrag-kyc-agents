"""Port interface for immutable audit log operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from src.domain.schemas.audit import AuditLogEntry


class AuditLogPort(ABC):
    """Abstract interface for audit log operations.

    Provides append-only logging with hash chain integrity
    for ISO 27001 compliance traceability.
    """

    @abstractmethod
    async def log_event(self, entry: AuditLogEntry) -> str:
        """Append an audit log entry.

        Args:
            entry: The audit log entry to persist.

        Returns:
            The entry_id of the persisted entry.
        """
        ...

    @abstractmethod
    async def query_by_evaluation_id(
        self, evaluation_id: str
    ) -> list[AuditLogEntry]:
        """Retrieve all audit entries for an evaluation.

        Args:
            evaluation_id: The evaluation to query.

        Returns:
            Ordered list of audit entries.
        """
        ...

    @abstractmethod
    async def query_by_time_range(
        self, start: datetime, end: datetime
    ) -> list[AuditLogEntry]:
        """Retrieve audit entries within a time range.

        Args:
            start: Range start (inclusive).
            end: Range end (inclusive).

        Returns:
            List of audit entries within the range.
        """
        ...
