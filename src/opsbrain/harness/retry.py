"""Retry, fallback, and circuit-breaker logic for LLM provider calls.

Wraps provider calls with exponential backoff, automatic fallback to
alternative providers, and circuit-breaker protection against repeated
failures.
"""

from __future__ import annotations

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any, TypeVar

import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from opsbrain.core.exceptions import (
    ProviderRateLimitError,
    ProviderTimeoutError,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Retry decorator
# ---------------------------------------------------------------------------

def with_retries(
    max_attempts: int = 3,
    min_wait: float = 1.0,
    max_wait: float = 30.0,
) -> Callable:
    """Return a tenacity retry decorator for LLM provider calls.

    Retries on rate-limit and timeout errors with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts (including the first).
        min_wait: Minimum wait time in seconds between retries.
        max_wait: Maximum wait time in seconds between retries.

    Returns:
        A retry decorator.
    """
    return retry(
        retry=retry_if_exception_type((ProviderRateLimitError, ProviderTimeoutError)),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(min=min_wait, max=max_wait),
        before_sleep=_log_retry,
        reraise=True,
    )


def _log_retry(retry_state: Any) -> None:
    """Log each retry attempt."""
    logger.warning(
        "retry.attempt",
        attempt=retry_state.attempt_number,
        wait=f"{retry_state.next_action.sleep:.1f}s",  # type: ignore[union-attr]
        error=str(retry_state.outcome.exception()) if retry_state.outcome else "",
    )


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

class CircuitBreaker:
    """Simple circuit breaker that trips after repeated failures.

    States:
        CLOSED  → requests flow normally
        OPEN    → requests are immediately rejected
        HALF_OPEN → a single probe request is allowed through

    Args:
        failure_threshold: Number of consecutive failures before opening.
        recovery_timeout: Seconds to wait before transitioning to half-open.
        name: Human-readable name for logging.
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        name: str = "",
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0

    @property
    def state(self) -> str:
        """Current circuit state, considering recovery timeout."""
        if self._state == self.OPEN:
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                self._state = self.HALF_OPEN
        return self._state

    def allow_request(self) -> bool:
        """Return ``True`` if a request should be allowed through."""
        s = self.state
        if s == self.CLOSED:
            return True
        if s == self.HALF_OPEN:
            return True  # allow one probe
        return False

    def record_success(self) -> None:
        """Record a successful request, resetting the breaker."""
        self._failure_count = 0
        self._state = self.CLOSED

    def record_failure(self) -> None:
        """Record a failed request. Opens the circuit after threshold."""
        self._failure_count += 1
        self._last_failure_time = time.monotonic()
        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            logger.warning(
                "circuit_breaker.opened",
                name=self.name,
                failures=self._failure_count,
            )


# Global registry of per-provider circuit breakers
_breakers: dict[str, CircuitBreaker] = defaultdict(
    lambda: CircuitBreaker(name="default")
)


def get_circuit_breaker(provider: str) -> CircuitBreaker:
    """Get or create a circuit breaker for *provider*."""
    if provider not in _breakers:
        _breakers[provider] = CircuitBreaker(name=provider)
    return _breakers[provider]
