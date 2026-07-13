"""Shared Hypothesis strategies for property-based testing.

Provides reusable strategies for generating valid instances of
all domain Pydantic models used across the test suite.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from hypothesis import strategies as st
from hypothesis.strategies import composite

from src.domain.schemas.config import DecisionConfig
from src.domain.schemas.graph_analysis import (
    FraudPath,
    GraphAnalysisResult,
    GraphEdge,
    GraphNode,
)
from src.domain.schemas.identity import (
    CustomerOnboardingPayload,
    FieldValidation,
    IdentityVerificationResult,
    RegistryCheck,
)
from src.domain.schemas.sanctions import (
    SanctionsScreeningResult,
    WatchlistEntry,
    WatchlistMatch,
)


@composite
def risk_scores(draw: st.DrawFn) -> float:
    """Generate valid risk scores in [0.0, 1.0]."""
    return draw(
        st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )


@composite
def decision_configs(draw: st.DrawFn) -> DecisionConfig:
    """Generate valid DecisionConfig with approval < denial."""
    approval = draw(st.floats(min_value=0.0, max_value=0.49, allow_nan=False, allow_infinity=False))
    denial = draw(st.floats(min_value=approval + 0.01, max_value=1.0, allow_nan=False, allow_infinity=False))
    w1 = draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False))
    w2 = draw(st.floats(min_value=0.0, max_value=max(0.0, 1.0 - w1), allow_nan=False, allow_infinity=False))
    w3 = max(0.0, 1.0 - w1 - w2)
    return DecisionConfig(
        approval_threshold=approval,
        denial_threshold=denial,
        identity_weight=w1,
        sanctions_weight=w2,
        network_weight=w3,
    )


@composite
def customer_payloads(draw: st.DrawFn) -> CustomerOnboardingPayload:
    """Generate valid CustomerOnboardingPayload instances."""
    name = draw(st.text(min_size=2, max_size=50, alphabet=st.characters(categories=("L", "Zs"))))
    # Ensure name has at least 2 non-whitespace chars
    name = name.strip()
    if len(name) < 2:
        name = "John Doe"

    return CustomerOnboardingPayload(
        full_name=name,
        date_of_birth=draw(st.dates(min_value=date(1920, 1, 1), max_value=date(2005, 12, 31))),
        national_id=draw(st.text(min_size=5, max_size=20, alphabet=st.characters(categories=("L", "N")))),
        address=draw(st.text(min_size=10, max_size=100, alphabet=st.characters(categories=("L", "N", "Zs")))),
        email=draw(st.from_regex(r"[a-z]{3,8}@[a-z]{3,6}\.(com|org|net)", fullmatch=True)),
        phone=draw(st.from_regex(r"\+[1-9][0-9]{7,13}", fullmatch=True)),
        ip_address=draw(st.ip_addresses(v=4).map(str)),
    )


@composite
def identity_verification_results(draw: st.DrawFn) -> IdentityVerificationResult:
    """Generate valid IdentityVerificationResult instances."""
    status = draw(st.sampled_from(["verified", "verification_failed", "ambiguous"]))
    return IdentityVerificationResult(
        verification_status=status,
        field_validations=[
            FieldValidation(field_name="email", is_valid=True),
            FieldValidation(field_name="phone", is_valid=True),
        ],
        registry_checks=[
            RegistryCheck(field_name="national_id", registry_status="match"),
        ],
        confidence_score=draw(risk_scores()),
        processing_time_ms=draw(st.integers(min_value=100, max_value=10000)),
    )


@composite
def sanctions_screening_results(draw: st.DrawFn) -> SanctionsScreeningResult:
    """Generate valid SanctionsScreeningResult instances."""
    status = draw(st.sampled_from(["screening_clear", "screening_hit", "screening_ambiguous"]))
    has_match = status == "screening_hit"
    return SanctionsScreeningResult(
        status=status,
        matches=[],
        match_score=draw(risk_scores()),
        has_confirmed_match=has_match,
        sources_screened=["ofac_sdn", "eu_sanctions"],
        processing_time_ms=draw(st.integers(min_value=100, max_value=15000)),
    )


@composite
def graph_analysis_results(draw: st.DrawFn) -> GraphAnalysisResult:
    """Generate valid GraphAnalysisResult instances."""
    status = draw(st.sampled_from(["graph_clear", "fraud_connections_found"]))
    has_ring = status == "fraud_connections_found"
    return GraphAnalysisResult(
        status=status,
        discovered_paths=[],
        network_risk_score=draw(risk_scores()),
        connected_flagged_entities=[],
        has_confirmed_fraud_ring=has_ring and draw(st.booleans()),
        traversal_metadata={"nodes_visited": draw(st.integers(min_value=0, max_value=200))},
        processing_time_ms=draw(st.integers(min_value=100, max_value=20000)),
    )
