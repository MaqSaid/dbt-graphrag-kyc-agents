"""KYC evaluation state aggregate root."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.domain.schemas.graph_analysis import GraphAnalysisResult
from src.domain.schemas.identity import (
    CustomerOnboardingPayload,
    IdentityVerificationResult,
)
from src.domain.schemas.reporting import ComplianceReport
from src.domain.schemas.sanctions import SanctionsScreeningResult


class Decision(str, Enum):
    """Final outcome of a KYC evaluation."""

    PENDING = "PENDING"
    APPROVE = "APPROVE"
    DENY = "DENY"
    ESCALATE_TO_HUMAN_REVIEW = "ESCALATE_TO_HUMAN_REVIEW"


class StateTransition(BaseModel):
    """Record of a single state machine transition."""

    model_config = ConfigDict(strict=True)

    from_node: str
    to_node: str
    timestamp: datetime
    condition_evaluated: str | None = None
    result: str | None = None


class KYCState(BaseModel):
    """Aggregate root for the KYC evaluation lifecycle.

    This model represents the complete evaluation state that flows through
    the LangGraph state machine. All agents read from and write to this state.
    """

    model_config = ConfigDict(strict=True)

    evaluation_id: str
    customer_data: CustomerOnboardingPayload | None = None
    identity_verification_result: IdentityVerificationResult | None = None
    sanctions_screening_result: SanctionsScreeningResult | None = None
    graph_analysis_result: GraphAnalysisResult | None = None
    compliance_report: ComplianceReport | None = None
    final_decision: Decision = Decision.PENDING
    state_history: list[StateTransition] = Field(default_factory=list)
    retry_count_identity: int = Field(default=0, ge=0, le=3)
    retry_count_sanctions: int = Field(default=0, ge=0, le=3)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    correlation_id: str | None = None

    @field_validator("final_decision")
    @classmethod
    def validate_decision(cls, v: Decision) -> Decision:
        """Ensure decision is a valid enum value."""
        if not isinstance(v, Decision):
            msg = f"final_decision must be a Decision enum, got {type(v)}"
            raise ValueError(msg)
        return v
