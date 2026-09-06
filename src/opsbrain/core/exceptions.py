"""Custom exception hierarchy for OpsBrain."""

from __future__ import annotations


class OpsBrainError(Exception):
    """Base exception for all OpsBrain errors."""

    def __init__(self, message: str = "", *, details: dict | None = None) -> None:
        self.details = details or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# Configuration errors
# ---------------------------------------------------------------------------

class ConfigError(OpsBrainError):
    """Raised when configuration is invalid or missing."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when a configuration file cannot be located."""


# ---------------------------------------------------------------------------
# Provider / Harness errors
# ---------------------------------------------------------------------------

class ProviderError(OpsBrainError):
    """Base class for LLM provider errors."""

    def __init__(
        self,
        message: str = "",
        *,
        provider: str = "",
        model: str = "",
        details: dict | None = None,
    ) -> None:
        self.provider = provider
        self.model = model
        super().__init__(message, details=details)


class ProviderNotFoundError(ProviderError):
    """Raised when a requested provider is not registered or available."""


class ProviderAuthError(ProviderError):
    """Raised when authentication with a provider fails (bad/missing API key)."""


class ProviderRateLimitError(ProviderError):
    """Raised when a provider returns a rate-limit / quota-exceeded response."""


class ProviderTimeoutError(ProviderError):
    """Raised when a provider request times out."""


class ModelNotFoundError(ProviderError):
    """Raised when the requested model is not available from the provider."""


class CostLimitExceededError(ProviderError):
    """Raised when a request would exceed configured cost limits."""


class GuardrailError(ProviderError):
    """Raised when content violates safety or PII guardrails."""


# ---------------------------------------------------------------------------
# Agent errors
# ---------------------------------------------------------------------------

class AgentError(OpsBrainError):
    """Base class for agent execution errors."""

    def __init__(
        self,
        message: str = "",
        *,
        agent_name: str = "",
        details: dict | None = None,
    ) -> None:
        self.agent_name = agent_name
        super().__init__(message, details=details)


class AgentToolError(AgentError):
    """Raised when an agent's tool call fails."""


class AgentTimeoutError(AgentError):
    """Raised when an agent exceeds its time budget."""


# ---------------------------------------------------------------------------
# Connector errors
# ---------------------------------------------------------------------------

class ConnectorError(OpsBrainError):
    """Base class for data connector errors."""

    def __init__(
        self,
        message: str = "",
        *,
        connector: str = "",
        details: dict | None = None,
    ) -> None:
        self.connector = connector
        super().__init__(message, details=details)


class ConnectorAuthError(ConnectorError):
    """Raised when a data connector cannot authenticate."""


class ConnectorTimeoutError(ConnectorError):
    """Raised when a data connector request times out."""


# ---------------------------------------------------------------------------
# Orchestrator errors
# ---------------------------------------------------------------------------

class OrchestratorError(OpsBrainError):
    """Raised for pipeline or orchestration failures."""


class PipelineNotFoundError(OrchestratorError):
    """Raised when a requested pipeline definition cannot be found."""
