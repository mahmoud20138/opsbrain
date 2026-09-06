"""Configuration management for OpsBrain.

Loads settings from YAML files, environment variables, and CLI arguments
with a layered priority: CLI > env vars > config file > defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from opsbrain.core.exceptions import ConfigError, ConfigFileNotFoundError
from opsbrain.core.types import Provider, Severity

# ---------------------------------------------------------------------------
# Provider configuration
# ---------------------------------------------------------------------------

class ProviderConfig(BaseModel):
    """Configuration for a single LLM provider."""

    enabled: bool = True
    api_key: str = ""
    api_base: str = ""
    default_model: str = ""
    max_retries: int = 3
    timeout_seconds: int = 60
    extra: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent configuration
# ---------------------------------------------------------------------------

class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    enabled: bool = True
    provider: Provider = Provider.OPENAI
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 4096
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Routing configuration
# ---------------------------------------------------------------------------

class RoutingRule(BaseModel):
    """A rule that maps agent roles or tasks to specific providers/models."""

    pattern: str = "*"  # agent role or task pattern
    provider: Provider = Provider.OPENAI
    model: str = ""
    priority: int = 0


class RoutingConfig(BaseModel):
    """Configuration for the model router."""

    default_provider: Provider = Provider.OPENAI
    default_model: str = ""
    fallback_chain: list[Provider] = Field(
        default_factory=lambda: [Provider.OPENAI, Provider.ANTHROPIC, Provider.OLLAMA]
    )
    rules: list[RoutingRule] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Guardrail configuration
# ---------------------------------------------------------------------------

class GuardrailConfig(BaseModel):
    """Configuration for safety and cost guardrails."""

    max_cost_per_request_usd: float = 1.0
    max_cost_per_hour_usd: float = 10.0
    max_tokens_per_request: int = 16_000
    pii_detection_enabled: bool = True
    blocked_patterns: list[str] = Field(default_factory=list)
    min_severity_for_action: Severity = Severity.MEDIUM


# ---------------------------------------------------------------------------
# Telemetry configuration
# ---------------------------------------------------------------------------

class TelemetryConfig(BaseModel):
    """Configuration for usage tracking and observability."""

    enabled: bool = True
    log_requests: bool = False  # log full request/response (verbose)
    log_usage: bool = True
    export_format: str = "structured_log"  # structured_log | otlp


# ---------------------------------------------------------------------------
# Storage configuration
# ---------------------------------------------------------------------------

class StorageConfig(BaseModel):
    """Configuration for state persistence."""

    backend: str = "sqlite"  # sqlite | postgres
    connection_string: str = "sqlite:///opsbrain.db"


# ---------------------------------------------------------------------------
# Root configuration
# ---------------------------------------------------------------------------

class OpsBrainConfig(BaseModel):
    """Root configuration model for the entire OpsBrain system."""

    # General
    log_level: str = "INFO"
    data_dir: str = ".opsbrain"

    # Providers
    providers: dict[Provider, ProviderConfig] = Field(default_factory=lambda: {
        Provider.OPENAI: ProviderConfig(
            default_model="gpt-4o",
            api_key=os.getenv("OPENAI_API_KEY", ""),
        ),
        Provider.GEMINI: ProviderConfig(
            default_model="gemini-2.5-flash",
            api_key=os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", "")),
        ),
        Provider.ANTHROPIC: ProviderConfig(
            default_model="claude-sonnet-4-20250514",
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        ),
        Provider.OLLAMA: ProviderConfig(
            default_model="llama3.1",
            api_base="http://localhost:11434",
        ),
        Provider.LITELLM: ProviderConfig(
            default_model="gpt-4o",
        ),
    })

    # Agents
    agents: dict[str, AgentConfig] = Field(default_factory=dict)

    # Routing
    routing: RoutingConfig = Field(default_factory=RoutingConfig)

    # Guardrails
    guardrails: GuardrailConfig = Field(default_factory=GuardrailConfig)

    # Telemetry
    telemetry: TelemetryConfig = Field(default_factory=TelemetryConfig)

    # Storage
    storage: StorageConfig = Field(default_factory=StorageConfig)


# ---------------------------------------------------------------------------
# Configuration loader
# ---------------------------------------------------------------------------

def load_config(
    config_path: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> OpsBrainConfig:
    """Load configuration from a YAML file with optional overrides.

    Priority: overrides > YAML file > environment variables > defaults.

    Args:
        config_path: Path to the YAML configuration file.
        overrides: Dictionary of values to override.

    Returns:
        A fully resolved OpsBrainConfig instance.

    Raises:
        ConfigFileNotFoundError: If the specified config file doesn't exist.
        ConfigError: If the config file is malformed.
    """
    data: dict[str, Any] = {}

    if config_path is not None:
        path = Path(config_path)
        if not path.exists():
            raise ConfigFileNotFoundError(
                f"Configuration file not found: {path}",
                details={"path": str(path)},
            )
        try:
            with open(path, encoding="utf-8") as f:
                raw = yaml.safe_load(f)
                if isinstance(raw, dict):
                    data = raw
        except yaml.YAMLError as exc:
            raise ConfigError(
                f"Failed to parse configuration file: {path}",
                details={"path": str(path), "error": str(exc)},
            ) from exc

    if overrides:
        data = _deep_merge(data, overrides)

    return OpsBrainConfig(**data)


def generate_default_config() -> str:
    """Generate a YAML string of the default configuration.

    Returns:
        The default configuration serialized as YAML.
    """
    config = OpsBrainConfig()
    data = config.model_dump(mode="json")
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base* (non-destructive to *base*)."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
