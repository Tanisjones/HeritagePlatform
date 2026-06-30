from rest_framework import serializers
from .models import AISuggestion

class AISuggestionSerializer(serializers.ModelSerializer):
    heritage_item_title = serializers.CharField(source='heritage_item.title', read_only=True)

    class Meta:
        model = AISuggestion
        fields = [
            'id', 'heritage_item', 'heritage_item_title', 'suggester', 'suggestion_type',
            'content', 'confidence', 'status', 'created_at',
            'reviewed_by', 'reviewed_at'
        ]
