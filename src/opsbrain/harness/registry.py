"""Provider registry — discovers and manages LLM client instances.

The registry auto-detects which provider SDKs are installed and which
have valid API keys configured, then serves the appropriate
:class:`LLMClient` on demand.
"""

from __future__ import annotations

import importlib
from typing import Any

import structlog

from opsbrain.core.config import OpsBrainConfig
from opsbrain.core.exceptions import ProviderNotFoundError
from opsbrain.core.types import Provider
from opsbrain.harness.base import LLMClient

logger = structlog.get_logger(__name__)

# Map provider enum → module path for lazy imports
_PROVIDER_MODULES: dict[Provider, str] = {
    Provider.OPENAI: "opsbrain.harness.providers.openai",
    Provider.GEMINI: "opsbrain.harness.providers.gemini",
    Provider.ANTHROPIC: "opsbrain.harness.providers.anthropic",
    Provider.OLLAMA: "opsbrain.harness.providers.ollama",
    Provider.LITELLM: "opsbrain.harness.providers.litellm_provider",
}

# Map provider enum → its third-party SDK package name (for availability check)
_PROVIDER_SDK_PACKAGES: dict[Provider, str] = {
    Provider.OPENAI: "openai",
    Provider.GEMINI: "google.genai",
    Provider.ANTHROPIC: "anthropic",
    Provider.OLLAMA: "ollama",
    Provider.LITELLM: "litellm",
}


class ProviderRegistry:
    """Central registry that creates and caches LLM client instances.

    Usage::

        registry = ProviderRegistry(config)
        client = registry.get(Provider.OPENAI)
        response = await client.complete(request)
    """

    def __init__(self, config: OpsBrainConfig) -> None:
        self._config = config
        self._clients: dict[Provider, LLMClient] = {}

    # ----- public API -----

    def get(self, provider: Provider) -> LLMClient:
        """Return a cached client instance for *provider*.

        Args:
            provider: The provider to retrieve.

        Returns:
            An initialized :class:`LLMClient`.

        Raises:
            ProviderNotFoundError: If the provider is disabled, its SDK is
                missing, or its configuration is invalid.
        """
        if provider in self._clients:
            return self._clients[provider]

        client = self._create_client(provider)
        self._clients[provider] = client
        return client

    def list_available(self) -> list[dict[str, Any]]:
        """List all providers and their availability status.

        Returns:
            A list of dicts with ``provider``, ``available``, ``reason`` keys.
        """
        results: list[dict[str, Any]] = []
        for prov in Provider:
            status: dict[str, Any] = {"provider": prov.value}
            prov_config = self._config.providers.get(prov)

            if prov_config is None or not prov_config.enabled:
                status.update(available=False, reason="disabled in config")
            elif not _sdk_available(prov):
                status.update(available=False, reason="SDK not installed")
            elif prov not in (Provider.OLLAMA, Provider.LITELLM) and not prov_config.api_key:
                status.update(available=False, reason="no API key configured")
            else:
                status.update(available=True, reason="ready")

            results.append(status)
        return results

    async def health_check_all(self) -> dict[Provider, bool]:
        """Run health checks on all available providers.

        Returns:
            A mapping of provider → healthy boolean.
        """
        results: dict[Provider, bool] = {}
        for info in self.list_available():
            if info["available"]:
                prov = Provider(info["provider"])
                try:
                    client = self.get(prov)
                    results[prov] = await client.health_check()
                except Exception:
                    results[prov] = False
        return results

    async def close_all(self) -> None:
        """Close all cached client instances."""
        for client in self._clients.values():
            await client.close()
        self._clients.clear()

    # ----- private -----

    def _create_client(self, provider: Provider) -> LLMClient:
        """Instantiate a new client for the given provider."""
        prov_config = self._config.providers.get(provider)
        if prov_config is None or not prov_config.enabled:
            raise ProviderNotFoundError(
                f"Provider '{provider.value}' is not enabled in configuration.",
                provider=provider.value,
            )

        if not _sdk_available(provider):
            raise ProviderNotFoundError(
                f"SDK for provider '{provider.value}' is not installed. "
                f"Install it with: pip install opsbrain[{provider.value}]",
                provider=provider.value,
            )

        module_path = _PROVIDER_MODULES.get(provider)
        if module_path is None:
            raise ProviderNotFoundError(
                f"No adapter module registered for provider '{provider.value}'.",
                provider=provider.value,
            )

        module = importlib.import_module(module_path)
        factory = getattr(module, "create_client", None)
        if factory is None:
            raise ProviderNotFoundError(
                f"Adapter module '{module_path}' does not export a 'create_client' function.",
                provider=provider.value,
            )

        client: LLMClient = factory(prov_config, self._config)
        logger.info(
            "provider_registry.created",
            provider=provider.value,
            model=prov_config.default_model,
        )
        return client


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sdk_available(provider: Provider) -> bool:
    """Check whether the SDK package for *provider* is importable."""
    pkg = _PROVIDER_SDK_PACKAGES.get(provider, "")
    if not pkg:
        return False
    try:
        importlib.import_module(pkg)
        return True
    except ImportError:
        return False
