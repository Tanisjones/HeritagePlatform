from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import httpx

from .ai_config import AIConfig
from .availability import AIServiceUnavailable


@dataclass(frozen=True)
class OllamaChatResult:
    raw_text: str
    parsed_json: Any


class OllamaClient:
    def __init__(self, config: AIConfig) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=config.base_url.rstrip("/"),
            timeout=httpx.Timeout(config.request_timeout_seconds),
        )

    def chat_json(self, *, system_prompt: str, user_payload: dict[str, Any]) -> OllamaChatResult:
        """
        Calls Ollama `/api/chat` and returns parsed JSON, retrying once if JSON parsing fails.
        """
        messages = [
            {
                "role": "system",
                "content": (
                    system_prompt.strip()
                    + "\n\n"
                    + "IMPORTANT:\n"
                    + "- Return ONLY valid JSON (no markdown, no code fences, no commentary).\n"
                    + "- Do NOT invent authoritative sources or URLs; use null when unknown.\n"
                ),
            },
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ]

        content = self._call_chat(messages)
        parsed = _parse_json_lenient(content)
        if parsed is not None:
            return OllamaChatResult(raw_text=content, parsed_json=parsed)

        # Retry once with a stronger correction message.
        messages.append(
            {
                "role": "system",
                "content": "Your previous response was invalid. Return ONLY valid JSON for the requested schema.",
            }
        )
        content = self._call_chat(messages)
        parsed = _parse_json_lenient(content)
        if parsed is None:
            raise AIServiceUnavailable("AI returned invalid JSON.")

        return OllamaChatResult(raw_text=content, parsed_json=parsed)

    def _call_chat(self, messages: list[dict[str, str]]) -> str:
        options: dict[str, Any] = {
            "temperature": self._config.temperature,
            "num_predict": self._config.max_output_tokens,
        }
        payload: dict[str, Any] = {
            "model": self._config.model,
            "messages": messages,
            "stream": False,
            "options": options,
        }

        try:
            resp = self._client.post("/api/chat", json=payload)
        except httpx.RequestError as exc:
            raise AIServiceUnavailable(f"AI provider request failed: {exc}") from exc

        if resp.status_code >= 400:
            raise AIServiceUnavailable(f"AI provider error: HTTP {resp.status_code}")

        try:
            data = resp.json()
        except ValueError as exc:
            raise AIServiceUnavailable("AI provider returned non-JSON response.") from exc

        message = data.get("message") if isinstance(data, dict) else None
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, str):
            raise AIServiceUnavailable("AI provider response missing message content.")

        return content.strip()


def _parse_json_lenient(text: str) -> Any | None:
    """
    Attempts to parse JSON from model output, stripping common wrappers like code fences.
    Returns None when parsing fails.
    """
    candidate = text.strip()

    # Strip markdown code fences.
    if candidate.startswith("```"):
        candidate = candidate.strip("`").strip()
        if candidate.lower().startswith("json"):
            candidate = candidate[4:].strip()

    # Extract the first JSON object/array substring if the model added prose.
    start_obj = candidate.find("{")
    start_arr = candidate.find("[")
    if start_obj == -1 and start_arr == -1:
        return None

    start = min([i for i in [start_obj, start_arr] if i != -1])
    end_obj = candidate.rfind("}")
    end_arr = candidate.rfind("]")
    end = max(end_obj, end_arr)
    if end == -1 or end <= start:
        return None

    candidate = candidate[start : end + 1].strip()
    try:
        return json.loads(candidate)
    except ValueError:
        return None

