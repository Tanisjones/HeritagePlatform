from rest_framework import serializers

from apps.heritage.models import HeritageItem
from apps.heritage.serializers import HeritageItemDetailSerializer, HeritageItemListSerializer

from .models import (
    ContributionFlag,
    ContributionVersion,
    CuratorNote,
    QualityScore,
    ReviewChecklist,
    ReviewChecklistItem,
    ReviewChecklistResponse,
)


class QualityScoreSerializer(serializers.ModelSerializer):
    class Meta:
        model = QualityScore
        fields = [
            'id',
            'heritage_item',
            'completeness_score',
            'accuracy_score',
            'media_quality_score',
            'total_score',
            'scored_by',
            'scored_at',
            'notes',
        ]
        read_only_fields = ['id', 'heritage_item', 'total_score', 'scored_by', 'scored_at']


class ContributionVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributionVersion
        fields = [
            'id',
            'heritage_item',
            'version_number',
            'created_by',
            'created_by_type',
            'data_snapshot',
            'changes_summary',
            'created_at',
        ]
        read_only_fields = ['id', 'version_number', 'created_at']


class ContributionFlagSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContributionFlag
        fields = [
            'id',
            'heritage_item',
            'flag_type',
            'status',
            'flagged_by',
            'reason',
            'resolved_by',
            'resolution_notes',
            'resolved_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'heritage_item', 'flagged_by', 'resolved_by', 'resolved_at', 'created_at', 'updated_at']


class ReviewChecklistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewChecklistItem
        fields = ['id', 'text', 'help_text', 'order', 'is_required']


class ReviewChecklistSerializer(serializers.ModelSerializer):
    items = ReviewChecklistItemSerializer(many=True, read_only=True)

    class Meta:
        model = ReviewChecklist
        fields = [
            'id',
            'name',
            'description',
            'is_active',
            'applicable_to_types',
            'applicable_to_categories',
            'items',
        ]


class ReviewChecklistResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewChecklistResponse
        fields = [
            'id',
            'heritage_item',
            'checklist_item',
            'curator',
            'is_checked',
            'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'heritage_item', 'curator', 'created_at']


class CuratorNoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CuratorNote
        fields = [
            'id',
            'heritage_item',
            'curator',
            'content',
            'is_pinned',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'heritage_item', 'curator', 'created_at', 'updated_at']


class CuratorQueueItemSerializer(HeritageItemListSerializer):
    flags_open = serializers.IntegerField(read_only=True)
    total_score = serializers.IntegerField(read_only=True)

    class Meta(HeritageItemListSerializer.Meta):
        fields = HeritageItemListSerializer.Meta.fields + ['flags_open', 'total_score']


class CuratorReviewDetailSerializer(serializers.ModelSerializer):
    heritage_item = HeritageItemDetailSerializer(source='*', read_only=True)
    quality_score = QualityScoreSerializer(read_only=True)
    flags = ContributionFlagSerializer(many=True, read_only=True)
    checklist_responses = ReviewChecklistResponseSerializer(many=True, read_only=True)
    curator_notes = CuratorNoteSerializer(many=True, read_only=True)
    versions = ContributionVersionSerializer(many=True, read_only=True)

    class Meta:
        model = HeritageItem
        fields = [
            'heritage_item',
            'quality_score',
            'flags',
            'checklist_responses',
            'curator_notes',
            'versions',
        ]

