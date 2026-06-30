from __future__ import annotations

from typing import Any

import httpx

from ..ai_config import AIConfig
from ..availability import AIServiceUnavailable
from ..ollama_client import OllamaClient
from .base import ChatProvider, ChatResult, ProviderHealth


class OllamaProvider(ChatProvider):
    """Adapts the existing OllamaClient to the ChatProvider interface."""

    def __init__(self, config: AIConfig) -> None:
        self._config = config
        self._client = OllamaClient(config)

    def chat_json(self, *, system_prompt: str, user_payload: dict[str, Any]) -> ChatResult:
        result = self._client.chat_json(system_prompt=system_prompt, user_payload=user_payload)
        return ChatResult(raw_text=result.raw_text, parsed_json=result.parsed_json)

    def health(self) -> ProviderHealth:
        # Probe Ollama's /api/tags — confirms the daemon is reachable. (Does not
        # verify the configured model is pulled; that is a deeper check.)
        base = self._config.base_url.rstrip("/")
        try:
            resp = httpx.get(f"{base}/api/tags", timeout=httpx.Timeout(2.5))
        except httpx.RequestError:
            return ProviderHealth(available=False, reason="Ollama not reachable.")

        if resp.status_code >= 400:
            return ProviderHealth(available=False, reason=f"Ollama error: HTTP {resp.status_code}.")

        return ProviderHealth(available=True)


__all__ = ["OllamaProvider", "AIServiceUnavailable"]
