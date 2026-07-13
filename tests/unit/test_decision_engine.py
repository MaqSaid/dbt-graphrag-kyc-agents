"""Unit tests for the decision engine domain logic."""

from __future__ import annotations

from datetime import date

import pytest

from src.domain.orchestration.decision_engine import (
    compute_composite_risk_score,
    evaluate_decision,
    has_critical_flag,
)
from src.domain.schemas.config import DecisionConfig
from src.domain.schemas.graph_analysis import GraphAnalysisResult
from src.domain.schemas.identity import (
    CustomerOnboardingPayload,
    IdentityVerificationResult,
)
from src.domain.schemas.kyc_state import Decision, KYCState
from src.domain.schemas.sanctions import SanctionsScreeningResult


def _make_config(
    identity_weight: float = 0.3,
    sanctions_weight: float = 0.4,
    network_weight: float = 0.3,
    approval_threshold: float = 0.3,
    denial_threshold: float = 0.7,
) -> DecisionConfig:
    """Create a DecisionConfig with specified or default values."""
    return DecisionConfig(
        identity_weight=identity_weight,
        sanctions_weight=sanctions_weight,
        network_weight=network_weight,
        approval_threshold=approval_threshold,
        denial_threshold=denial_threshold,
    )


def _make_state(
    confidence_score: float = 0.9,
    match_score: float = 0.0,
    network_risk_score: float = 0.0,
    has_confirmed_match: bool = False,
    has_confirmed_fraud_ring: bool = False,
) -> KYCState:
    """Create a KYCState with populated agent results for testing."""
    return KYCState(
        evaluation_id="test-eval-001",
        customer_data=CustomerOnboardingPayload(
            full_name="John Doe",
            date_of_birth=date(1990, 1, 1),
            national_id="AB123456789",
            address="123 Main Street, London, UK, SW1A 1AA",
            email="john.doe@example.com",
            phone="+441234567890",
            ip_address="192.168.1.1",
        ),
        identity_verification_result=IdentityVerificationResult(
            verification_status="verified",
            field_validations=[],
            registry_checks=[],
            confidence_score=confidence_score,
            processing_time_ms=150,
        ),
        sanctions_screening_result=SanctionsScreeningResult(
            status="screening_clear",
            matches=[],
            match_score=match_score,
            has_confirmed_match=has_confirmed_match,
            sources_screened=["ofac_sdn"],
            processing_time_ms=200,
        ),
        graph_analysis_result=GraphAnalysisResult(
            status="graph_clear",
            discovered_paths=[],
            network_risk_score=network_risk_score,
            connected_flagged_entities=[],
            has_confirmed_fraud_ring=has_confirmed_fraud_ring,
            traversal_metadata={},
            processing_time_ms=300,
        ),
    )


class TestComputeCompositeRiskScore:
    """Tests for compute_composite_risk_score function."""

    def test_all_zeros_returns_identity_risk(self) -> None:
        """When all inputs are ideal, only identity inversion contributes."""
        config = _make_config()
        # confidence=1.0 → (1-1)*0.3 + 0*0.4 + 0*0.3 = 0.0
        score = compute_composite_risk_score(1.0, 0.0, 0.0, config)
        assert score == 0.0

    def test_worst_case_all_ones(self) -> None:
        """Maximum risk from all components."""
        config = _make_config()
        # (1-0)*0.3 + 1*0.4 + 1*0.3 = 0.3 + 0.4 + 0.3 = 1.0
        score = compute_composite_risk_score(0.0, 1.0, 1.0, config)
        assert score == 1.0

    def test_medium_risk_scenario(self) -> None:
        """Mid-range inputs produce expected weighted sum."""
        config = _make_config()
        # (1-0.8)*0.3 + 0.5*0.4 + 0.3*0.3 = 0.06 + 0.2 + 0.09 = 0.35
        score = compute_composite_risk_score(0.8, 0.5, 0.3, config)
        assert abs(score - 0.35) < 1e-10

    def test_output_clamped_to_zero(self) -> None:
        """Score cannot go below 0.0 even with unusual weights."""
        config = _make_config(identity_weight=0.0, sanctions_weight=0.0, network_weight=0.0)
        score = compute_composite_risk_score(0.5, 0.5, 0.5, config)
        assert score == 0.0

    def test_output_clamped_to_one(self) -> None:
        """Score is clamped to 1.0 maximum."""
        # Weights summing to > 1.0 could exceed 1.0 unclamped
        config = _make_config(identity_weight=0.5, sanctions_weight=0.5, network_weight=0.5)
        score = compute_composite_risk_score(0.0, 1.0, 1.0, config)
        # (1-0)*0.5 + 1*0.5 + 1*0.5 = 0.5 + 0.5 + 0.5 = 1.5 → clamped to 1.0
        assert score == 1.0


