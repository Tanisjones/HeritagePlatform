from __future__ import annotations

import json
from typing import Any

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.serializers import Serializer

from .ai_config import AIConfig
from .availability import AIServiceUnavailable, require_ai_available
from .assist_serializers import (
    ContributionDraftAssistRequestSerializer,
    ContributionDraftAssistResponseSerializer,
    ContributionMetadataAssistRequestSerializer,
    ContributionMetadataAssistResponseSerializer,
    CuratorReviewAssistRequestSerializer,
    CuratorReviewAssistResponseSerializer,
    EducationalMetadataAssistRequestSerializer,
    EducationalMetadataAssistResponseSerializer,
    TranslateAssistRequestSerializer,
    TranslateAssistResponseSerializer,
)
from .providers import get_provider, is_supported_provider
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
        raise AIServiceUnavailable("AI operation is not allowed by configuration.")


def _require_supported_provider(config: AIConfig) -> None:
    if not is_supported_provider(config.provider):
        raise AIServiceUnavailable(f"Unsupported AI provider: {config.provider}")


def _enforce_input_size(payload: dict[str, Any]) -> None:
    # Measure the actual content (JSON), not the dict repr — repr noise
    # (OrderedDict([...]) wrappers, escaped quotes) would distort the bound,
    # especially for operations with nested payloads like translate.
    try:
        raw = json.dumps(payload, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        raw = str(payload)
    if len(raw) > MAX_INPUT_CHARS:
        raise AIServiceUnavailable("AI input too large.")


class BaseAssistView(APIView):
    """
    Shared pipeline for every AI assist endpoint:
      require AI available -> operation allow-listed -> supported provider ->
      per-user rate limit -> validate request -> bound input size ->
      render prompt -> call provider -> validate response (strict) -> 200.

    Subclasses declare the operation, the request/response serializers, the
    rate limit, the permission classes, and (optionally) the prompt variables.
    """

    operation: str = ""
    request_serializer: type[Serializer] = Serializer
    response_serializer: type[Serializer] = Serializer
    rate_limit_per_minute: int | None = None
    permission_classes = [permissions.IsAuthenticated]

    def prompt_variables(self, data: dict[str, Any]) -> dict[str, Any]:
        """Variables substituted into the prompt template. Override as needed."""
        return {"language": data.get("language", "es")}

    def post(self, request):  # noqa: ANN001
        config = require_ai_available()
        _require_operation_allowed(config, self.operation)
        _require_supported_provider(config)

        rate_kwargs = {}
        if self.rate_limit_per_minute is not None:
            rate_kwargs["limit_per_minute"] = self.rate_limit_per_minute
        enforce_user_rate_limit(user_id=request.user.id, operation=self.operation, **rate_kwargs)

        serializer = self.request_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        _enforce_input_size(data)

        prompt = _render_prompt(config.prompts[self.operation], variables=self.prompt_variables(data))
        client = get_provider(config)
        result = client.chat_json(system_prompt=prompt, user_payload=data)

        out = self.response_serializer(data=result.parsed_json)
        out.is_valid(raise_exception=True)
        return Response(out.validated_data, status=status.HTTP_200_OK)


class ContributionDraftAssistView(BaseAssistView):
    operation = "contribution_draft"
    request_serializer = ContributionDraftAssistRequestSerializer
    response_serializer = ContributionDraftAssistResponseSerializer


class ContributionMetadataAssistView(BaseAssistView):
    operation = "contribution_metadata"
    request_serializer = ContributionMetadataAssistRequestSerializer
    response_serializer = ContributionMetadataAssistResponseSerializer


class CuratorReviewAssistView(BaseAssistView):
    operation = "curator_review_assist"
    request_serializer = CuratorReviewAssistRequestSerializer
    response_serializer = CuratorReviewAssistResponseSerializer
    rate_limit_per_minute = 20
    permission_classes = [IsStaff]


class EducationalMetadataAssistView(BaseAssistView):
    operation = "educational_metadata"
    request_serializer = EducationalMetadataAssistRequestSerializer
    response_serializer = EducationalMetadataAssistResponseSerializer


class TranslateAssistView(BaseAssistView):
    operation = "translate"
    request_serializer = TranslateAssistRequestSerializer
    response_serializer = TranslateAssistResponseSerializer

    def prompt_variables(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "source_lang": data.get("source_lang", ""),
            "target_lang": data.get("target_lang", ""),
        }
