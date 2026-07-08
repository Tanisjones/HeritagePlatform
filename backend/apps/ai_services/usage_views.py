"""Aggregation endpoints for the AI-economy dashboard (G.4).

Three staff/curator-gated read endpoints over `AIUsageRecord`:

- ``GET /ai/usage/summary/``    — grouped totals (by operation/provider/model/user/day)
- ``GET /ai/usage/timeseries/`` — daily buckets for the line charts
- ``GET /ai/usage/recent/``     — last N raw rows for an audit table

All three share date-range parsing (``?since=&until=``, ISO dates), default to the
last 30 days when ``since`` is omitted, and are gated to staff/curator via
``IsCurator``. Aggregation is done in the DB (``Values().annotate(Count/Sum)``);
cost is summed from the per-row ``estimated_cost_usd`` already computed at record
time — the dashboard never re-prices.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, Sum, Value
from django.db.models.functions import Coalesce, TruncDate
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.cities.request import get_request_city
from apps.moderation.permissions import IsCurator

from .models import AIUsageRecord
from .usage_serializers import AIUsageRecordSerializer

# Cap how far back an unbounded query reaches, and how wide any window may be.
DEFAULT_WINDOW_DAYS = 30
MAX_WINDOW_DAYS = 366
MAX_RECENT_LIMIT = 200
DEFAULT_RECENT_LIMIT = 50

# group_by -> the AIUsageRecord field(s) the DB groups on.
GROUP_BY_FIELDS = {
    "operation": ["operation"],
    "provider": ["provider"],
    "model": ["provider", "model"],
    "user": ["user__email"],
    "day": None,  # special-cased: TruncDate('created_at')
}

# Zero-decimal used so Coalesce keeps the DecimalField output type.
_ZERO_COST = Value(Decimal("0"), output_field=DecimalField(max_digits=14, decimal_places=6))


def _parse_iso_date(raw: str | None):
    """Parse a YYYY-MM-DD string; return a date or None. Raises ValueError on bad input."""
    if not raw:
        return None
    return date.fromisoformat(raw)


class _UsageRangeMixin:
    """Shared ``?since=&until=`` parsing with a 30-day default and a hard cap."""

    permission_classes = [IsCurator]

    def get_range(self, request):
        """Return (start_dt, end_dt) as aware datetimes, or raise ValueError.

        ``since``/``until`` are inclusive ISO dates. ``until`` covers the whole day.
        Defaults: ``since`` = today-30d, ``until`` = today. The window is clamped to
        MAX_WINDOW_DAYS to keep a single query bounded.
        """
        today = timezone.localdate()
        since = _parse_iso_date(request.query_params.get("since")) or (
            today - timedelta(days=DEFAULT_WINDOW_DAYS)
        )
        until = _parse_iso_date(request.query_params.get("until")) or today
        if until < since:
            raise ValueError("`until` must not be before `since`.")
        if (until - since).days > MAX_WINDOW_DAYS:
            raise ValueError(f"Date range too wide; maximum is {MAX_WINDOW_DAYS} days.")

        tz = timezone.get_current_timezone()
        start_dt = datetime.combine(since, time.min, tzinfo=tz)
        # end is exclusive at the start of the day AFTER `until`, so the whole
        # `until` day is included.
        end_dt = datetime.combine(until + timedelta(days=1), time.min, tzinfo=tz)
        return start_dt, end_dt

    def base_queryset(self, request):
        start_dt, end_dt = self.get_range(request)
        qs = AIUsageRecord.objects.filter(created_at__gte=start_dt, created_at__lt=end_dt)
        # Optional per-city drill-down (?city=/X-City); no city = global totals,
        # which keeps the pre-multi-city dashboard behavior.
        city = get_request_city(request)
        if city is not None:
            qs = qs.filter(city=city)
        return qs


class AIUsageSummaryView(_UsageRangeMixin, APIView):
    """Grouped usage totals for the dashboard's breakdown tables/bars.

    ``?group_by=operation|provider|model|user|day`` (default ``operation``).
    Returns ``{ group_by, since, until, totals, rows: [...] }`` where each row is
    ``{ key, calls, input_tokens, output_tokens, total_tokens, estimated_cost_usd }``.
    """

    def get(self, request):  # noqa: ANN001
        try:
            qs = self.base_queryset(request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        group_by = request.query_params.get("group_by", "operation")
        if group_by not in GROUP_BY_FIELDS:
            return Response(
                {"detail": f"Invalid group_by. Choose one of: {', '.join(GROUP_BY_FIELDS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        agg = {
            "calls": Count("id"),
            "input_tokens": Coalesce(Sum("input_tokens"), 0),
            "output_tokens": Coalesce(Sum("output_tokens"), 0),
            "total_tokens": Coalesce(Sum("total_tokens"), 0),
            "estimated_cost_usd": Coalesce(Sum("estimated_cost_usd"), _ZERO_COST),
        }

        if group_by == "day":
            grouped = (
                qs.annotate(day=TruncDate("created_at"))
                .values("day")
                .annotate(**agg)
                .order_by("day")
            )
            rows = [
                {"key": (r["day"].isoformat() if r["day"] else None), **_row_metrics(r)}
                for r in grouped
            ]
        else:
            fields = GROUP_BY_FIELDS[group_by]
            grouped = qs.values(*fields).annotate(**agg).order_by("-calls")
            rows = [{"key": _row_key(r, fields), **_row_metrics(r)} for r in grouped]

        totals = qs.aggregate(**agg)
        totals_metrics = _row_metrics(totals)
        # True window-wide error count (not ok) so the dashboard KPI reflects the
        # whole period, not a 50-row sample.
        totals_metrics["error_calls"] = qs.exclude(status=AIUsageRecord.STATUS_OK).count()
        since, until = _range_echo(request)
        return Response(
            {
                "group_by": group_by,
                "since": since,
                "until": until,
                "totals": totals_metrics,
                "rows": rows,
            },
            status=status.HTTP_200_OK,
        )


class AIUsageTimeseriesView(_UsageRangeMixin, APIView):
    """Daily buckets for the spend/tokens line chart.

    Returns ``{ since, until, points: [{date, calls, total_tokens, estimated_cost_usd}] }``.
    Days with no activity are omitted (the client fills gaps if it wants a continuous axis).
    """

    def get(self, request):  # noqa: ANN001
        try:
            qs = self.base_queryset(request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        buckets = (
            qs.annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                calls=Count("id"),
                total_tokens=Coalesce(Sum("total_tokens"), 0),
                estimated_cost_usd=Coalesce(Sum("estimated_cost_usd"), _ZERO_COST),
            )
            .order_by("day")
        )
        points = [
            {
                "date": r["day"].isoformat() if r["day"] else None,
                "calls": r["calls"],
                "total_tokens": r["total_tokens"],
                "estimated_cost_usd": str(r["estimated_cost_usd"]),
            }
            for r in buckets
        ]
        since, until = _range_echo(request)
        return Response({"since": since, "until": until, "points": points}, status=status.HTTP_200_OK)


class AIUsageRecentView(_UsageRangeMixin, APIView):
    """Most-recent raw usage rows for the audit table.

    ``?limit=`` (default 50, max 200). Ordered newest-first. Honours the same
    ``?since=&until=`` window as the other endpoints.
    """

    def get(self, request):  # noqa: ANN001
        try:
            qs = self.base_queryset(request)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            limit = int(request.query_params.get("limit", DEFAULT_RECENT_LIMIT))
        except (TypeError, ValueError):
            return Response({"detail": "`limit` must be an integer."}, status=status.HTTP_400_BAD_REQUEST)
        limit = max(1, min(limit, MAX_RECENT_LIMIT))

        rows = qs.select_related("user").order_by("-created_at")[:limit]
        data = AIUsageRecordSerializer(rows, many=True).data
        return Response({"count": len(data), "results": data}, status=status.HTTP_200_OK)


def _row_key(row: dict, fields: list[str]) -> str:
    """Join grouped field values into a single display key (e.g. provider/model)."""
    parts = [str(row.get(f) or "—") for f in fields]
    return "/".join(parts)


def _row_metrics(row: dict) -> dict:
    """Normalise the aggregate fields (cost as string to preserve Decimal precision)."""
    cost = row.get("estimated_cost_usd")
    return {
        "calls": row.get("calls", 0),
        "input_tokens": row.get("input_tokens", 0) or 0,
        "output_tokens": row.get("output_tokens", 0) or 0,
        "total_tokens": row.get("total_tokens", 0) or 0,
        "estimated_cost_usd": str(cost if cost is not None else Decimal("0")),
    }


def _range_echo(request) -> tuple[str, str]:
    """Echo the resolved since/until back to the client (post-default)."""
    today = timezone.localdate()
    since = _parse_iso_date(request.query_params.get("since")) or (
        today - timedelta(days=DEFAULT_WINDOW_DAYS)
    )
    until = _parse_iso_date(request.query_params.get("until")) or today
    return since.isoformat(), until.isoformat()
