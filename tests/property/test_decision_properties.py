"""Property-based tests for decision engine.

Validates:
- Property 2: Composite Risk Score Range Invariant
- Property 3: Decision Determinism
"""

from __future__ import annotations

from hypothesis import given, settings

from src.domain.orchestration.decision_engine import (
    compute_composite_risk_score,
    evaluate_decision,
    has_critical_flag,
)
from src.domain.schemas.config import DecisionConfig
from src.domain.schemas.kyc_state import Decision, KYCState
from tests.property.strategies import (
    decision_configs,
    graph_analysis_results,
    identity_verification_results,
    risk_scores,
    sanctions_screening_results,
)


@settings(max_examples=200)
@given(
    identity_confidence=risk_scores(),
    sanctions_score=risk_scores(),
    network_score=risk_scores(),
    config=decision_configs(),
)
def test_composite_score_always_bounded(
    identity_confidence: float,
    sanctions_score: float,
    network_score: float,
    config: DecisionConfig,
) -> None:
    """Property 2: Composite risk score is always in [0.0, 1.0].

    For any input scores in [0,1] and valid weights,
    the computed composite score must be bounded.
    """
    score = compute_composite_risk_score(
        identity_confidence, sanctions_score, network_score, config
    )
    assert 0.0 <= score <= 1.0, f"Score {score} out of bounds"


@settings(max_examples=200)
@given(
    identity_confidence=risk_scores(),
    sanctions_score=risk_scores(),
    network_score=risk_scores(),
    config=decision_configs(),
)
def test_decision_is_deterministic(
    identity_confidence: float,
    sanctions_score: float,
    network_score: float,
    config: DecisionConfig,
) -> None:
    """Property 3: Same inputs always produce same decision.

    The decision engine must be deterministic — calling it twice
    with identical inputs must yield identical results.
    """
    # Build a minimal KYCState with the given scores
    from src.domain.schemas.graph_analysis import GraphAnalysisResult
    from src.domain.schemas.identity import (
        FieldValidation,
        IdentityVerificationResult,
        RegistryCheck,
    )
    from src.domain.schemas.sanctions import SanctionsScreeningResult

    iv_result = IdentityVerificationResult(
        verification_status="verified",
        field_validations=[FieldValidation(field_name="email", is_valid=True)],
        registry_checks=[RegistryCheck(field_name="national_id", registry_status="match")],
        confidence_score=identity_confidence,
        processing_time_ms=500,
    )
    ss_result = SanctionsScreeningResult(
        status="screening_clear",
        matches=[],
        match_score=sanctions_score,
        has_confirmed_match=False,
        sources_screened=["ofac_sdn"],
        processing_time_ms=500,
    )
    ga_result = GraphAnalysisResult(
        status="graph_clear",
        discovered_paths=[],
        network_risk_score=network_score,
        connected_flagged_entities=[],
        has_confirmed_fraud_ring=False,
        traversal_metadata={},
        processing_time_ms=500,
    )

    state = KYCState(
        evaluation_id="test-determinism",
        identity_verification_result=iv_result,
        sanctions_screening_result=ss_result,
        graph_analysis_result=ga_result,
    )

    decision1 = evaluate_decision(state, config)
    decision2 = evaluate_decision(state, config)
    assert decision1 == decision2, f"Non-deterministic: {decision1} != {decision2}"


@settings(max_examples=100)
@given(
    identity_confidence=risk_scores(),
    sanctions_score=risk_scores(),
    network_score=risk_scores(),
)
def test_critical_flag_always_denies(
    identity_confidence: float,
    sanctions_score: float,
    network_score: float,
) -> None:
    """Critical flags always result in DENY regardless of scores."""
    from src.domain.schemas.graph_analysis import GraphAnalysisResult
    from src.domain.schemas.identity import (
        FieldValidation,
        IdentityVerificationResult,
        RegistryCheck,
    )
    from src.domain.schemas.sanctions import SanctionsScreeningResult

    config = DecisionConfig()

    # State with confirmed sanctions match (critical flag)
    state = KYCState(
        evaluation_id="test-critical",
        identity_verification_result=IdentityVerificationResult(
            verification_status="verified",
            field_validations=[FieldValidation(field_name="email", is_valid=True)],
            registry_checks=[RegistryCheck(field_name="national_id", registry_status="match")],
            confidence_score=identity_confidence,
            processing_time_ms=500,
        ),
        sanctions_screening_result=SanctionsScreeningResult(
            status="screening_hit",
            matches=[],
            match_score=sanctions_score,
            has_confirmed_match=True,  # CRITICAL FLAG
            sources_screened=["ofac_sdn"],
            processing_time_ms=500,
        ),
        graph_analysis_result=GraphAnalysisResult(
            status="graph_clear",
            discovered_paths=[],
            network_risk_score=network_score,
            connected_flagged_entities=[],
            has_confirmed_fraud_ring=False,
            traversal_metadata={},
            processing_time_ms=500,
        ),
    )

    decision = evaluate_decision(state, config)
    assert decision == Decision.DENY, f"Expected DENY with critical flag, got {decision}"
