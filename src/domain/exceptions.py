"""Domain exception hierarchy for KYC Pipeline.

All domain-specific exceptions inherit from KYCEvaluationError,
providing structured error context including evaluation_id and
correlation_id for distributed tracing.
"""

from __future__ import annotations


class KYCEvaluationError(Exception):
    """Base exception for all KYC pipeline errors.

    Args:
        message: Human-readable error description.
        evaluation_id: Associated evaluation identifier.
        correlation_id: Request correlation identifier for tracing.
    """

    def __init__(
        self,
        message: str,
        evaluation_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        """Initialize KYC evaluation error."""
        self.evaluation_id = evaluation_id
        self.correlation_id = correlation_id
        super().__init__(message)


class AgentTimeoutError(KYCEvaluationError):
    """Agent did not respond within the configured timeout.

    Args:
        agent_name: Name of the agent that timed out.
        timeout_seconds: The timeout threshold that was exceeded.
    """

    def __init__(
        self,
        agent_name: str,
        timeout_seconds: int,
        **kwargs: object,
    ) -> None:
        """Initialize agent timeout error."""
        self.agent_name = agent_name
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Agent '{agent_name}' timed out after {timeout_seconds}s",
            **kwargs,  # type: ignore[arg-type]
        )


class GraphConnectionError(KYCEvaluationError):
    """Neo4j/Neptune graph database connectivity failure.

    Raised when the graph database is unreachable after retry attempts.
    """


class LLMConnectionError(KYCEvaluationError):
    """LLM provider unreachable after retry attempts.

    Raised when Bedrock, OpenAI, or other LLM providers cannot be reached.
    """


class SecurityViolationError(KYCEvaluationError):
    """Security constraint violated.

    Raised on prompt injection detection, tool scope violations,
    or other security policy breaches.

    Args:
        violation_type: Category of the security violation.
    """

    def __init__(
        self,
        message: str,
        violation_type: str = "unknown",
        **kwargs: object,
    ) -> None:
        """Initialize security violation error."""
        self.violation_type = violation_type
        super().__init__(message, **kwargs)  # type: ignore[arg-type]


class SchemaValidationError(KYCEvaluationError):
    """Pydantic validation failure at a system boundary.

    Raised when data crossing a boundary (API, agent-to-agent,
    database read) fails Pydantic schema validation.

    Args:
        field_errors: List of field-level validation error details.
    """

    def __init__(
        self,
        message: str,
        field_errors: list[dict[str, str]] | None = None,
        **kwargs: object,
    ) -> None:
        """Initialize schema validation error."""
        self.field_errors = field_errors or []
        super().__init__(message, **kwargs)  # type: ignore[arg-type]


class CircuitBreakerOpenError(KYCEvaluationError):
    """Circuit breaker is open for an external service.

    Raised when a service call is rejected because the circuit breaker
    is in the OPEN state due to consecutive failures.

    Args:
        service_name: Name of the affected external service.
    """

    def __init__(
        self,
        service_name: str,
        **kwargs: object,
    ) -> None:
        """Initialize circuit breaker open error."""
        self.service_name = service_name
        super().__init__(
            f"Circuit breaker open for service '{service_name}'",
            **kwargs,  # type: ignore[arg-type]
        )


class TokenBudgetExceededError(KYCEvaluationError):
    """Token budget for an evaluation has been exceeded.

    Raised when cumulative LLM token usage exceeds the configured
    per-evaluation budget limit.

    Args:
        budget_limit: Configured token budget.
        tokens_used: Actual tokens consumed.
    """

    def __init__(
        self,
        budget_limit: int,
        tokens_used: int,
        **kwargs: object,
    ) -> None:
        """Initialize token budget exceeded error."""
        self.budget_limit = budget_limit
        self.tokens_used = tokens_used
        super().__init__(
            f"Token budget exceeded: {tokens_used}/{budget_limit} tokens used",
            **kwargs,  # type: ignore[arg-type]
        )
