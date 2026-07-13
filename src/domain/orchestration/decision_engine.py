"""Decision engine for KYC evaluation risk scoring and final decisions.

Implements configurable weighted composite risk scoring and threshold-based
decision routing. Deterministic: same inputs always produce same decision.
"""

from __future__ import annotations

from src.domain.schemas.config import DecisionConfig
from src.domain.schemas.kyc_state import Decision, KYCState


def compute_composite_risk_score(
    identity_confidence: float,
    sanctions_match_score: float,
    network_risk_score: float,
    config: DecisionConfig,
) -> float:
    """Compute weighted composite risk score from agent results.

    The composite score combines three signals:
    - Identity confidence (inverted: low confidence = high risk)
    - Sanctions match score (direct: high score = high risk)
    - Network risk score (direct: high score = high risk)

    All inputs and output are bounded [0.0, 1.0].

    Args:
        identity_confidence: Confidence from identity verification (0-1).
        sanctions_match_score: Highest match score from sanctions screening (0-1).
        network_risk_score: Risk score from graph network analysis (0-1).
        config: Decision configuration with weights and thresholds.

    Returns:
        Composite risk score bounded between 0.0 and 1.0.
    """
    score = (
        (1.0 - identity_confidence) * config.identity_weight
        + sanctions_match_score * config.sanctions_weight
        + network_risk_score * config.network_weight
    )
    return max(0.0, min(1.0, score))


def has_critical_flag(state: KYCState) -> bool:
    """Check if any agent returned a critical flag.

    Critical flags trigger immediate DENY regardless of composite score:
    - Confirmed sanctions match (has_confirmed_match)
    - Confirmed fraud ring membership (has_confirmed_fraud_ring)

    Args:
        state: Current KYC evaluation state.

    Returns:
        True if a critical flag is present.
    """
    if (
        state.sanctions_screening_result is not None
        and state.sanctions_screening_result.has_confirmed_match
    ):
        return True
    if (
        state.graph_analysis_result is not None
        and state.graph_analysis_result.has_confirmed_fraud_ring
    ):
        return True
    return False


def evaluate_decision(state: KYCState, config: DecisionConfig) -> Decision:
    """Determine final KYC decision from composite score and critical flags.

    Decision rules (applied in order):
    1. Any critical_flag → DENY (regardless of composite score)
    2. composite_risk_score < approval_threshold → APPROVE
    3. composite_risk_score > denial_threshold → DENY
    4. Otherwise → ESCALATE_TO_HUMAN_REVIEW

    Args:
        state: Complete KYC evaluation state with all agent results.
        config: Decision configuration with thresholds and weights.

    Returns:
        Final decision: APPROVE, DENY, or ESCALATE_TO_HUMAN_REVIEW.
    """
    # Rule 1: Critical flags always result in DENY
    if has_critical_flag(state):
        return Decision.DENY

    # Extract scores from agent results (default to safe values if missing)
    identity_confidence = (
        state.identity_verification_result.confidence_score
        if state.identity_verification_result is not None
        else 0.0
    )
    sanctions_score = (
        state.sanctions_screening_result.match_score
        if state.sanctions_screening_result is not None
        else 0.0
    )
    network_score = (
        state.graph_analysis_result.network_risk_score
        if state.graph_analysis_result is not None
        else 0.0
    )

    # Compute composite risk score
    composite = compute_composite_risk_score(
        identity_confidence,
        sanctions_score,
        network_score,
        config,
    )

    # Rule 2-4: Threshold-based routing
    if composite < config.approval_threshold:
        return Decision.APPROVE
    if composite > config.denial_threshold:
        return Decision.DENY
    return Decision.ESCALATE_TO_HUMAN_REVIEW


def compute_decision_audit_payload(
    state: KYCState,
    config: DecisionConfig,
    decision: Decision,
) -> dict[str, object]:
    """Generate audit payload documenting the decision calculation.

    Args:
        state: Complete KYC evaluation state.
        config: Decision configuration used.
        decision: The final decision made.

    Returns:
        Dictionary with all input scores, weights, thresholds, and result.
    """
    identity_confidence = (
        state.identity_verification_result.confidence_score
        if state.identity_verification_result is not None
        else 0.0
    )
    sanctions_score = (
        state.sanctions_screening_result.match_score
        if state.sanctions_screening_result is not None
        else 0.0
    )
    network_score = (
        state.graph_analysis_result.network_risk_score
        if state.graph_analysis_result is not None
        else 0.0
    )

    composite = compute_composite_risk_score(
        identity_confidence, sanctions_score, network_score, config
    )

    return {
        "identity_confidence_score": identity_confidence,
        "sanctions_match_score": sanctions_score,
        "network_risk_score": network_score,
        "composite_risk_score": composite,
        "identity_weight": config.identity_weight,
        "sanctions_weight": config.sanctions_weight,
        "network_weight": config.network_weight,
        "approval_threshold": config.approval_threshold,
        "denial_threshold": config.denial_threshold,
        "has_critical_flag": has_critical_flag(state),
        "final_decision": decision.value,
    }
