from __future__ import annotations

from rest_framework import serializers

from .strict_serializers import StrictSerializer


class ContributionDraftAssistRequestSerializer(serializers.Serializer):
    language = serializers.CharField(required=False, default="es", max_length=10)
    notes = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)


class ContributionDraftAssistResponseSerializer(StrictSerializer):
    title = serializers.CharField()
    description = serializers.CharField()


class ContributionMetadataAssistRequestSerializer(serializers.Serializer):
    language = serializers.CharField(required=False, default="es", max_length=10)
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    address = serializers.CharField(required=False, allow_blank=True, max_length=300)
    parish = serializers.CharField(required=False, allow_blank=True, max_length=120)
    heritage_type = serializers.CharField(required=False, allow_blank=True, max_length=120)
    heritage_category = serializers.CharField(required=False, allow_blank=True, max_length=120)


class ContributionMetadataAssistResponseSerializer(StrictSerializer):
    historical_period = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=120)
    keywords = serializers.ListField(
        child=serializers.CharField(allow_blank=False, max_length=60),
        allow_empty=True,
        max_length=30,
    )
    external_registry_url = serializers.URLField(required=False, allow_null=True, allow_blank=True)


class CuratorReviewAssistRequestSerializer(serializers.Serializer):
    language = serializers.CharField(required=False, default="es", max_length=10)
    # Keep flexible in Phase 3: frontend can send either a structured object or a string.
    item = serializers.JSONField(required=False)
    text = serializers.CharField(required=False, allow_blank=True, max_length=10000)


class SuggestedEditsSerializer(StrictSerializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    historical_period = serializers.CharField(required=False, allow_blank=True, max_length=120)


class CuratorReviewAssistResponseSerializer(StrictSerializer):
    missing_fields = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    risk_flags = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    curator_feedback_draft = serializers.CharField()
    suggested_edits = SuggestedEditsSerializer(required=False)
