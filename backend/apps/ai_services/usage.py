"""Recording of AI operation usage for the AI-economy dashboard.

`record_ai_usage` writes one AIUsageRecord per attempt. It is deliberately
best-effort: recording must NEVER break the AI operation, so all failures here
are swallowed and logged.
"""

from __future__ import annotations

import logging

from .ai_config import AIConfig
from .models import AIUsageRecord
from .providers.base import TokenUsage

logger = logging.getLogger(__name__)


def record_ai_usage(
    *,
    user_id: int | None,
    operation: str,
    config: AIConfig | None,
    usage: TokenUsage | None,
    duration_ms: int | None,
    status: str,
    error_type: str = "",
) -> None:
    """Persist one AIUsageRecord. Never raises."""
    try:
        provider = config.provider if config else ""
        model = config.model if config else ""
        input_tokens = usage.input_tokens if usage else None
        output_tokens = usage.output_tokens if usage else None
        total_tokens = usage.total_tokens if usage else None
        estimated_cost = (
            config.estimate_cost(model, input_tokens, output_tokens) if config else None
        )
        AIUsageRecord.objects.create(
            user_id=user_id,
            operation=operation or "",
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            duration_ms=duration_ms,
            status=status,
            error_type=error_type[:80],
        )
        # Drop the cached month-to-date budget aggregate for this scope so the next
        # budget check sees this row immediately (tightens the ~60s soft window).
        from .budget import invalidate_budget_cache

        invalidate_budget_cache(user_id=user_id)
    except Exception:  # noqa: BLE001 — recording must never break the AI request
        logger.exception("Failed to record AI usage (operation=%s)", operation)
