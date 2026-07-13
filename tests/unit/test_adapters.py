"""Unit tests for infrastructure adapters (Task 7.3)."""

from __future__ import annotations

import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from domain.schemas.audit import AuditLogEntry
from domain.schemas.identity import RegistryCheck, RegistryVerificationResult
from domain.schemas.sanctions import WatchlistSearchResult
from infrastructure.adapters.duckdb_adapter import DuckDBAdapter
from infrastructure.adapters.registry_adapter import RegistryAdapter
from infrastructure.adapters.s3_audit_log_adapter import S3AuditLogAdapter
from infrastructure.adapters.watchlist_api_adapter import WatchlistAPIAdapter
from infrastructure.resilience.circuit_breaker import CircuitState


# --- WatchlistAPIAdapter Tests ---


class TestWatchlistAPIAdapter:
    """Tests for WatchlistAPIAdapter."""

    @pytest.fixture
    def adapter(self) -> WatchlistAPIAdapter:
        """Create a watchlist adapter with all sources."""
        return WatchlistAPIAdapter(
            sources=["ofac_sdn", "eu_sanctions", "un_sanctions", "pep"]
        )

    @pytest.mark.asyncio
    async def test_search_by_name_exact_match(self, adapter: WatchlistAPIAdapter) -> None:
        """Test that exact name matches return results."""
        result = await adapter.search_by_name("Viktor Bout", threshold=0.85)
        assert isinstance(result, WatchlistSearchResult)
        assert len(result.entries) >= 1
        assert result.entries[0].matched_entity.entity_name == "Viktor Bout"
        assert result.entries[0].similarity_score == 1.0

    @pytest.mark.asyncio
    async def test_search_by_name_fuzzy_match(self, adapter: WatchlistAPIAdapter) -> None:
        """Test that fuzzy name matches work within threshold."""
        result = await adapter.search_by_name("Viktor Boutt", threshold=0.80)
        assert len(result.entries) >= 1

    @pytest.mark.asyncio
    async def test_search_by_name_no_match(self, adapter: WatchlistAPIAdapter) -> None:
        """Test that non-matching names return empty results."""
        result = await adapter.search_by_name("John Smith", threshold=0.85)
        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_search_by_name_returns_sources_queried(
        self, adapter: WatchlistAPIAdapter
    ) -> None:
        """Test that sources_queried is populated."""
        result = await adapter.search_by_name("anyone")
        assert "ofac_sdn" in result.sources_queried
        assert "eu_sanctions" in result.sources_queried

    @pytest.mark.asyncio
    async def test_search_by_national_id_exact(self, adapter: WatchlistAPIAdapter) -> None:
        """Test exact national ID matching."""
        result = await adapter.search_by_national_id("RU-1234567890")
        assert len(result.entries) == 1
        assert result.entries[0].matched_entity.entity_name == "Viktor Bout"
        assert result.entries[0].similarity_score == 1.0

    @pytest.mark.asyncio
    async def test_search_by_national_id_no_match(self, adapter: WatchlistAPIAdapter) -> None:
        """Test national ID with no match."""
        result = await adapter.search_by_national_id("XX-0000000000")
        assert len(result.entries) == 0

    @pytest.mark.asyncio
    async def test_search_by_date_of_birth(self, adapter: WatchlistAPIAdapter) -> None:
        """Test combined DOB and name search."""
        result = await adapter.search_by_date_of_birth("1967-01-13", "Viktor Bout")
        assert len(result.entries) >= 1
        assert result.entries[0].similarity_score > 0.5

    @pytest.mark.asyncio
    async def test_circuit_breaker_integration(self, adapter: WatchlistAPIAdapter) -> None:
        """Test that circuit breaker is properly integrated."""
        assert adapter.circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_source_filtering(self) -> None:
        """Test that adapter only searches configured sources."""
        adapter = WatchlistAPIAdapter(sources=["ofac_sdn"])
        result = await adapter.search_by_name("Elena Petrov", threshold=0.85)
        # Elena Petrov is in eu_sanctions, not ofac_sdn
        assert len(result.entries) == 0


# --- S3AuditLogAdapter Tests ---


