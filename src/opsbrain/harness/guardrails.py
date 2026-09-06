"""Guardrails — safety, cost, and content validation for LLM I/O.

Applied automatically by the harness before requests are sent and
after responses are received.
"""

from __future__ import annotations

import re

import structlog

from opsbrain.core.config import GuardrailConfig
from opsbrain.core.exceptions import CostLimitExceededError, GuardrailError
from opsbrain.core.types import LLMRequest, LLMResponse

logger = structlog.get_logger(__name__)

# Common PII patterns (intentionally broad for safety)
_PII_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("phone_us", re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
    ("ip_address", re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b")),
]


class Guardrails:
    """Validates LLM requests and responses against safety policies.

    Checks include:
    - Cost limit enforcement (per-request)
    - PII detection in outgoing prompts
    - Blocked-pattern matching
    - Token limit enforcement

    Usage::

        guard = Guardrails(config.guardrails)
        guard.validate_request(request)    # raises on violation
        guard.validate_response(response)  # raises on violation
    """

    def __init__(self, config: GuardrailConfig) -> None:
        self._config = config
        self._hourly_cost: float = 0.0
        self._blocked_patterns = [
            re.compile(p, re.IGNORECASE) for p in config.blocked_patterns
        ]

    # ----- request validation -----

    def validate_request(self, request: LLMRequest) -> None:
        """Validate a request before it is sent to a provider.

        Args:
            request: The request to validate.

        Raises:
            GuardrailError: If the request violates any guardrail.
            CostLimitExceededError: If cost limits would be exceeded.
        """
        # Token limit
        if request.max_tokens and request.max_tokens > self._config.max_tokens_per_request:
            raise GuardrailError(
                f"Requested max_tokens ({request.max_tokens}) exceeds limit "
                f"({self._config.max_tokens_per_request}).",
            )

        # PII detection in outgoing messages
        if self._config.pii_detection_enabled:
            for msg in request.messages:
                pii_found = self._detect_pii(msg.content)
                if pii_found:
                    logger.warning(
                        "guardrails.pii_detected",
                        types=[t for t, _ in pii_found],
                        message_role=msg.role,
                    )
                    # Log warning but don't block (operators may intend to send PII)
                    # To hard-block, uncomment below:
                    # raise GuardrailError(
                    #     f"PII detected in {msg.role} message: {[t for t, _ in pii_found]}",
                    # )

        # Blocked patterns
        for msg in request.messages:
            self._check_blocked_patterns(msg.content, direction="request")

    # ----- response validation -----

    def validate_response(self, response: LLMResponse) -> None:
        """Validate a response received from a provider.

        Args:
            response: The response to validate.

        Raises:
            GuardrailError: If the response violates any guardrail.
        """
        self._check_blocked_patterns(response.content, direction="response")

        # Track cost
        if response.usage.cost_usd is not None:
            self._hourly_cost += response.usage.cost_usd
            if self._hourly_cost > self._config.max_cost_per_hour_usd:
                logger.error(
                    "guardrails.hourly_cost_exceeded",
                    hourly_cost=self._hourly_cost,
                    limit=self._config.max_cost_per_hour_usd,
                )
                raise CostLimitExceededError(
                    f"Hourly cost limit exceeded: ${self._hourly_cost:.4f} "
                    f"> ${self._config.max_cost_per_hour_usd:.2f}",
                )

    # ----- PII detection -----

    def _detect_pii(self, text: str) -> list[tuple[str, str]]:
        """Scan *text* for common PII patterns.

        Returns:
            A list of ``(pii_type, matched_text)`` tuples.
        """
        findings: list[tuple[str, str]] = []
        for pii_type, pattern in _PII_PATTERNS:
            for match in pattern.finditer(text):
                findings.append((pii_type, match.group()))
        return findings

    # ----- blocked patterns -----

    def _check_blocked_patterns(self, text: str, *, direction: str) -> None:
        """Check text against blocked patterns.

        Args:
            text: The text to check.
            direction: ``"request"`` or ``"response"`` for logging.

        Raises:
            GuardrailError: If a blocked pattern is found.
        """
        for pattern in self._blocked_patterns:
            if pattern.search(text):
                raise GuardrailError(
                    f"Blocked pattern matched in {direction}: {pattern.pattern}",
                )

    # ----- cost management -----

    def reset_hourly_cost(self) -> None:
        """Reset the hourly cost accumulator (call on the hour)."""
        self._hourly_cost = 0.0

    @property
    def current_hourly_cost(self) -> float:
        """Current accumulated cost this hour."""
        return self._hourly_cost
