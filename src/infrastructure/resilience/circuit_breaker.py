"""Circuit breaker pattern for external service calls.

Implements the standard circuit breaker state machine (CLOSED → OPEN → HALF_OPEN)
to prevent cascading failures when external services become unavailable.
"""

from __future__ import annotations

import time
from enum import Enum


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Opens after consecutive failures, rejects calls while open,
    and attempts recovery after a timeout period.

    Args:
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout_seconds: Seconds to wait before attempting recovery.
        service_name: Name of the protected service (for logging).
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        service_name: str = "unknown",
    ) -> None:
        """Initialize circuit breaker."""
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.service_name = service_name
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._success_count_half_open = 0

    @property
    def state(self) -> CircuitState:
        """Get current circuit state, transitioning from OPEN to HALF_OPEN if timeout elapsed."""
        if self._state == CircuitState.OPEN:
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    @property
    def failure_count(self) -> int:
        """Get current consecutive failure count."""
        return self._failure_count

    def can_execute(self) -> bool:
        """Check if a call is allowed through the circuit.

        Returns:
            True if the circuit is CLOSED or HALF_OPEN (allowing a test call).
        """
        return self.state != CircuitState.OPEN

    def record_success(self) -> None:
        """Record a successful call, resetting the circuit to CLOSED."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._success_count_half_open = 0

    def record_failure(self) -> None:
        """Record a failed call, potentially opening the circuit."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state."""
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        self._last_failure_time = 0.0
        self._success_count_half_open = 0
