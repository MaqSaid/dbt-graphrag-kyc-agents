"""KYC evaluation API routes.

Provides endpoints for submitting evaluations, polling status,
and retrieving compliance reports.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Header, HTTPException

from src.domain.schemas.api import (
    ComplianceReportResponse,
    CustomerOnboardingRequest,
    ErrorResponse,
    EvaluationAcceptedResponse,
    EvaluationStatusResponse,
)
from src.domain.schemas.kyc_state import Decision

router = APIRouter(prefix="/api/v1/kyc", tags=["kyc"])

# In-memory store (would be replaced with persistent storage)
_evaluations: dict[str, dict] = {}


@router.post(
    "/evaluate",
    status_code=202,
    response_model=EvaluationAcceptedResponse,
)
async def submit_evaluation(
    request: CustomerOnboardingRequest,
    x_correlation_id: str | None = Header(None),
) -> EvaluationAcceptedResponse:
    """Accept a customer onboarding payload for KYC evaluation.

    Returns a 202 Accepted with an evaluation_id for polling.

    Args:
        request: Customer onboarding data.
        x_correlation_id: Optional correlation ID for tracing.

    Returns:
        Accepted response with evaluation_id.
    """
    evaluation_id = str(uuid.uuid4())
    _evaluations[evaluation_id] = {
        "status": "in_progress",
        "current_stage": "initialize",
        "created_at": datetime.now(tz=timezone.utc),
        "updated_at": datetime.now(tz=timezone.utc),
        "correlation_id": x_correlation_id,
        "request": request.model_dump(),
    }

    return EvaluationAcceptedResponse(evaluation_id=evaluation_id)


@router.get(
    "/status/{evaluation_id}",
    response_model=EvaluationStatusResponse,
)
async def get_evaluation_status(evaluation_id: str) -> EvaluationStatusResponse:
    """Return the current evaluation state.

    Args:
        evaluation_id: The evaluation to query.

    Returns:
        Current status of the evaluation.

    Raises:
        HTTPException: 404 if evaluation not found.
    """
    if evaluation_id not in _evaluations:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    eval_data = _evaluations[evaluation_id]
    return EvaluationStatusResponse(
        evaluation_id=evaluation_id,
        status=eval_data["status"],
        current_stage=eval_data.get("current_stage"),
        final_decision=eval_data.get("final_decision"),
        created_at=eval_data["created_at"],
        updated_at=eval_data["updated_at"],
    )


@router.get(
    "/report/{evaluation_id}",
    response_model=ComplianceReportResponse,
)
async def get_evaluation_report(evaluation_id: str) -> ComplianceReportResponse:
    """Return the completed compliance report and decision.

    Args:
        evaluation_id: The evaluation to query.

    Returns:
        Compliance report with final decision.

    Raises:
        HTTPException: 404 if not found, 409 if not yet complete.
    """
    if evaluation_id not in _evaluations:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    eval_data = _evaluations[evaluation_id]
    if eval_data["status"] != "completed":
        raise HTTPException(status_code=409, detail="Evaluation not yet complete")

    return ComplianceReportResponse(
        evaluation_id=evaluation_id,
        report_id=eval_data.get("report_id", ""),
        final_decision=eval_data.get("final_decision", Decision.PENDING),
        executive_summary=eval_data.get("executive_summary", ""),
        risk_score=eval_data.get("risk_score", 0.0),
        generation_timestamp=eval_data["updated_at"],
    )
