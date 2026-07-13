"""Retry logic with exponential backoff for external service calls.

Provides a decorator and utility for retrying failed operations
with configurable backoff, max attempts, and exception filtering.
"""

from __future__ import annotations

import asyncio
import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class RetryConfig:
    """Configuration for retry behavior.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay_seconds: Initial delay before first retry.
        max_delay_seconds: Maximum delay between retries.
        exponential_base: Multiplier for exponential backoff.
        retryable_exceptions: Tuple of exception types that trigger retry.
    """

    def __init__(
        self,
        max_retries: int = 3,
        base_delay_seconds: float = 2.0,
        max_delay_seconds: float = 30.0,
        exponential_base: float = 2.0,
        retryable_exceptions: tuple[type[Exception], ...] = (Exception,),
    ) -> None:
        """Initialize retry configuration."""
        self.max_retries = max_retries
        self.base_delay_seconds = base_delay_seconds
        self.max_delay_seconds = max_delay_seconds
        self.exponential_base = exponential_base
        self.retryable_exceptions = retryable_exceptions


def compute_backoff_delay(
    attempt: int,
    base_delay: float,
    max_delay: float,
    exponential_base: float = 2.0,
) -> float:
    """Compute exponential backoff delay for a given attempt.

    Args:
        attempt: Current attempt number (0-indexed).
        base_delay: Base delay in seconds.
        max_delay: Maximum delay cap.
        exponential_base: Exponential growth factor.

    Returns:
        Delay in seconds (capped at max_delay).
    """
    delay = base_delay * (exponential_base**attempt)
    return min(delay, max_delay)


def with_retry(config: RetryConfig | None = None) -> Callable[[F], F]:
    """Decorator for async functions with exponential backoff retry.

    Args:
        config: Retry configuration. Uses defaults if None.

    Returns:
        Decorated function with retry behavior.
    """
    if config is None:
        config = RetryConfig()

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(config.max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as exc:
                    last_exception = exc
                    if attempt < config.max_retries:
                        delay = compute_backoff_delay(
                            attempt,
                            config.base_delay_seconds,
                            config.max_delay_seconds,
                            config.exponential_base,
                        )
                        logger.warning(
                            "Retry attempt %d/%d for %s after %.1fs: %s",
                            attempt + 1,
                            config.max_retries,
                            func.__name__,
                            delay,
                            str(exc),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All %d retries exhausted for %s: %s",
                            config.max_retries,
                            func.__name__,
                            str(exc),
                        )
            raise last_exception  # type: ignore[misc]

        return wrapper  # type: ignore[return-value]

    return decorator


def retry_with_backoff(
    max_retries: int = 3,
    base_delay_seconds: float = 2.0,
    max_delay_seconds: float = 30.0,
    exponential_base: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """Decorator for functions with exponential backoff retry.

    Supports both sync and async functions. Retries on specified
    exception types with configurable exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts.
        base_delay_seconds: Initial delay before first retry.
        max_delay_seconds: Maximum delay cap between retries.
        exponential_base: Growth factor for backoff.
        exceptions: Tuple of exception types that trigger retry.

    Returns:
        Decorated function with retry behavior.
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        delay = compute_backoff_delay(
                            attempt, base_delay_seconds, max_delay_seconds, exponential_base
                        )
                        logger.warning(
                            "Retry attempt %d/%d for %s after %.1fs: %s",
                            attempt + 1,
                            max_retries,
                            func.__name__,
                            delay,
                            str(exc),
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            "All %d retries exhausted for %s: %s",
                            max_retries,
                            func.__name__,
                            str(exc),
                        )
            raise last_exception  # type: ignore[misc]

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            import time as _time

            last_exception: Exception | None = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last_exception = exc
                    if attempt < max_retries:
                        delay = compute_backoff_delay(
                            attempt, base_delay_seconds, max_delay_seconds, exponential_base
                        )
                        logger.warning(
                            "Retry attempt %d/%d for %s after %.1fs: %s",
                            attempt + 1,
                            max_retries,
                            func.__name__,
                            delay,
                            str(exc),
                        )
                        _time.sleep(delay)
                    else:
                        logger.error(
                            "All %d retries exhausted for %s: %s",
                            max_retries,
                            func.__name__,
                            str(exc),
                        )
            raise last_exception  # type: ignore[misc]

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


async def retry_async(
    func: Callable[..., Any],
    *args: Any,
    config: RetryConfig | None = None,
    **kwargs: Any,
) -> Any:
    """Execute an async function with retry logic.

    Utility function for cases where the decorator pattern doesn't fit.

    Args:
        func: Async function to execute.
        *args: Positional arguments for the function.
        config: Retry configuration.
        **kwargs: Keyword arguments for the function.

    Returns:
        Result of the successful function call.

    Raises:
        The last exception if all retries are exhausted.
    """
    if config is None:
        config = RetryConfig()

    last_exception: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except config.retryable_exceptions as exc:
            last_exception = exc
            if attempt < config.max_retries:
                delay = compute_backoff_delay(
                    attempt,
                    config.base_delay_seconds,
                    config.max_delay_seconds,
                    config.exponential_base,
                )
                await asyncio.sleep(delay)
    raise last_exception  # type: ignore[misc]
