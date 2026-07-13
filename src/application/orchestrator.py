"""LangGraph orchestrator for the KYC evaluation pipeline.

Implements the stateful workflow graph with explicit nodes, conditional
edges, retry logic, timeout handling, and state transition recording.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, StateGraph

from src.domain.orchestration.decision_engine import (
    compute_composite_risk_score,
    evaluate_decision,
    has_critical_flag,
)
from src.domain.schemas.config import DecisionConfig
from src.domain.schemas.kyc_state import Decision, KYCState, StateTransition


def build_kyc_graph(config: DecisionConfig | None = None) -> Any:
    """Build the KYC evaluation LangGraph state machine.

    Creates a compiled StateGraph with nodes for each processing step
    and conditional edges for routing decisions.

    Args:
        config: Decision configuration. Uses defaults if None.

    Returns:
        Compiled LangGraph StateGraph ready for execution.
    """
    if config is None:
        config = DecisionConfig()

    graph = StateGraph(KYCState)

    # Add processing nodes
    graph.add_node("initialize", _initialize_evaluation)
    graph.add_node("verify_identity", _invoke_identity_verifier)
    graph.add_node("screen_sanctions", _invoke_sanctions_analyst)
    graph.add_node("analyze_graph", _invoke_graph_analyst)
    graph.add_node("draft_report", _invoke_report_drafter)
    graph.add_node("evaluate_decision", lambda state: _evaluate_decision_node(state, config))
    graph.add_node("finalize", _finalize_evaluation)

    # Define flow
    graph.set_entry_point("initialize")
    graph.add_edge("initialize", "verify_identity")

    # Conditional: after identity verification
    graph.add_conditional_edges(
        "verify_identity",
        _route_after_identity,
        {
            "proceed": "screen_sanctions",
            "retry": "verify_identity",
            "escalate": "finalize",
        },
    )

    # Conditional: after sanctions screening
    graph.add_conditional_edges(
        "screen_sanctions",
        _route_after_sanctions,
        {
            "proceed": "analyze_graph",
            "retry": "screen_sanctions",
            "escalate": "finalize",
        },
    )

    graph.add_edge("analyze_graph", "draft_report")
    graph.add_edge("draft_report", "evaluate_decision")
    graph.add_edge("evaluate_decision", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


def _record_transition(state: KYCState, from_node: str, to_node: str, condition: str = "") -> KYCState:
    """Record a state transition in the history.

    Args:
        state: Current KYC state.
        from_node: Source node name.
        to_node: Target node name.
        condition: Condition that triggered the transition.

    Returns:
        Updated state with new transition recorded.
    """
    transition = StateTransition(
        from_node=from_node,
        to_node=to_node,
        timestamp=datetime.now(tz=timezone.utc),
        condition_evaluated=condition if condition else None,
        result=to_node,
    )
    state.state_history.append(transition)
    state.updated_at = datetime.now(tz=timezone.utc)
    return state


def _initialize_evaluation(state: KYCState) -> KYCState:
    """Initialize the evaluation state.

    Args:
        state: Incoming KYC state with customer data.

    Returns:
        State with initialization recorded.
    """
    return _record_transition(state, "entry", "initialize")


def _invoke_identity_verifier(state: KYCState) -> KYCState:
    """Invoke the Identity Verifier agent (placeholder for agent invocation).

    Args:
        state: Current KYC state with customer data.

    Returns:
        State with identity verification result (populated by agent runtime).
    """
    return _record_transition(state, "initialize", "verify_identity")


def _invoke_sanctions_analyst(state: KYCState) -> KYCState:
    """Invoke the Sanctions Analyst agent (placeholder for agent invocation).

    Args:
        state: Current KYC state with verified identity.

    Returns:
        State with sanctions screening result (populated by agent runtime).
    """
    return _record_transition(state, "verify_identity", "screen_sanctions")


def _invoke_graph_analyst(state: KYCState) -> KYCState:
    """Invoke the Graph Analyst agent (placeholder for agent invocation).

    Args:
        state: Current KYC state with screening results.

    Returns:
        State with graph analysis result (populated by agent runtime).
    """
    return _record_transition(state, "screen_sanctions", "analyze_graph")


def _invoke_report_drafter(state: KYCState) -> KYCState:
    """Invoke the Report Drafter agent (placeholder for agent invocation).

    Args:
        state: Current KYC state with all agent results.

    Returns:
        State with compliance report (populated by agent runtime).
    """
    return _record_transition(state, "analyze_graph", "draft_report")


def _evaluate_decision_node(state: KYCState, config: DecisionConfig) -> KYCState:
    """Evaluate the final KYC decision based on all agent results.

    Args:
        state: Complete KYC state with all results.
        config: Decision configuration with thresholds.

    Returns:
        State with final decision set.
    """
    decision = evaluate_decision(state, config)
    state.final_decision = decision
    return _record_transition(state, "draft_report", "evaluate_decision", f"decision={decision.value}")


def _finalize_evaluation(state: KYCState) -> KYCState:
    """Finalize the evaluation and record completion.

    Args:
        state: Complete KYC state with decision.

    Returns:
        Finalized state.
    """
    state.updated_at = datetime.now(tz=timezone.utc)
    return _record_transition(state, "evaluate_decision", "finalize")


def _route_after_identity(state: KYCState) -> str:
    """Conditional edge: route based on identity verification outcome.

    Args:
        state: Current KYC state.

    Returns:
        Route key: 'proceed', 'retry', or 'escalate'.
    """
    if state.identity_verification_result is None:
        return "escalate"
    if state.identity_verification_result.verification_status == "verified":
        return "proceed"
    if (
        state.identity_verification_result.verification_status == "ambiguous"
        and state.retry_count_identity < 3
    ):
        state.retry_count_identity += 1
        return "retry"
    return "escalate"


def _route_after_sanctions(state: KYCState) -> str:
    """Conditional edge: route based on sanctions screening outcome.

    Args:
        state: Current KYC state.

    Returns:
        Route key: 'proceed', 'retry', or 'escalate'.
    """
    if state.sanctions_screening_result is None:
        return "escalate"
    if state.sanctions_screening_result.status in ("screening_clear", "screening_hit"):
        return "proceed"
    if (
        state.sanctions_screening_result.status == "screening_ambiguous"
        and state.retry_count_sanctions < 3
    ):
        state.retry_count_sanctions += 1
        return "retry"
    return "escalate"
