"""Report Drafter Strands agent for compliance narrative generation.

Synthesizes findings from Identity, Sanctions, and Graph agents into
a structured, standard-compliant audit narrative with explainability metadata.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from strands import Agent, tool

from src.domain.ports.llm_client_port import LLMClientPort


# Module-level port reference set by factory
_llm_port: LLMClientPort | None = None


@tool
def draft_executive_summary(
    identity_status: str,
    sanctions_status: str,
    graph_status: str,
    risk_score: float,
    decision: str,
) -> dict[str, Any]:
    """Draft the executive summary section of the compliance report.

    Args:
        identity_status: Result of identity verification (verified/failed/ambiguous).
        sanctions_status: Result of sanctions screening (clear/hit/ambiguous).
        graph_status: Result of graph analysis (clear/fraud_connections_found).
        risk_score: Composite risk score (0.0 to 1.0).
        decision: Final decision (APPROVE/DENY/ESCALATE_TO_HUMAN_REVIEW).

    Returns:
        Dictionary with executive summary text and source references.
    """
    summary_parts = [
        f"KYC Evaluation Summary - Decision: {decision}",
        f"Identity Verification: {identity_status}",
        f"Sanctions Screening: {sanctions_status}",
        f"Network Analysis: {graph_status}",
        f"Composite Risk Score: {risk_score:.2f}",
    ]

    if decision == "DENY":
        summary_parts.append("RECOMMENDATION: Application should be DENIED based on risk indicators.")
    elif decision == "ESCALATE_TO_HUMAN_REVIEW":
        summary_parts.append("RECOMMENDATION: Manual review required due to ambiguous signals.")
    else:
        summary_parts.append("RECOMMENDATION: Application may proceed pending standard controls.")

    return {
        "content": "\n".join(summary_parts),
        "source_references": ["identity_verification_result", "sanctions_screening_result", "graph_analysis_result"],
    }


@tool
def draft_risk_assessment(
    composite_score: float,
    identity_confidence: float,
    sanctions_match_score: float,
    network_risk_score: float,
    contributing_factors: list[str],
) -> dict[str, Any]:
    """Draft the risk assessment section with factor breakdown.

    Args:
        composite_score: Overall composite risk score.
        identity_confidence: Identity verification confidence.
        sanctions_match_score: Highest sanctions match score.
        network_risk_score: Network analysis risk score.
        contributing_factors: List of contributing risk factors.

    Returns:
        Dictionary with risk assessment narrative and references.
    """
    assessment_parts = [
        f"Risk Assessment - Composite Score: {composite_score:.4f}",
        "",
        "Score Breakdown:",
        f"  - Identity Confidence: {identity_confidence:.2f} (inverted risk: {1.0 - identity_confidence:.2f})",
        f"  - Sanctions Match Score: {sanctions_match_score:.2f}",
        f"  - Network Risk Score: {network_risk_score:.2f}",
        "",
        "Contributing Factors:",
    ]

    for factor in contributing_factors:
        assessment_parts.append(f"  - {factor}")

    return {
        "content": "\n".join(assessment_parts),
        "source_references": ["decision_engine", "graph_analysis_result", "sanctions_screening_result"],
    }


@tool
def format_compliance_report(
    evaluation_id: str,
    executive_summary: str,
    identity_findings: str,
    sanctions_findings: str,
    network_findings: str,
    risk_assessment: str,
    recommended_action: str,
    escalation_reasons: list[str] | None = None,
) -> dict[str, Any]:
    """Assemble all sections into the final ComplianceReport structure.

    Args:
        evaluation_id: The evaluation identifier.
        executive_summary: Executive summary section content.
        identity_findings: Identity verification findings content.
        sanctions_findings: Sanctions screening findings content.
        network_findings: Network analysis findings content.
        risk_assessment: Risk assessment section content.
        recommended_action: Recommended action text.
        escalation_reasons: Optional list of reasons for human escalation.

    Returns:
        Dictionary with the complete structured report.
    """
    import uuid

    report = {
        "report_id": str(uuid.uuid4()),
        "evaluation_id": evaluation_id,
        "generation_timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "pipeline_version": "1.0.0",
        "sections": {
            "executive_summary": executive_summary,
            "identity_findings": identity_findings,
            "sanctions_findings": sanctions_findings,
            "network_findings": network_findings,
            "risk_assessment": risk_assessment,
        },
        "recommended_action": recommended_action,
        "escalation_ambiguities": escalation_reasons or [],
    }

    return report


@tool
def generate_trace_mapping(
    report_section: str,
    source_data_ids: list[str],
    prompt_template: str,
) -> dict[str, Any]:
    """Generate explainability trace from report assertions to source data.

    Creates an ISO 42001 compliant trace mapping that links each
    assertion in the generated text to its source data nodes.

    Args:
        report_section: The report section text to trace.
        source_data_ids: List of Neo4j node IDs or data source references.
        prompt_template: The prompt template used for generation.

    Returns:
        Dictionary with trace mapping and explainability metadata.
    """
    prompt_hash = hashlib.sha256(prompt_template.encode()).hexdigest()

    # Create assertion-to-source mapping
    trace_mapping: dict[str, list[str]] = {}
    sentences = [s.strip() for s in report_section.split(".") if s.strip()]
    for sentence in sentences:
        # Map each assertion to all provided source data
        trace_mapping[sentence[:100]] = source_data_ids

    return {
        "prompt_template_hash": prompt_hash,
        "trace_mapping": trace_mapping,
        "source_count": len(source_data_ids),
        "assertion_count": len(trace_mapping),
        "invocation_timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


SYSTEM_PROMPT = """You are a specialized Compliance Report Drafter agent.

Your sole responsibility is to synthesize all investigation findings from the
Identity Verifier, Sanctions Analyst, and Graph Analyst into a polished,
standard-compliant audit narrative.

Your tools allow you to:
1. Draft the executive summary from all agent outcomes
2. Draft the risk assessment with factor breakdown
3. Format the complete compliance report structure
4. Generate explainability trace mappings (ISO 42001)

Workflow:
- Review all provided agent results (identity, sanctions, graph analysis)
- Draft the executive summary capturing the overall outcome
- Draft the risk assessment with score breakdown and contributing factors
- Assemble all sections into the final structured report
- Generate trace mappings for regulatory explainability

The report must:
- Include direct references to source data for every assertion
- Contain an explainability metadata section
- List specific ambiguities if decision is ESCALATE_TO_HUMAN_REVIEW
- Be formatted for regulatory examination readiness
"""


def create_report_drafter_agent(
    llm_port: LLMClientPort,
) -> Agent:
    """Factory function creating the Report_Drafter Strands agent.

    Args:
        llm_port: Port for LLM interactions.

    Returns:
        Configured Strands Agent for compliance report drafting.
    """
    global _llm_port  # noqa: PLW0603
    _llm_port = llm_port

    return Agent(
        system_prompt=SYSTEM_PROMPT,
        tools=[
            draft_executive_summary,
            draft_risk_assessment,
            format_compliance_report,
            generate_trace_mapping,
        ],
        max_iterations=10,
    )
