"""
Admin configuration for AI services app models.
"""

from django.contrib import admin
from .models import AISuggestion


@admin.register(AISuggestion)
class AISuggestionAdmin(admin.ModelAdmin):
    """Admin interface for AI Suggestions."""
    list_display = ['heritage_item', 'suggestion_type', 'suggester', 'status', 'confidence', 'created_at']
    list_filter = ['status', 'suggestion_type', 'suggester', 'created_at']
    search_fields = ['heritage_item__title', 'suggestion_type', 'suggester']
    readonly_fields = ['id', 'created_at', 'reviewed_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'heritage_item', 'suggester', 'suggestion_type')
        }),
        ('Content', {
            'fields': ('content', 'confidence'),
            'description': 'AI-generated suggestion content and confidence score'
        }),
        ('Review Status', {
            'fields': ('status', 'reviewed_by', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
