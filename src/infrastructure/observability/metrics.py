"""Prometheus metrics for KYC pipeline observability.

Defines counters, histograms, and gauges for tracking
evaluation throughput, latency, and error rates.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

# Evaluation metrics
evaluation_count = Counter(
    "kyc_evaluation_count_total",
    "Total KYC evaluations processed",
    ["decision"],
)

evaluation_duration = Histogram(
    "kyc_evaluation_duration_seconds",
    "KYC evaluation end-to-end latency",
    buckets=[10, 30, 60, 90, 120, 180, 300],
)

active_evaluations = Gauge(
    "kyc_active_evaluations",
    "Number of currently in-progress evaluations",
)

# Agent metrics
agent_invocation_duration = Histogram(
    "kyc_agent_invocation_duration_seconds",
    "Agent invocation latency by agent name",
    ["agent_name"],
    buckets=[1, 5, 10, 15, 20, 30, 60],
)

agent_invocation_count = Counter(
    "kyc_agent_invocation_count_total",
    "Total agent invocations by agent and status",
    ["agent_name", "status"],
)

# External service metrics
external_call_latency = Histogram(
    "kyc_external_call_latency_seconds",
    "External service call latency",
    ["service_name", "operation"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30],
)

external_call_count = Counter(
    "kyc_external_call_count_total",
    "Total external service calls by service and status",
    ["service_name", "operation", "status"],
)

# Error metrics
error_count = Counter(
    "kyc_error_count_total",
    "Total errors by error type",
    ["error_type"],
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    "kyc_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half_open)",
    ["service_name"],
)

# Token/cost metrics
token_usage = Counter(
    "kyc_token_usage_total",
    "Total LLM tokens consumed",
    ["model_identifier", "direction"],
)

evaluation_cost = Histogram(
    "kyc_evaluation_estimated_cost_usd",
    "Estimated cost per evaluation in USD",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0],
)
