from __future__ import annotations

from ..ai_config import AIConfig
from ..availability import AIServiceUnavailable
from .base import ChatProvider, ChatResult, ProviderHealth

# Providers the factory knows how to build. Keep in sync with get_provider().
SUPPORTED_PROVIDERS = ("ollama", "gemini")


def is_supported_provider(name: str) -> bool:
    return name in SUPPORTED_PROVIDERS


def get_provider(config: AIConfig) -> ChatProvider:
    """
    Build the configured AI provider. Raises AIServiceUnavailable for an
    unknown provider so callers get a clean 503 instead of an AttributeError.
    """
    if config.provider == "ollama":
        from .ollama import OllamaProvider

        return OllamaProvider(config)

    if config.provider == "gemini":
        from .gemini import GeminiProvider

        return GeminiProvider(config)

    raise AIServiceUnavailable(f"Unsupported AI provider: {config.provider}")


__all__ = [
    "ChatProvider",
    "ChatResult",
    "ProviderHealth",
    "get_provider",
    "is_supported_provider",
    "SUPPORTED_PROVIDERS",
]
