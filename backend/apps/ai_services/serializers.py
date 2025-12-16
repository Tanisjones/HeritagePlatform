from rest_framework import serializers
from .models import AISuggestion

class AISuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AISuggestion
        fields = [
            'id', 'heritage_item', 'suggester', 'suggestion_type',
            'content', 'confidence', 'status', 'created_at',
            'reviewed_by', 'reviewed_at'
        ]
