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


class EducationalMetadataAssistRequestSerializer(serializers.Serializer):
    language = serializers.CharField(required=False, default="es", max_length=10)
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    resource_type = serializers.CharField(required=False, allow_blank=True, max_length=60)


class EducationalMetadataAssistResponseSerializer(StrictSerializer):
    learning_resource_type = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=40)
    difficulty = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=20)
    typical_age_range = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=20)
    typical_learning_time = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=40)
    context = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=40)
    learning_objectives = serializers.ListField(
        child=serializers.CharField(allow_blank=False, max_length=300),
        allow_empty=True,
        max_length=20,
    )
    keywords = serializers.ListField(
        child=serializers.CharField(allow_blank=False, max_length=60),
        allow_empty=True,
        max_length=30,
    )


class TranslateFieldsSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=5000)
    keywords = serializers.ListField(
        child=serializers.CharField(allow_blank=True, max_length=60),
        required=False,
        allow_empty=True,
        max_length=30,
    )


class TranslateAssistRequestSerializer(serializers.Serializer):
    source_lang = serializers.CharField(max_length=10)
    target_lang = serializers.CharField(max_length=10)
    fields = TranslateFieldsSerializer()


class TranslateAssistResponseSerializer(StrictSerializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=400)
    description = serializers.CharField(required=False, allow_blank=True, max_length=8000)
    keywords = serializers.ListField(
        child=serializers.CharField(allow_blank=True, max_length=80),
        required=False,
        allow_empty=True,
        max_length=30,
    )


class RouteMetadataStopSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    description = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class RouteMetadataAssistRequestSerializer(serializers.Serializer):
    language = serializers.CharField(required=False, default="es", max_length=10)
    title = serializers.CharField(required=False, allow_blank=True, max_length=200)
    stops = RouteMetadataStopSerializer(many=True, required=False)


class RouteMetadataAssistResponseSerializer(StrictSerializer):
    description = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=5000)
    theme = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=100)
    difficulty = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=20)
    estimated_duration = serializers.CharField(required=False, allow_null=True, allow_blank=True, max_length=40)