class TestS3AuditLogAdapter:
    """Tests for S3AuditLogAdapter."""

    @pytest.fixture
    def adapter(self) -> S3AuditLogAdapter:
        """Create an audit log adapter."""
        return S3AuditLogAdapter(bucket="test-audit-bucket")

    def _make_entry(self, evaluation_id: str = "eval-001") -> AuditLogEntry:
        """Create a test audit log entry."""
        return AuditLogEntry(
            entry_id=str(uuid4()),
            evaluation_id=evaluation_id,
            event_type="identity_verification_started",
            timestamp=datetime.now(tz=timezone.utc),
            agent_name="identity_verifier",
        )

    @pytest.mark.asyncio
    async def test_log_event_returns_hash(self, adapter: S3AuditLogAdapter) -> None:
        """Test that log_event returns a valid hash."""
        entry = self._make_entry()
        entry_hash = await adapter.log_event(entry)
        assert isinstance(entry_hash, str)
        assert len(entry_hash) == 64  # SHA-256 hex

    @pytest.mark.asyncio
    async def test_hash_chain_genesis(self, adapter: S3AuditLogAdapter) -> None:
        """Test that first entry has GENESIS as previous_hash."""
        entry = self._make_entry()
        await adapter.log_event(entry)
        stored = adapter.entries[0]
        assert stored.previous_hash == "GENESIS"

    @pytest.mark.asyncio
    async def test_hash_chain_linkage(self, adapter: S3AuditLogAdapter) -> None:
        """Test that entries are properly chained."""
        entry1 = self._make_entry()
        hash1 = await adapter.log_event(entry1)

        entry2 = self._make_entry()
        await adapter.log_event(entry2)

        stored2 = adapter.entries[1]
        assert stored2.previous_hash == hash1

    @pytest.mark.asyncio
    async def test_verify_chain_valid(self, adapter: S3AuditLogAdapter) -> None:
        """Test chain verification with valid entries."""
        for _ in range(5):
            entry = self._make_entry()
            await adapter.log_event(entry)

        assert adapter.verify_chain() is True

    @pytest.mark.asyncio
    async def test_verify_chain_tampered(self, adapter: S3AuditLogAdapter) -> None:
        """Test chain verification detects tampering."""
        for _ in range(3):
            entry = self._make_entry()
            await adapter.log_event(entry)

        # Tamper with an entry
        adapter._entries[1].entry_hash = "tampered_hash_value"
        assert adapter.verify_chain() is False

    @pytest.mark.asyncio
    async def test_query_by_evaluation_id(self, adapter: S3AuditLogAdapter) -> None:
        """Test querying entries by evaluation ID."""
        entry1 = self._make_entry("eval-001")
        entry2 = self._make_entry("eval-002")
        entry3 = self._make_entry("eval-001")

        await adapter.log_event(entry1)
        await adapter.log_event(entry2)
        await adapter.log_event(entry3)

        results = await adapter.query_by_evaluation_id("eval-001")
        assert len(results) == 2
        assert all(e.evaluation_id == "eval-001" for e in results)

    @pytest.mark.asyncio
    async def test_query_by_time_range(self, adapter: S3AuditLogAdapter) -> None:
        """Test querying entries by time range."""
        entry = self._make_entry()
        await adapter.log_event(entry)

        start = datetime(2020, 1, 1, tzinfo=timezone.utc)
        end = datetime(2030, 12, 31, tzinfo=timezone.utc)
        results = await adapter.query_by_time_range(start, end)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_verify_chain_empty(self, adapter: S3AuditLogAdapter) -> None:
        """Test that empty chain is considered valid."""
        assert adapter.verify_chain() is True


# --- DuckDBAdapter Tests ---


