from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ChatResult:
    """Provider-agnostic result of a JSON chat completion."""

    raw_text: str
    parsed_json: Any


@dataclass(frozen=True)
class ProviderHealth:
    """Result of a provider availability probe (for GET /ai/status/)."""

    available: bool
    reason: str | None = None


@runtime_checkable
class ChatProvider(Protocol):
    """
    Common interface every AI provider (Ollama, Gemini, …) implements.

    `chat_json` takes a system prompt plus a JSON-serialisable user payload and
    returns parsed JSON; `health` reports whether the provider is reachable and
    configured so the UI can enable/disable AI affordances.
    """

    def chat_json(self, *, system_prompt: str, user_payload: dict[str, Any]) -> ChatResult: ...

    def health(self) -> ProviderHealth: ...
