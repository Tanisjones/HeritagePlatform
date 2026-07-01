from __future__ import annotations

import json
from typing import Any

import httpx

from ..ai_config import AIConfig
from ..availability import AIServiceUnavailable
from ..ollama_client import _parse_json_lenient
from .base import ChatProvider, ChatResult, ProviderHealth, TokenUsage

# Google Generative Language REST API base.
_GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"

_JSON_INSTRUCTION = (
    "Return ONLY valid JSON (no markdown, no code fences, no commentary). "
    "Do NOT invent authoritative sources or URLs; use null when unknown."
)


class GeminiProvider(ChatProvider):
    """
    Calls Google's Gemini `generateContent` endpoint with native JSON mode.

    The API key is read from config (resolved from an env var — see AIConfig);
    it is never persisted in ai.yaml.
    """

    def __init__(self, config: AIConfig) -> None:
        self._config = config

    def _require_key(self) -> str:
        key = self._config.api_key
        if not key:
            raise AIServiceUnavailable(
                "Gemini API key not configured "
                f"(set {self._config.api_key_env or 'the API key env var'})."
            )
        return key

    def chat_json(self, *, system_prompt: str, user_payload: dict[str, Any]) -> ChatResult:
        key = self._require_key()
        model = self._config.model
        url = f"{_GEMINI_API_BASE}/models/{model}:generateContent"

        body = {
            "system_instruction": {
                "parts": [{"text": f"{system_prompt.strip()}\n\n{_JSON_INSTRUCTION}"}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": json.dumps(user_payload, ensure_ascii=False)}],
                }
            ],
            "generationConfig": {
                "temperature": self._config.temperature,
                "maxOutputTokens": self._config.max_output_tokens,
                # Native JSON mode — Gemini guarantees parseable JSON output.
                "responseMimeType": "application/json",
            },
        }

        try:
            resp = httpx.post(
                url,
                params={"key": key},
                json=body,
                timeout=httpx.Timeout(self._config.request_timeout_seconds),
            )
        except httpx.RequestError as exc:
            raise AIServiceUnavailable(f"AI provider request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise AIServiceUnavailable(f"AI provider error: HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise AIServiceUnavailable("AI provider returned non-JSON response.") from exc

        # A safety/recitation block returns HTTP 200 with no candidates and a
        # promptFeedback.blockReason — surface that distinctly, not as a generic
        # "missing content" outage.
        block_reason = _block_reason(data)
        if block_reason:
            raise AIServiceUnavailable(f"AI request was blocked by the provider ({block_reason}).")

        text = _extract_text(data)
        if text is None:
            raise AIServiceUnavailable("AI provider response missing content.")

        # JSON mode (responseMimeType=application/json) yields parseable JSON, so
        # parse it directly; fall back to lenient extraction only if that fails.
        try:
            parsed = json.loads(text)
        except ValueError:
            parsed = _parse_json_lenient(text)
        if parsed is None:
            raise AIServiceUnavailable("AI returned invalid JSON.")

        return ChatResult(raw_text=text, parsed_json=parsed, usage=_extract_usage(data))

    def health(self) -> ProviderHealth:
        if not self._config.api_key:
            return ProviderHealth(
                available=False,
                reason=(
                    "Gemini API key not configured "
                    f"(set {self._config.api_key_env or 'the API key env var'})."
                ),
            )
        # Key is present; a cheap ListModels call confirms it is valid/reachable.
        try:
            resp = httpx.get(
                f"{_GEMINI_API_BASE}/models",
                params={"key": self._config.api_key},
                timeout=httpx.Timeout(2.5),
            )
        except httpx.RequestError:
            return ProviderHealth(available=False, reason="Gemini not reachable.")

        if resp.status_code >= 400:
            return ProviderHealth(available=False, reason=f"Gemini error: HTTP {resp.status_code}.")

        return ProviderHealth(available=True)


def _block_reason(data: Any) -> str | None:
    """Return the promptFeedback.blockReason if the request was safety-blocked."""
    if not isinstance(data, dict):
        return None
    feedback = data.get("promptFeedback")
    reason = feedback.get("blockReason") if isinstance(feedback, dict) else None
    return reason if isinstance(reason, str) and reason else None


def _extract_usage(data: Any) -> TokenUsage | None:
    """Read Gemini's usageMetadata{promptTokenCount, candidatesTokenCount,
    totalTokenCount} into a provider-agnostic TokenUsage, or None if absent."""
    meta = data.get("usageMetadata") if isinstance(data, dict) else None
    if not isinstance(meta, dict):
        return None

    def _int(key: str) -> int | None:
        value = meta.get(key)
        return value if isinstance(value, int) else None

    return TokenUsage(
        input_tokens=_int("promptTokenCount"),
        output_tokens=_int("candidatesTokenCount"),
        total_tokens=_int("totalTokenCount"),
    )


def _extract_text(data: Any) -> str | None:
    """Pull the first text part out of a Gemini generateContent response."""
    if not isinstance(data, dict):
        return None
    candidates = data.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        return None
    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list) or not parts:
        return None
    text = parts[0].get("text") if isinstance(parts[0], dict) else None
    return text if isinstance(text, str) else None


__all__ = ["GeminiProvider"]
