"""S3 audit log adapter — append-only audit log with SHA-256 hash chain.

Implements the AuditLogPort interface with cryptographic hash chain integrity
for ISO 27001 compliance. Uses an in-memory buffer for local development;
production would persist to S3 with append-only key patterns.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime

from domain.ports.audit_log_port import AuditLogPort
from domain.schemas.audit import AuditLogEntry


class S3AuditLogAdapter(AuditLogPort):
    """Append-only audit log with cryptographic hash chain.

    Each entry's previous_hash links to its predecessor's entry_hash,
    forming a tamper-evident chain. entry_hash is computed as SHA-256 of
    the entry JSON excluding the entry_hash field itself.

    For local development, entries are stored in an in-memory buffer.
    In production, entries would be persisted to S3 with append-only
    key patterns (audit/{evaluation_id}/{timestamp}_{hash_prefix}.json).

    Args:
        bucket: S3 bucket name for audit log storage.
    """

    def __init__(self, bucket: str) -> None:
        """Initialize S3AuditLogAdapter.

        Args:
            bucket: S3 bucket name for audit log storage.
        """
        self._bucket = bucket
        self._previous_hash: str = "GENESIS"
        self._entries: list[AuditLogEntry] = []

    @property
    def bucket(self) -> str:
        """Return the configured S3 bucket name."""
        return self._bucket

    @property
    def entries(self) -> list[AuditLogEntry]:
        """Return all stored audit log entries (for testing/inspection)."""
        return list(self._entries)

    async def log_event(self, entry: AuditLogEntry) -> str:
        """Append an audit log entry with hash chain link.

        Sets the previous_hash to link to the predecessor entry, computes
        the entry_hash as SHA-256 of the entry JSON (excluding entry_hash),
        and persists the entry.

        Args:
            entry: The audit log entry to persist.

        Returns:
            The entry_hash of the persisted audit log entry.
        """
        # Link to previous entry in the hash chain
        entry.previous_hash = self._previous_hash

        # Compute entry_hash from JSON excluding the entry_hash field
        entry.entry_hash = None  # Ensure excluded from hash computation
        entry_json_for_hash = entry.model_dump_json(exclude={"entry_hash"})
        entry_hash = hashlib.sha256(entry_json_for_hash.encode()).hexdigest()
        entry.entry_hash = entry_hash

        # Update chain state
        self._previous_hash = entry_hash

        # Persist to in-memory buffer (S3 in production)
        self._entries.append(entry.model_copy(deep=True))

        # In production: persist to S3 with append-only key pattern
        # key = f"audit/{entry.evaluation_id}/{entry.timestamp.isoformat()}_{entry_hash[:8]}.json"
        # await self._put_object(key, entry.model_dump_json())

        return entry_hash

    async def query_by_evaluation_id(
        self,
        evaluation_id: str,
    ) -> list[AuditLogEntry]:
        """Retrieve all audit entries for an evaluation.

        Args:
            evaluation_id: The evaluation identifier to query by.

        Returns:
            List of audit log entries ordered by timestamp.
        """
        results = [
            entry
            for entry in self._entries
            if entry.evaluation_id == evaluation_id
        ]
        return sorted(results, key=lambda e: e.timestamp)

    async def query_by_time_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[AuditLogEntry]:
        """Retrieve audit entries within time range.

        Args:
            start: Start of the time range (inclusive).
            end: End of the time range (inclusive).

        Returns:
            List of audit log entries within the specified range.
        """
        results = [
            entry
            for entry in self._entries
            if start <= entry.timestamp <= end
        ]
        return sorted(results, key=lambda e: e.timestamp)

    def verify_chain(self, entries: list[AuditLogEntry] | None = None) -> bool:
        """Verify hash chain integrity for a sequence of entries.

        Checks that each entry's previous_hash correctly references the
        preceding entry's entry_hash, and that each entry_hash matches
        the recomputed SHA-256 of the entry content.

        Args:
            entries: List of entries to verify. If None, verifies all
                stored entries in order.

        Returns:
            True if the hash chain is valid, False if tampering is detected.
        """
        if entries is None:
            entries = sorted(self._entries, key=lambda e: e.timestamp)

        if not entries:
            return True

        for i, entry in enumerate(entries):
            # Verify previous_hash linkage
            if i == 0:
                if entry.previous_hash != "GENESIS":
                    return False
            else:
                if entry.previous_hash != entries[i - 1].entry_hash:
                    return False

            # Recompute entry_hash and verify
            recomputed = hashlib.sha256(
                entry.model_dump_json(exclude={"entry_hash"}).encode()
            ).hexdigest()
            if recomputed != entry.entry_hash:
                return False

        return True

    def _compute_entry_hash(self, entry: AuditLogEntry) -> str:
        """Compute SHA-256 hash for an entry (excluding entry_hash field).

        Args:
            entry: The audit log entry to hash.

        Returns:
            Hex-encoded SHA-256 hash string.
        """
        entry_json = entry.model_dump_json(exclude={"entry_hash"})
        return hashlib.sha256(entry_json.encode()).hexdigest()
