"""Monthly AI spend/usage budgets (G.6).

Enforcement sums the *current calendar month's* AIUsageRecord rows and blocks with
HTTP 429 before the provider is called, when a configured cap would be exceeded.
Caps are config-driven (ai.yaml `budget:`) — per-user and global, in USD and/or
tokens. Everything is inert until a cap is set (all default to null).

The month-to-date aggregate is cached (~60s) so a burst of calls doesn't re-scan
the table each time; the cache key includes the year-month so it rolls over
naturally. Enforcement is intentionally a *soft* guard: a slightly stale cache can
let usage drift marginally over a cap, which is fine for a spend guardrail (and far
cheaper than a per-call full aggregate).
"""

from __future__ import annotations

from decimal import Decimal

from django.core.cache import cache
from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.exceptions import APIException

from .ai_config import AIConfig
from .models import AIUsageRecord

CACHE_TTL_SECONDS = 60

# Uniform scale for the USD strings surfaced to the UI, matching the 6dp of
# AIUsageRecord.estimated_cost_usd so cap/used/remaining line up.
_USD_Q = Decimal("0.000001")


def _usd_block(cap_value: float, used: Decimal) -> dict:
    cap = Decimal(str(cap_value)).quantize(_USD_Q)
    used_q = (used or Decimal("0")).quantize(_USD_Q)
    remaining = max(Decimal("0"), cap - used_q).quantize(_USD_Q)
    return {"cap": str(cap), "used": str(used_q), "remaining": str(remaining)}


class AIBudgetExceeded(APIException):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_code = "ai_budget_exceeded"
    default_detail = "The monthly AI budget has been reached. Please try again next month."


def _month_start(now=None):
    now = now or timezone.now()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _month_key(now=None) -> str:
    now = now or timezone.now()
    return now.strftime("%Y-%m")


def _aggregate(*, user_id: int | None) -> dict:
    """Month-to-date {cost, tokens, calls} for one user (user_id set) or globally.

    Cached per (scope, year-month). ``cost`` is a Decimal, ``tokens``/``calls`` ints.
    """
    scope = f"user:{user_id}" if user_id is not None else "global"
    cache_key = f"ai_budget:{scope}:{_month_key()}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    qs = AIUsageRecord.objects.filter(created_at__gte=_month_start())
    if user_id is not None:
        qs = qs.filter(user_id=user_id)
    agg = qs.aggregate(
        cost=Sum("estimated_cost_usd"),
        tokens=Sum("total_tokens"),
        calls=Count("id"),
    )
    result = {
        "cost": agg["cost"] or Decimal("0"),
        "tokens": agg["tokens"] or 0,
        "calls": agg["calls"] or 0,
    }
    cache.set(cache_key, result, timeout=CACHE_TTL_SECONDS)
    return result


def invalidate_budget_cache(*, user_id: int | None) -> None:
    """Drop the cached month-to-date aggregate for a scope (best-effort)."""
    for scope in filter(None, [f"user:{user_id}" if user_id is not None else None, "global"]):
        cache.delete(f"ai_budget:{scope}:{_month_key()}")


def enforce_budget(*, user_id: int | None, config: AIConfig) -> None:
    """Raise AIBudgetExceeded (429) if a configured monthly cap is already met.

    Checked before the provider call. No-op when no caps are configured. Never
    raises anything other than AIBudgetExceeded (a DB hiccup here must not block a
    legitimate AI call, so lookup failures fail open).
    """
    b = config.budget
    if not b.any_enabled:
        return

    try:
        # Per-user caps.
        if user_id is not None and (
            b.monthly_usd_per_user is not None or b.monthly_tokens_per_user is not None
        ):
            u = _aggregate(user_id=user_id)
            if b.monthly_usd_per_user is not None and u["cost"] >= Decimal(str(b.monthly_usd_per_user)):
                raise AIBudgetExceeded(
                    detail="Your monthly AI budget has been reached. Please try again next month."
                )
            if b.monthly_tokens_per_user is not None and u["tokens"] >= b.monthly_tokens_per_user:
                raise AIBudgetExceeded(
                    detail="Your monthly AI token allowance has been reached."
                )

        # Global caps.
        if b.monthly_usd_global is not None or b.monthly_tokens_global is not None:
            g = _aggregate(user_id=None)
            if b.monthly_usd_global is not None and g["cost"] >= Decimal(str(b.monthly_usd_global)):
                raise AIBudgetExceeded()
            if b.monthly_tokens_global is not None and g["tokens"] >= b.monthly_tokens_global:
                raise AIBudgetExceeded()
    except AIBudgetExceeded:
        raise
    except Exception:  # noqa: BLE001 — a budget lookup must never block a legit call
        return


def budget_status(*, user_id: int | None, config: AIConfig, include_global: bool = False) -> dict | None:
    """Remaining monthly allowance for `/ai/status/`, or None if no caps configured.

    Shape: ``{ enabled, user: {...}|null, global: {...} }`` with per-metric
    ``{cap, used, remaining}`` (cost as strings). Only configured metrics appear.

    ``include_global`` gates the platform-wide ``global`` block: it is sensitive
    internal spend data, so callers pass True ONLY for staff/curator. For everyone
    else (incl. the public /ai/status/ endpoint) ``global`` is an empty dict.
    """
    b = config.budget
    if not b.any_enabled:
        return None

    out: dict = {"enabled": True}

    if user_id is not None and (
        b.monthly_usd_per_user is not None or b.monthly_tokens_per_user is not None
    ):
        u = _aggregate(user_id=user_id)
        user_block: dict = {}
        if b.monthly_usd_per_user is not None:
            user_block["usd"] = _usd_block(b.monthly_usd_per_user, u["cost"])
        if b.monthly_tokens_per_user is not None:
            cap = b.monthly_tokens_per_user
            user_block["tokens"] = {
                "cap": cap,
                "used": u["tokens"],
                "remaining": max(0, cap - u["tokens"]),
            }
        out["user"] = user_block
    else:
        out["user"] = None

    global_block: dict = {}
    if include_global and (b.monthly_usd_global is not None or b.monthly_tokens_global is not None):
        g = _aggregate(user_id=None)
        if b.monthly_usd_global is not None:
            global_block["usd"] = _usd_block(b.monthly_usd_global, g["cost"])
        if b.monthly_tokens_global is not None:
            cap = b.monthly_tokens_global
            global_block["tokens"] = {
                "cap": cap,
                "used": g["tokens"],
                "remaining": max(0, cap - g["tokens"]),
            }
    out["global"] = global_block
    return out
