from __future__ import annotations

from rest_framework import status
from rest_framework.exceptions import APIException

from .ai_config import AIConfig, AIConfigError, load_ai_config


class AIServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_code = "ai_unavailable"
    default_detail = "AI is unavailable."


def require_ai_available() -> AIConfig:
    try:
        config = load_ai_config()
    except AIConfigError as exc:
        raise AIServiceUnavailable(str(exc)) from exc

    if not config.enabled:
        raise AIServiceUnavailable("AI is disabled by configuration.")

    return config

