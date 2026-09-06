"""Model router — selects the optimal provider and model for each request.

Routing decisions can be based on:
- Explicit routing rules (e.g., "RCA agent always uses Claude")
- Cost constraints (prefer cheaper models for triage)
- Capability requirements (need vision → use GPT-4o or Gemini)
- Fallback chains when the primary provider is unavailable
"""

from __future__ import annotations

import fnmatch
from typing import Any

import structlog

from opsbrain.core.config import OpsBrainConfig
from opsbrain.core.exceptions import ProviderNotFoundError
from opsbrain.core.types import LLMRequest, LLMResponse, Provider
from opsbrain.harness.registry import ProviderRegistry

logger = structlog.get_logger(__name__)


class ModelRouter:
    """Routes LLM requests to the appropriate provider based on rules.

    The router consults the routing configuration to determine which
    provider and model should handle a given request, and falls back
    through a chain of alternatives if the primary choice fails.

    Usage::

        router = ModelRouter(config, registry)
        response = await router.route(request, context={"agent_role": "rca"})
    """

    def __init__(self, config: OpsBrainConfig, registry: ProviderRegistry) -> None:
        self._config = config
        self._routing = config.routing
        self._registry = registry

    async def route(
        self,
        request: LLMRequest,
        *,
        context: dict[str, Any] | None = None,
        required_features: list[str] | None = None,
    ) -> LLMResponse:
        """Route a request to the best available provider.

        Args:
            request: The LLM request to route.
            context: Additional context for routing decisions (e.g.,
                ``{"agent_role": "rca", "task": "deep_analysis"}``).
            required_features: Features the provider must support
                (e.g., ``["tool_calling", "vision"]``).

        Returns:
            The LLM response from the selected provider.

        Raises:
            ProviderNotFoundError: If no provider can handle the request.
        """
        ctx = context or {}
        provider, model = self._resolve(ctx, required_features)

        # Override model on the request if resolved
        routed_request = request.model_copy()
        if model:
            routed_request.model = model

        # Try primary, then walk the fallback chain
        chain = [provider, *[
            p for p in self._routing.fallback_chain if p != provider
        ]]

        last_error: Exception | None = None
        for prov in chain:
            try:
                client = self._registry.get(prov)

                # If specific features are required, verify support
                if required_features:
                    unsupported = [
                        f for f in required_features
                        if not client.supports_feature(f)
                    ]
                    if unsupported:
                        logger.debug(
                            "router.skip_provider",
                            provider=prov.value,
                            missing_features=unsupported,
                        )
                        continue

                logger.info(
                    "router.dispatching",
                    provider=prov.value,
                    model=routed_request.model or "(default)",
                    agent_role=ctx.get("agent_role", ""),
                )
                return await client.complete(routed_request)

            except ProviderNotFoundError:
                logger.debug("router.provider_unavailable", provider=prov.value)
                continue
            except Exception as exc:
                logger.warning(
                    "router.provider_error",
                    provider=prov.value,
                    error=str(exc),
                )
                last_error = exc
                continue

        raise ProviderNotFoundError(
            "No provider in the fallback chain could handle the request. "
            f"Last error: {last_error}",
        )

    def _resolve(
        self,
        context: dict[str, Any],
        required_features: list[str] | None,
    ) -> tuple[Provider, str]:
        """Resolve the provider and model from routing rules.

        Returns:
            A ``(provider, model)`` tuple. *model* may be empty if the
            provider's default should be used.
        """
        agent_role = context.get("agent_role", "")
        task = context.get("task", "")

        # Check explicit routing rules (highest priority first)
        matched_rules = sorted(
            self._routing.rules,
            key=lambda r: r.priority,
            reverse=True,
        )
        for rule in matched_rules:
            if fnmatch.fnmatch(agent_role, rule.pattern) or fnmatch.fnmatch(task, rule.pattern):
                logger.debug(
                    "router.rule_matched",
                    pattern=rule.pattern,
                    provider=rule.provider.value,
                    model=rule.model,
                )
                return rule.provider, rule.model

        # Fall back to defaults
        return self._routing.default_provider, self._routing.default_model
