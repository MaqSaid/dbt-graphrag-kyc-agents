"""Identity verification domain service.

Implements structural field validation and government registry verification
for the Identity bounded context.
"""

from __future__ import annotations

import ipaddress
import re
import time
from typing import TYPE_CHECKING

from domain.schemas.identity import (
    CustomerOnboardingPayload,
    FieldValidation,
    IdentityVerificationResult,
)

if TYPE_CHECKING:
    from domain.ports.customer_registry_port import CustomerRegistryPort


class IdentityVerificationService:
    """Domain service for customer identity verification.

    Validates customer onboarding fields structurally and verifies identity
    against a government registry via the CustomerRegistryPort. Computes a
    confidence score based on the ratio of passing checks.

    Args:
        registry_port: Injected port for government registry verification.
    """

    def __init__(self, registry_port: CustomerRegistryPort) -> None:
        """Initialize with injected CustomerRegistryPort.

        Args:
            registry_port: Port implementation for government registry lookups.
        """
        self._registry_port = registry_port

    async def verify_identity(
        self,
        payload: CustomerOnboardingPayload,
    ) -> IdentityVerificationResult:
        """Verify customer identity through structural validation and registry check.

        Performs structural validation of email, phone, IP, and national_id fields,
        then calls the government registry port to verify identity. Computes
        confidence_score based on the fraction of checks that pass.

        Args:
            payload: Customer onboarding data to verify.

        Returns:
            Structured identity verification result with field validations,
            registry checks, confidence score, and processing time.

        Raises:
            ValidationError: If the payload is fundamentally invalid.
        """
        start_time = time.perf_counter()

        # Structural field validations
        field_validations = self._validate_fields(payload)

        # Registry verification via port
        registry_result = await self._registry_port.verify_identity(
            full_name=payload.full_name,
            national_id=payload.national_id,
            date_of_birth=payload.date_of_birth.isoformat(),
        )

        # Compute confidence score from pass/fail counts
        structural_pass_count = sum(
            1 for fv in field_validations if fv.is_valid
        )
        registry_pass_count = sum(
            1 for rc in registry_result.checks if rc.registry_status == "match"
        )
        total_checks = len(field_validations) + len(registry_result.checks)
        total_passed = structural_pass_count + registry_pass_count

        confidence_score = total_passed / total_checks if total_checks > 0 else 0.0

        # Determine verification status
        verification_status = self._determine_status(
            confidence_score, field_validations, registry_result.is_verified,
        )

        elapsed_ms = int((time.perf_counter() - start_time) * 1000)

        return IdentityVerificationResult(
            verification_status=verification_status,
            field_validations=field_validations,
            registry_checks=registry_result.checks,
            confidence_score=confidence_score,
            processing_time_ms=elapsed_ms,
        )

    def _validate_fields(
        self,
        payload: CustomerOnboardingPayload,
    ) -> list[FieldValidation]:
        """Validate each identity field structurally.

        Args:
            payload: Customer onboarding data.

        Returns:
            List of field validation results.
        """
        validations: list[FieldValidation] = []

        # Email validation (RFC 5322 simplified)
        email_valid, email_error = self._validate_email(payload.email)
        validations.append(
            FieldValidation(
                field_name="email",
                is_valid=email_valid,
                error_description=email_error,
            ),
        )

        # Phone validation (E.164)
        phone_valid, phone_error = self._validate_phone(payload.phone)
        validations.append(
            FieldValidation(
                field_name="phone",
                is_valid=phone_valid,
                error_description=phone_error,
            ),
        )

        # IP address validation
        ip_valid, ip_error = self._validate_ip(payload.ip_address)
        validations.append(
            FieldValidation(
                field_name="ip_address",
                is_valid=ip_valid,
                error_description=ip_error,
            ),
        )

        # National ID validation
        nid_valid, nid_error = self._validate_national_id(payload.national_id)
        validations.append(
            FieldValidation(
                field_name="national_id",
                is_valid=nid_valid,
                error_description=nid_error,
            ),
        )

        return validations

    @staticmethod
    def _validate_email(email: str) -> tuple[bool, str | None]:
        """Validate email against RFC 5322 simplified pattern.

        Args:
            email: Email address to validate.

        Returns:
            Tuple of (is_valid, error_description or None).
        """
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(pattern, email):
            return True, None
        return False, "Email does not conform to RFC 5322 format"

    @staticmethod
    def _validate_phone(phone: str) -> tuple[bool, str | None]:
        """Validate phone number against E.164 format.

        Args:
            phone: Phone number to validate.

        Returns:
            Tuple of (is_valid, error_description or None).
        """
        if re.match(r"^\+[1-9]\d{6,14}$", phone):
            return True, None
        return False, "Phone number does not conform to E.164 format"

    @staticmethod
    def _validate_ip(ip_address: str) -> tuple[bool, str | None]:
        """Validate IP address (IPv4 or IPv6).

        Args:
            ip_address: IP address string to validate.

        Returns:
            Tuple of (is_valid, error_description or None).
        """
        try:
            ipaddress.ip_address(ip_address)
            return True, None
        except ValueError:
            return False, "Invalid IP address format"

    @staticmethod
    def _validate_national_id(national_id: str) -> tuple[bool, str | None]:
        """Validate national ID has acceptable length and alphanumeric content.

        Args:
            national_id: National identification number to validate.

        Returns:
            Tuple of (is_valid, error_description or None).
        """
        if len(national_id) < 5 or len(national_id) > 30:
            return False, "National ID must be between 5 and 30 characters"
        if not re.match(r"^[a-zA-Z0-9\-]+$", national_id):
            return False, "National ID must contain only alphanumeric characters and hyphens"
        return True, None

    @staticmethod
    def _determine_status(
        confidence_score: float,
        field_validations: list[FieldValidation],
        registry_verified: bool,
    ) -> str:
        """Determine overall verification status.

        Args:
            confidence_score: Computed confidence from pass/fail ratio.
            field_validations: Results of structural field validations.
            registry_verified: Whether the registry confirmed identity.

        Returns:
            One of "verified", "verification_failed", or "ambiguous".
        """
        all_fields_valid = all(fv.is_valid for fv in field_validations)

        if all_fields_valid and registry_verified and confidence_score >= 0.8:
            return "verified"
        if confidence_score < 0.5:
            return "verification_failed"
        return "ambiguous"
