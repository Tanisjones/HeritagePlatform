from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def get_ai_suggestions(heritage_item):
    """
    Generate reviewable AI suggestions for a freshly created heritage item.

    Calls the configured AI provider (Ollama/Gemini) for structured metadata and
    maps the result to a list of suggestion dicts:
        {suggester, suggestion_type, content, confidence}
    that the caller persists as AISuggestion rows for a curator to approve.

    Resilient by design: if AI is disabled, misconfigured, or unreachable, this
    returns an empty list so contribution creation never fails because of AI.
    """
    # Import here to avoid import cycles and so a missing AI config can't break
    # the heritage app at import time.
    from .ai_config import load_ai_config
    from .availability import AIServiceUnavailable
    from .providers import get_provider, is_supported_provider

    try:
        config = load_ai_config()
    except Exception:  # noqa: BLE001 — config errors must not break item creation
        logger.exception("AI suggestions skipped: failed to load AI config")
        return []

    # Off by default: only attempt the (synchronous) provider call when an
    # operator has explicitly opted in AND the provider/operation are usable.
    if not config.auto_suggest_on_create:
        return []
    if not config.enabled or not is_supported_provider(config.provider):
        return []
    if "contribution_metadata" not in config.allowed_operations:
        return []

    try:
        provider = get_provider(config)
        prompt = config.prompts["contribution_metadata"]
        payload = {
            "language": "es",
            "title": heritage_item.title or "",
            "description": heritage_item.description or "",
        }
        result = provider.chat_json(system_prompt=prompt, user_payload=payload)
    except AIServiceUnavailable as exc:
        # Expected when the provider is down/misconfigured — info, not an error.
        logger.info("AI suggestions skipped (unavailable): %s", exc)
        return []
    except Exception:  # noqa: BLE001 — never let AI break item creation
        # Unexpected: log with traceback at ERROR so real bugs are visible,
        # but still return [] so the contribution is created.
        logger.exception("AI suggestion generation failed unexpectedly")
        return []

    data = result.parsed_json if isinstance(result.parsed_json, dict) else {}
    suggestions = []

    keywords = data.get("keywords")
    if isinstance(keywords, list):
        cleaned = [str(k).strip() for k in keywords if str(k).strip()]
        if cleaned:
            suggestions.append({
                "suggester": config.provider,
                "suggestion_type": "keyword",
                "content": cleaned,
                "confidence": None,
            })

    period = data.get("historical_period")
    if isinstance(period, str) and period.strip():
        suggestions.append({
            "suggester": config.provider,
            "suggestion_type": "historical_period",
            "content": period.strip(),
            "confidence": None,
        })

    return suggestions