class TestHasCriticalFlag:
    """Tests for has_critical_flag function."""

    def test_no_critical_flags(self) -> None:
        """No flags present returns False."""
        state = _make_state()
        assert has_critical_flag(state) is False

    def test_confirmed_sanctions_match(self) -> None:
        """Confirmed sanctions match triggers critical flag."""
        state = _make_state(has_confirmed_match=True)
        assert has_critical_flag(state) is True

    def test_confirmed_fraud_ring(self) -> None:
        """Confirmed fraud ring triggers critical flag."""
        state = _make_state(has_confirmed_fraud_ring=True)
        assert has_critical_flag(state) is True

    def test_both_critical_flags(self) -> None:
        """Both flags present still returns True."""
        state = _make_state(has_confirmed_match=True, has_confirmed_fraud_ring=True)
        assert has_critical_flag(state) is True

    def test_none_results_returns_false(self) -> None:
        """When agent results are None, no critical flag is detected."""
        state = KYCState(evaluation_id="test-eval-002")
        assert has_critical_flag(state) is False


class TestEvaluateDecision:
    """Tests for evaluate_decision function."""

    def test_critical_flag_overrides_score(self) -> None:
        """Critical flag forces DENY regardless of low score."""
        state = _make_state(
            confidence_score=1.0,
            match_score=0.0,
            network_risk_score=0.0,
            has_confirmed_match=True,
        )
        config = _make_config()
        assert evaluate_decision(state, config) == Decision.DENY

    def test_low_score_approves(self) -> None:
        """Score below approval threshold results in APPROVE."""
        state = _make_state(confidence_score=0.95, match_score=0.0, network_risk_score=0.0)
        config = _make_config(approval_threshold=0.3)
        # Score = (1-0.95)*0.3 + 0*0.4 + 0*0.3 = 0.015 < 0.3 → APPROVE
        assert evaluate_decision(state, config) == Decision.APPROVE

    def test_high_score_denies(self) -> None:
        """Score above denial threshold results in DENY."""
        state = _make_state(confidence_score=0.1, match_score=0.9, network_risk_score=0.8)
        config = _make_config(denial_threshold=0.7)
        # Score = (1-0.1)*0.3 + 0.9*0.4 + 0.8*0.3 = 0.27 + 0.36 + 0.24 = 0.87 > 0.7 → DENY
        assert evaluate_decision(state, config) == Decision.DENY

    def test_ambiguous_score_escalates(self) -> None:
        """Score between thresholds results in ESCALATE_TO_HUMAN_REVIEW."""
        state = _make_state(confidence_score=0.5, match_score=0.5, network_risk_score=0.5)
        config = _make_config(approval_threshold=0.3, denial_threshold=0.7)
        # Score = (1-0.5)*0.3 + 0.5*0.4 + 0.5*0.3 = 0.15 + 0.2 + 0.15 = 0.5
        # 0.3 <= 0.5 <= 0.7 → ESCALATE
        assert evaluate_decision(state, config) == Decision.ESCALATE_TO_HUMAN_REVIEW

    def test_score_exactly_at_approval_threshold_escalates(self) -> None:
        """Score exactly at approval threshold does NOT approve (< is strict)."""
        # Need score == 0.3 exactly
        # (1 - identity) * 0.3 + sanctions * 0.4 + network * 0.3 = 0.3
        # Let identity=0.0, sanctions=0.0, network=0.0 → (1-0)*0.3 = 0.3
        state = _make_state(confidence_score=0.0, match_score=0.0, network_risk_score=0.0)
        config = _make_config(approval_threshold=0.3)
        # Score = 0.3, not < 0.3, so escalate
        assert evaluate_decision(state, config) == Decision.ESCALATE_TO_HUMAN_REVIEW

    def test_score_exactly_at_denial_threshold_escalates(self) -> None:
        """Score exactly at denial threshold does NOT deny (> is strict)."""
        # Need score == 0.7 exactly
        # Use custom config/inputs to achieve this
        config = _make_config(
            identity_weight=0.0,
            sanctions_weight=1.0,
            network_weight=0.0,
            denial_threshold=0.7,
        )
        state = _make_state(confidence_score=1.0, match_score=0.7, network_risk_score=0.0)
        # Score = 0*0 + 0.7*1.0 + 0*0 = 0.7, not > 0.7, so escalate
        assert evaluate_decision(state, config) == Decision.ESCALATE_TO_HUMAN_REVIEW

    def test_missing_agent_results_raises_value_error(self) -> None:
        """Raises ValueError when required agent results are missing."""
        state = KYCState(evaluation_id="test-eval-003")
        config = _make_config()
        with pytest.raises(ValueError, match="Cannot evaluate decision"):
            evaluate_decision(state, config)
