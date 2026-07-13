"""Port interface for government registry verification."""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.domain.schemas.identity import RegistryVerificationResult


class CustomerRegistryPort(ABC):
    """Abstract interface for government registry verification.

    Provides identity verification against official government
    databases and registries.
    """

    @abstractmethod
    async def verify_identity(
        self, full_name: str, national_id: str, date_of_birth: str
    ) -> RegistryVerificationResult:
        """Verify identity against government registry.

        Args:
            full_name: Customer's full legal name.
            national_id: National identification number.
            date_of_birth: Date of birth in ISO format.

        Returns:
            Verification result with match/mismatch details.
        """
        ...