class TestDuckDBAdapter:
    """Tests for DuckDBAdapter."""

    @pytest.fixture
    def adapter(self) -> DuckDBAdapter:
        """Create an in-memory DuckDB adapter."""
        return DuckDBAdapter(db_path=":memory:")

    @pytest.fixture
    def csv_file(self, tmp_path: Path) -> Path:
        """Create a temporary CSV file for testing."""
        csv_path = tmp_path / "test_data.csv"
        csv_path.write_text("id,name,score\n1,Alice,0.95\n2,Bob,0.80\n3,Charlie,0.70\n")
        return csv_path

    @pytest.mark.asyncio
    async def test_load_raw_data(self, adapter: DuckDBAdapter, csv_file: Path) -> None:
        """Test loading CSV data into DuckDB."""
        row_count = await adapter.load_raw_data(str(csv_file), "test_table")
        assert row_count == 3

    @pytest.mark.asyncio
    async def test_load_raw_data_file_not_found(self, adapter: DuckDBAdapter) -> None:
        """Test that missing CSV raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            await adapter.load_raw_data("/nonexistent/file.csv", "test_table")

    @pytest.mark.asyncio
    async def test_execute_query(self, adapter: DuckDBAdapter, csv_file: Path) -> None:
        """Test executing a query and getting results."""
        await adapter.load_raw_data(str(csv_file), "test_table")
        results = await adapter.execute_query("SELECT * FROM test_table WHERE score > 0.75")
        assert len(results) == 2
        assert results[0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_export_to_csv(self, adapter: DuckDBAdapter, csv_file: Path, tmp_path: Path) -> None:
        """Test exporting query results to CSV."""
        await adapter.load_raw_data(str(csv_file), "test_table")
        output_path = str(tmp_path / "output" / "export.csv")
        result_path = await adapter.export_to_csv("SELECT * FROM test_table", output_path)
        assert Path(result_path).exists()
        content = Path(result_path).read_text()
        assert "Alice" in content

    @pytest.mark.asyncio
    async def test_db_path_property(self, adapter: DuckDBAdapter) -> None:
        """Test db_path property."""
        assert adapter.db_path == ":memory:"


# --- RegistryAdapter Tests ---


class TestRegistryAdapter:
    """Tests for RegistryAdapter."""

    @pytest.fixture
    def adapter(self) -> RegistryAdapter:
        """Create a registry adapter."""
        return RegistryAdapter(endpoint="https://registry.example.gov/api/v1")

    @pytest.mark.asyncio
    async def test_verify_known_id(self, adapter: RegistryAdapter) -> None:
        """Test that known IDs always verify successfully."""
        result = await adapter.verify_identity(
            full_name="Test User",
            national_id="US-123456789",
            date_of_birth="1990-01-15",
        )
        assert isinstance(result, RegistryVerificationResult)
        assert result.is_verified is True
        assert len(result.checks) == 3
        assert all(c.registry_status == "match" for c in result.checks)

    @pytest.mark.asyncio
    async def test_verify_unknown_id_deterministic(self, adapter: RegistryAdapter) -> None:
        """Test that unknown IDs produce consistent results."""
        result1 = await adapter.verify_identity(
            full_name="Unknown Person",
            national_id="XX-0000000",
            date_of_birth="1985-06-20",
        )
        result2 = await adapter.verify_identity(
            full_name="Unknown Person",
            national_id="XX-0000000",
            date_of_birth="1985-06-20",
        )
        # Results should be deterministic
        assert result1.is_verified == result2.is_verified
        for c1, c2 in zip(result1.checks, result2.checks):
            assert c1.registry_status == c2.registry_status

    @pytest.mark.asyncio
    async def test_verify_returns_response_time(self, adapter: RegistryAdapter) -> None:
        """Test that response time is captured."""
        result = await adapter.verify_identity(
            full_name="Test User",
            national_id="US-123456789",
            date_of_birth="1990-01-15",
        )
        assert result.registry_response_time_ms >= 0

    @pytest.mark.asyncio
    async def test_endpoint_property(self, adapter: RegistryAdapter) -> None:
        """Test endpoint property."""
        assert adapter.endpoint == "https://registry.example.gov/api/v1"

    @pytest.mark.asyncio
    async def test_field_checks_have_correct_fields(self, adapter: RegistryAdapter) -> None:
        """Test that field checks cover all expected fields."""
        result = await adapter.verify_identity(
            full_name="Test User",
            national_id="US-123456789",
            date_of_birth="1990-01-15",
        )
        field_names = [c.field_name for c in result.checks]
        assert "full_name" in field_names
        assert "national_id" in field_names
        assert "date_of_birth" in field_names
