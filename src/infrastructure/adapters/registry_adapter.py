"""Registry adapter — simulated government registry verification.

Implements the CustomerRegistryPort interface with deterministic simulation
logic for local development. Known national IDs produce consistent pass
results; unknown IDs produce deterministic pseudo-random results.
"""

from __future__ import annotations

import hashlib
import time
from typing import Literal

from domain.ports.customer_registry_port import CustomerRegistryPort
from domain.schemas.identity import RegistryCheck, RegistryVerificationResult


# Known national IDs that always verify successfully (for testing)
_KNOWN_VALID_IDS: set[str] = {
    "US-123456789",
    "UK-AB123456C",
    "FR-1122334",
    "DE-9876543210",
    "CA-123456789",
    "AU-987654321",
}


class RegistryAdapter(CustomerRegistryPort):
    """Adapter for government registry identity verification.

    Simulates government registry checks with deterministic logic for
    development and testing. In production, this would connect to actual
    government identity verification endpoints.

    Behavior:
    - Known national IDs (in the predefined set) always pass all checks.
    - Unknown IDs produce deterministic results based on a hash of the
      input fields, ensuring reproducible behavior across runs.

    Args:
        endpoint: Registry API endpoint URL (used in production).
    """

    def __init__(self, endpoint: str) -> None:
        """Initialize RegistryAdapter.

        Args:
            endpoint: Registry API endpoint URL.
        """
        self._endpoint = endpoint

    @property
    def endpoint(self) -> str:
        """Return the configured registry endpoint."""
        return self._endpoint

    async def verify_identity(
        self,
        full_name: str,
        national_id: str,
        date_of_birth: str,
    ) -> RegistryVerificationResult:
        """Verify identity against simulated government registry.

        Performs field-level verification checks against the registry.
        Known IDs always pass; unknown IDs produce deterministic results
        based on a hash of the combined input fields.

        Args:
            full_name: Customer's full legal name.
            national_id: National identification number.
            date_of_birth: Date of birth in ISO 8601 format (YYYY-MM-DD).

        Returns:
            Verification result with individual field checks and response time.
        """
        start_time = time.perf_counter()

        if national_id in _KNOWN_VALID_IDS:
            checks = self._generate_all_match_checks(full_name, national_id, date_of_birth)
            is_verified = True
        else:
            checks = self._generate_deterministic_checks(
                full_name, national_id, date_of_birth
            )
            is_verified = all(
                check.registry_status == "match" for check in checks
            )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return RegistryVerificationResult(
            is_verified=is_verified,
            checks=checks,
            registry_response_time_ms=max(elapsed_ms, 1),
        )

    def _generate_all_match_checks(
        self,
        full_name: str,
        national_id: str,
        date_of_birth: str,
    ) -> list[RegistryCheck]:
        """Generate all-pass registry checks for known valid IDs.

        Args:
            full_name: Customer's full legal name.
            national_id: National identification number.
            date_of_birth: Date of birth in ISO 8601 format.

        Returns:
            List of RegistryCheck entries all showing "match" status.
        """
        return [
            RegistryCheck(
                field_name="full_name",
                registry_status="match",
                discrepancy_details=None,
            ),
            RegistryCheck(
                field_name="national_id",
                registry_status="match",
                discrepancy_details=None,
            ),
            RegistryCheck(
                field_name="date_of_birth",
                registry_status="match",
                discrepancy_details=None,
            ),
        ]

    def _generate_deterministic_checks(
        self,
        full_name: str,
        national_id: str,
        date_of_birth: str,
    ) -> list[RegistryCheck]:
        """Generate deterministic registry checks for unknown IDs.

        Uses a hash of the combined input fields to produce reproducible
        results. Each field check status is determined by specific bits
        in the hash digest.

        Args:
            full_name: Customer's full legal name.
            national_id: National identification number.
            date_of_birth: Date of birth in ISO 8601 format.

        Returns:
            List of RegistryCheck entries with deterministic statuses.
        """
        # Create deterministic hash from all input fields
        combined = f"{full_name}|{national_id}|{date_of_birth}"
        digest = hashlib.sha256(combined.encode()).digest()

        # Use different bytes for each field's status determination
        name_status = self._status_from_byte(digest[0])
        id_status = self._status_from_byte(digest[1])
        dob_status = self._status_from_byte(digest[2])

        checks: list[RegistryCheck] = []

        checks.append(
            RegistryCheck(
                field_name="full_name",
                registry_status=name_status,
                discrepancy_details=(
                    "Name does not match registry records"
                    if name_status == "mismatch"
                    else (
                        "Name not found in registry"
                        if name_status == "not_found"
                        else None
                    )
                ),
            )
        )

        checks.append(
            RegistryCheck(
                field_name="national_id",
                registry_status=id_status,
                discrepancy_details=(
                    "National ID does not match registry records"
                    if id_status == "mismatch"
                    else (
                        "National ID not found in registry"
                        if id_status == "not_found"
                        else None
                    )
                ),
            )
        )

        checks.append(
            RegistryCheck(
                field_name="date_of_birth",
                registry_status=dob_status,
                discrepancy_details=(
                    "Date of birth does not match registry records"
                    if dob_status == "mismatch"
                    else (
                        "Date of birth not found in registry"
                        if dob_status == "not_found"
                        else None
                    )
                ),
            )
        )

        return checks

    @staticmethod
    def _status_from_byte(
        byte_val: int,
    ) -> Literal["match", "mismatch", "not_found"]:
        """Determine registry status from a single byte value.

        Distributes outcomes as: 70% match, 20% mismatch, 10% not_found.

        Args:
            byte_val: A byte value (0-255) from the hash digest.

        Returns:
            A registry status literal.
        """
        if byte_val < 179:  # ~70% of 256
            return "match"
        if byte_val < 230:  # ~20% of 256
            return "mismatch"
        return "not_found"  # ~10% of 256
