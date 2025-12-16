from __future__ import annotations

import httpx
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .ai_config import AIConfigError, load_ai_config


class AIStatusView(APIView):
    """
    Lightweight availability check for the UI to enable/disable AI buttons.
    Returns 200 with `{ available: bool, reason?: str }`.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request):  # noqa: ANN001
        try:
            config = load_ai_config()
        except AIConfigError as exc:
            return Response({"available": False, "reason": str(exc)}, status=status.HTTP_200_OK)

        if not config.enabled:
            return Response({"available": False, "reason": "AI disabled."}, status=status.HTTP_200_OK)

        if config.provider != "ollama":
            return Response(
                {"available": False, "reason": f"Unsupported provider: {config.provider}."},
                status=status.HTTP_200_OK,
            )

        base = config.base_url.rstrip("/")
        try:
            resp = httpx.get(f"{base}/api/tags", timeout=httpx.Timeout(2.5))
            if resp.status_code >= 400:
                return Response(
                    {"available": False, "reason": f"Ollama error: HTTP {resp.status_code}."},
                    status=status.HTTP_200_OK,
                )
        except httpx.RequestError:
            return Response(
                {"available": False, "reason": "Ollama not reachable."},
                status=status.HTTP_200_OK,
            )

        return Response({"available": True}, status=status.HTTP_200_OK)

