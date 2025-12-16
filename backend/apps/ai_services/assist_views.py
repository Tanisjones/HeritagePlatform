from __future__ import annotations

import json
from typing import Any

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_config import AIConfig
from .availability import require_ai_available
from .assist_serializers import (
    ContributionDraftAssistRequestSerializer,
    ContributionDraftAssistResponseSerializer,
    ContributionMetadataAssistRequestSerializer,
    ContributionMetadataAssistResponseSerializer,
    CuratorReviewAssistRequestSerializer,
    CuratorReviewAssistResponseSerializer,
)
from .ollama_client import OllamaClient
from .rate_limit import enforce_user_rate_limit


class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view) -> bool:  # noqa: ANN001
        return bool(request.user and request.user.is_staff)


MAX_INPUT_CHARS = 12000


def _render_prompt(template: str, *, variables: dict[str, Any]) -> str:
    rendered = template
    for key, value in variables.items():
        placeholder = "{{" + key + "}}"
        if placeholder not in rendered:
            continue

        if value is None:
            rendered = rendered.replace(placeholder, "")
        elif isinstance(value, (dict, list)):
            rendered = rendered.replace(placeholder, json.dumps(value, ensure_ascii=False))
        else:
            rendered = rendered.replace(placeholder, str(value))
    return rendered


def _require_operation_allowed(config: AIConfig, operation: str) -> None:
    if operation not in config.allowed_operations:
        from .availability import AIServiceUnavailable

        raise AIServiceUnavailable("AI operation is not allowed by configuration.")


def _require_supported_provider(config: AIConfig) -> None:
    if config.provider != "ollama":
        from .availability import AIServiceUnavailable

        raise AIServiceUnavailable(f"Unsupported AI provider: {config.provider}")


def _enforce_input_size(payload: dict[str, Any]) -> None:
    # crude but effective: stringify and cap
    raw = str(payload)
    if len(raw) > MAX_INPUT_CHARS:
        from .availability import AIServiceUnavailable

        raise AIServiceUnavailable("AI input too large.")


class ContributionDraftAssistView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):  # noqa: ANN001
        config = require_ai_available()
        operation = "contribution_draft"
        _require_operation_allowed(config, operation)
        _require_supported_provider(config)
        enforce_user_rate_limit(user_id=request.user.id, operation=operation)

        serializer = ContributionDraftAssistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _enforce_input_size(data)

        prompt = _render_prompt(config.prompts[operation], variables={"language": data.get("language", "es")})
        client = OllamaClient(config)
        result = client.chat_json(system_prompt=prompt, user_payload=data)

        out = ContributionDraftAssistResponseSerializer(data=result.parsed_json)
        out.is_valid(raise_exception=True)
        return Response(out.validated_data, status=status.HTTP_200_OK)


class ContributionMetadataAssistView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):  # noqa: ANN001
        config = require_ai_available()
        operation = "contribution_metadata"
        _require_operation_allowed(config, operation)
        _require_supported_provider(config)
        enforce_user_rate_limit(user_id=request.user.id, operation=operation)

        serializer = ContributionMetadataAssistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _enforce_input_size(data)

        prompt = _render_prompt(config.prompts[operation], variables={"language": data.get("language", "es")})
        client = OllamaClient(config)
        result = client.chat_json(system_prompt=prompt, user_payload=data)

        out = ContributionMetadataAssistResponseSerializer(data=result.parsed_json)
        out.is_valid(raise_exception=True)
        return Response(out.validated_data, status=status.HTTP_200_OK)


class CuratorReviewAssistView(APIView):
    permission_classes = [IsStaff]

    def post(self, request):  # noqa: ANN001
        config = require_ai_available()
        operation = "curator_review_assist"
        _require_operation_allowed(config, operation)
        _require_supported_provider(config)
        enforce_user_rate_limit(user_id=request.user.id, operation=operation, limit_per_minute=20)

        serializer = CuratorReviewAssistRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _enforce_input_size(data)

        prompt = _render_prompt(config.prompts[operation], variables={"language": data.get("language", "es")})
        client = OllamaClient(config)
        result = client.chat_json(system_prompt=prompt, user_payload=data)

        out = CuratorReviewAssistResponseSerializer(data=result.parsed_json)
        out.is_valid(raise_exception=True)
        return Response(out.validated_data, status=status.HTTP_200_OK)
