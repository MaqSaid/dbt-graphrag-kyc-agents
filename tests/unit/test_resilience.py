"""Unit tests for infrastructure resilience patterns.

Tests circuit breaker state transitions and retry with exponential backoff.
"""

import asyncio
import time
from unittest.mock import patch

import pytest

from src.infrastructure.resilience.circuit_breaker import CircuitBreaker, CircuitState
from src.infrastructure.resilience.retry import retry_with_backoff


class TestCircuitBreaker:
    """Tests for CircuitBreaker class."""

    def test_initial_state_is_closed(self) -> None:
        """Circuit breaker starts in CLOSED state."""
        breaker = CircuitBreaker()
        assert breaker.state == CircuitState.CLOSED

    def test_default_parameters(self) -> None:
        """Default constructor parameters match specification."""
        breaker = CircuitBreaker()
        assert breaker.failure_threshold == 5
        assert breaker.recovery_timeout_seconds == 60
        assert breaker.service_name == "unknown"

    def test_custom_parameters(self) -> None:
        """Custom constructor parameters are stored correctly."""
        breaker = CircuitBreaker(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            service_name="neo4j",
        )
        assert breaker.failure_threshold == 3
        assert breaker.recovery_timeout_seconds == 30
        assert breaker.service_name == "neo4j"

    def test_can_execute_when_closed(self) -> None:
        """can_execute returns True when circuit is CLOSED."""
        breaker = CircuitBreaker()
        assert breaker.can_execute() is True

    def test_stays_closed_below_threshold(self) -> None:
        """Circuit remains CLOSED when failures are below threshold."""
        breaker = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED
        assert breaker.can_execute() is True

    def test_opens_at_failure_threshold(self) -> None:
        """Circuit transitions to OPEN when failure threshold is reached."""
        breaker = CircuitBreaker(failure_threshold=5)
        for _ in range(5):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        assert breaker.can_execute() is False

    def test_record_success_resets_to_closed(self) -> None:
        """record_success resets failure count and transitions to CLOSED."""
        breaker = CircuitBreaker(failure_threshold=5)
        for _ in range(4):
            breaker.record_failure()
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED
        # After reset, need full threshold again to open
        for _ in range(4):
            breaker.record_failure()
        assert breaker.state == CircuitState.CLOSED

    def test_record_success_closes_from_half_open(self) -> None:
        """record_success transitions from HALF_OPEN to CLOSED."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout_seconds=0)
        for _ in range(5):
            breaker.record_failure()
        # Recovery timeout is 0, so state transitions to HALF_OPEN immediately
        assert breaker.state == CircuitState.HALF_OPEN
        breaker.record_success()
        assert breaker.state == CircuitState.CLOSED

    def test_transitions_to_half_open_after_recovery_timeout(self) -> None:
        """Circuit transitions from OPEN to HALF_OPEN after recovery timeout."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout_seconds=1)
        for _ in range(5):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN

        # Simulate time passing beyond recovery timeout by manipulating _last_failure_time
        breaker._last_failure_time = time.time() - 2
        assert breaker.state == CircuitState.HALF_OPEN
        assert breaker.can_execute() is True

    def test_half_open_failure_reopens_circuit(self) -> None:
        """Failure in HALF_OPEN state reopens the circuit."""
        breaker = CircuitBreaker(failure_threshold=5, recovery_timeout_seconds=60)
        for _ in range(5):
            breaker.record_failure()
        assert breaker.state == CircuitState.OPEN
        # Simulate recovery timeout elapsed to transition to HALF_OPEN
        breaker._last_failure_time = time.time() - 61
        assert breaker.state == CircuitState.HALF_OPEN
        # Record another failure — count is already at threshold so circuit reopens
        breaker.record_failure()
        # The failure sets _last_failure_time to now, and count is >= threshold → OPEN
        # But state property checks timeout, which hasn't elapsed yet
        assert breaker.state == CircuitState.OPEN

    def test_can_execute_returns_false_when_open(self) -> None:
        """can_execute returns False when circuit is OPEN."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=9999)
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.can_execute() is False

    def test_can_execute_returns_true_when_half_open(self) -> None:
        """can_execute returns True when circuit is HALF_OPEN."""
        breaker = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=0)
        breaker.record_failure()
        breaker.record_failure()
        # 0 timeout means immediate transition to HALF_OPEN
        assert breaker.can_execute() is True


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""

    def test_succeeds_on_first_attempt(self) -> None:
        """Function that succeeds immediately returns without retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay_seconds=0.01)
        def success_fn() -> str:
            nonlocal call_count
            call_count += 1
            return "ok"

        result = success_fn()
        assert result == "ok"
        assert call_count == 1

    def test_retries_on_failure_then_succeeds(self) -> None:
        """Function retries on failure and returns on eventual success."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay_seconds=0.01,
            exceptions=(ValueError,),
        )
        def flaky_fn() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("transient error")
            return "recovered"

        result = flaky_fn()
        assert result == "recovered"
        assert call_count == 3

    def test_raises_after_max_retries_exhausted(self) -> None:
        """Raises the last exception when all retries are exhausted."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay_seconds=0.01,
            exceptions=(ConnectionError,),
        )
        def always_fails() -> str:
            nonlocal call_count
            call_count += 1
            raise ConnectionError(f"attempt {call_count}")

        with pytest.raises(ConnectionError, match="attempt 3"):
            always_fails()
        assert call_count == 3

    def test_only_catches_specified_exceptions(self) -> None:
        """Exceptions not in the exceptions tuple propagate immediately."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay_seconds=0.01,
            exceptions=(ValueError,),
        )
        def raises_type_error() -> str:
            nonlocal call_count
            call_count += 1
            raise TypeError("not retryable")

        with pytest.raises(TypeError, match="not retryable"):
            raises_type_error()
        assert call_count == 1

    def test_exponential_backoff_delays(self) -> None:
        """Verifies exponential backoff timing: delay = base * 2^attempt."""
        delays: list[float] = []

        @retry_with_backoff(
            max_retries=4,
            base_delay_seconds=1.0,
            exceptions=(RuntimeError,),
        )
        def always_fails() -> str:
            raise RuntimeError("fail")

        with patch("src.infrastructure.resilience.retry.time.sleep") as mock_sleep:
            with pytest.raises(RuntimeError):
                always_fails()
            delays = [call.args[0] for call in mock_sleep.call_args_list]

        # Expected delays: 1*2^0=1.0, 1*2^1=2.0, 1*2^2=4.0 (3 delays for 4 attempts)
        assert delays == [1.0, 2.0, 4.0]

    @pytest.mark.asyncio
    async def test_async_succeeds_on_first_attempt(self) -> None:
        """Async function that succeeds immediately returns without retry."""
        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay_seconds=0.01)
        async def async_success() -> str:
            nonlocal call_count
            call_count += 1
            return "async_ok"

        result = await async_success()
        assert result == "async_ok"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_async_retries_on_failure_then_succeeds(self) -> None:
        """Async function retries on failure and returns on eventual success."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay_seconds=0.01,
            exceptions=(IOError,),
        )
        async def flaky_async() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise IOError("transient")
            return "async_recovered"

        result = await flaky_async()
        assert result == "async_recovered"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_async_raises_after_max_retries(self) -> None:
        """Async function raises last exception when retries exhausted."""
        call_count = 0

        @retry_with_backoff(
            max_retries=3,
            base_delay_seconds=0.01,
            exceptions=(TimeoutError,),
        )
        async def always_fails_async() -> str:
            nonlocal call_count
            call_count += 1
            raise TimeoutError(f"async attempt {call_count}")

        with pytest.raises(TimeoutError, match="async attempt 3"):
            await always_fails_async()
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_async_exponential_backoff_delays(self) -> None:
        """Verifies async exponential backoff timing."""
        recorded_delays: list[float] = []
        original_sleep = asyncio.sleep

        async def fake_sleep(delay: float) -> None:
            recorded_delays.append(delay)

        @retry_with_backoff(
            max_retries=3,
            base_delay_seconds=1.0,
            exceptions=(RuntimeError,),
        )
        async def always_fails_async() -> str:
            raise RuntimeError("fail")

        with patch("src.infrastructure.resilience.retry.asyncio.sleep", side_effect=fake_sleep):
            with pytest.raises(RuntimeError):
                await always_fails_async()

        # Expected delays: 1*2^0=1.0, 1*2^1=2.0 (2 delays for 3 attempts)
        assert recorded_delays == [1.0, 2.0]

    def test_preserves_function_metadata(self) -> None:
        """Decorated function retains original name and docstring."""

        @retry_with_backoff()
        def documented_fn() -> None:
            """Original docstring."""

        assert documented_fn.__name__ == "documented_fn"
        assert documented_fn.__doc__ == "Original docstring."

    def test_default_parameters(self) -> None:
        """Default decorator parameters match specification."""
        call_count = 0

        @retry_with_backoff()
        def fails_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("fail")  # noqa: TRY002
            return "done"

        with patch("src.infrastructure.resilience.retry.time.sleep"):
            result = fails_twice()

        assert result == "done"
        assert call_count == 3
