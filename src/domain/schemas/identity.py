"""Identity domain schemas for customer onboarding and verification."""

from __future__ import annotations

import re
from datetime import date
from ipaddress import ip_address as validate_ip_address
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerOnboardingPayload(BaseModel):
    """Inbound customer data for KYC evaluation."""

    model_config = ConfigDict(strict=True)

    full_name: str = Field(min_length=2, max_length=200)
    date_of_birth: date
    national_id: str = Field(min_length=5, max_length=30)
    address: str = Field(min_length=10, max_length=500)
    email: str
    phone: str
    ip_address: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email against RFC 5322 simplified format."""
        pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            msg = "Email must conform to RFC 5322 format"
            raise ValueError(msg)
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone_e164(cls, v: str) -> str:
        """Validate phone number against E.164 format."""
        if not re.match(r"^\+[1-9]\d{6,14}$", v):
            msg = "Phone must be in E.164 format (e.g., +14155552671)"
            raise ValueError(msg)
        return v

    @field_validator("ip_address")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IPv4 or IPv6 address format."""
        try:
            validate_ip_address(v)
        except ValueError as e:
            msg = f"Invalid IP address: {v}"
            raise ValueError(msg) from e
        return v


class FieldValidation(BaseModel):
    """Result of validating a single identity field."""

    model_config = ConfigDict(strict=True)

    field_name: str
    is_valid: bool
    error_description: str | None = None


class RegistryCheck(BaseModel):
    """Result of checking a field against government registry."""

    model_config = ConfigDict(strict=True)

    field_name: str
    registry_status: Literal["match", "mismatch", "not_found"]
    discrepancy_details: str | None = None


class RegistryVerificationResult(BaseModel):
    """Result from government registry verification."""

    model_config = ConfigDict(strict=True)

    is_verified: bool
    checks: list[RegistryCheck]
    registry_source: str


class IdentityVerificationResult(BaseModel):
    """Complete result of identity verification process."""

    model_config = ConfigDict(strict=True)

    verification_status: Literal["verified", "verification_failed", "ambiguous"]
    field_validations: list[FieldValidation]
    registry_checks: list[RegistryCheck]
    confidence_score: float = Field(ge=0.0, le=1.0)
    processing_time_ms: int = Field(ge=0)
