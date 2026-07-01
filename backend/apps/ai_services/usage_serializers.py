"""Serializers for the AI-economy dashboard (G.4).

Only the raw-row audit table needs a serializer; the summary/timeseries endpoints
build plain dict payloads in the view. ``user`` is exposed as the email (a stable,
human-readable key) rather than a nested object — the dashboard only needs a label.
"""

from __future__ import annotations

from rest_framework import serializers

from .models import AIUsageRecord


class AIUsageRecordSerializer(serializers.ModelSerializer):
    """One AI usage attempt, for the recent-activity audit table."""

    user_email = serializers.CharField(source="user.email", read_only=True, default=None)

    class Meta:
        model = AIUsageRecord
        fields = [
            "id",
            "created_at",
            "user_email",
            "operation",
            "provider",
            "model",
            "input_tokens",
            "output_tokens",
            "total_tokens",
            "estimated_cost_usd",
            "duration_ms",
            "status",
            "error_type",
        ]
        read_only_fields = fields
