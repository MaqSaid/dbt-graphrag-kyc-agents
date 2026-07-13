"""API request and response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.domain.schemas.kyc_state import Decision


class CustomerOnboardingRequest(BaseModel):
    """API request body for submitting a KYC evaluation."""

    model_config = ConfigDict(strict=True)

    full_name: str = Field(min_length=2, max_length=200)
    date_of_birth: str = Field(
        description="Date of birth in ISO 8601 format (YYYY-MM-DD)"
    )
    national_id: str = Field(min_length=5, max_length=30)
    address: str = Field(min_length=10, max_length=500)
    email: str
    phone: str
    ip_address: str


class EvaluationAcceptedResponse(BaseModel):
    """Response returned when an evaluation is accepted (202)."""

    model_config = ConfigDict(strict=True)

    evaluation_id: str
    status: str = "accepted"
    message: str = "KYC evaluation submitted successfully"


class EvaluationStatusResponse(BaseModel):
    """Response for evaluation status polling."""

    model_config = ConfigDict(strict=True)

    evaluation_id: str
    status: str
    current_stage: str | None = None
    final_decision: Decision | None = None
    created_at: datetime
    updated_at: datetime


class ComplianceReportResponse(BaseModel):
    """Response containing the completed compliance report."""

    model_config = ConfigDict(strict=True)

    evaluation_id: str
    report_id: str
    final_decision: Decision
    executive_summary: str
    risk_score: float = Field(ge=0.0, le=1.0)
    generation_timestamp: datetime
    report_url: str | None = None


class ErrorResponse(BaseModel):
    """Standardized API error response."""

    model_config = ConfigDict(strict=True)

    error_code: str
    message: str
    details: list[dict[str, str]] | None = None
    correlation_id: str
    timestamp: datetime
