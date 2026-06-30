from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_config import AIConfigError, load_ai_config
from .providers import get_provider, is_supported_provider


class AIStatusView(APIView):
    """
    Lightweight availability check for the UI to enable/disable AI buttons.
    Returns 200 with `{ available: bool, reason?: str, provider?, model? }`.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):  # noqa: ANN001
        try:
            config = load_ai_config()
        except AIConfigError as exc:
            return Response({"available": False, "reason": str(exc)}, status=status.HTTP_200_OK)

        if not config.enabled:
            return Response({"available": False, "reason": "AI disabled."}, status=status.HTTP_200_OK)

        if not is_supported_provider(config.provider):
            return Response(
                {"available": False, "reason": f"Unsupported provider: {config.provider}."},
                status=status.HTTP_200_OK,
            )

        # Delegate the reachability/configuration probe to the provider itself.
        health = get_provider(config).health()
        body = {
            "available": health.available,
            "provider": config.provider,
            "model": config.model,
        }
        if not health.available and health.reason:
            body["reason"] = health.reason

        return Response(body, status=status.HTTP_200_OK)

