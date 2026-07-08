from __future__ import annotations

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.permissions import is_curator_anywhere

from .ai_config import AIConfigError, load_ai_config
from .budget import budget_status
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

        # Remaining monthly allowance (G.6), when budgets are configured. The
        # per-user block is for the authenticated caller; the platform-wide global
        # block is sensitive spend data, exposed ONLY to staff/curator (never
        # anonymously — this endpoint is AllowAny).
        user = request.user if request.user and request.user.is_authenticated else None
        user_id = user.id if user else None
        is_curator = is_curator_anywhere(user)
        budgets = budget_status(user_id=user_id, config=config, include_global=is_curator)
        if budgets is not None:
            body["budget"] = budgets

        return Response(body, status=status.HTTP_200_OK)

