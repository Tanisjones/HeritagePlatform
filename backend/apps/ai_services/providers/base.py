from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class TokenUsage:
    """Token counts reported by a provider for a single completion.

    All optional because not every provider/response reports them; the AI-economy
    layer records whatever is present and prices it when possible.
    """

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class ChatResult:
    """Provider-agnostic result of a JSON chat completion."""

    raw_text: str
    parsed_json: Any
    usage: TokenUsage | None = None


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
