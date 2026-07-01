"""
Admin configuration for AI services app models.
"""

from django.contrib import admin
from .models import AISuggestion, AIUsageRecord


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


@admin.register(AIUsageRecord)
class AIUsageRecordAdmin(admin.ModelAdmin):
    """Read-only audit of AI usage/cost (the AI-economy dashboard's backing data)."""
    list_display = [
        'created_at', 'operation', 'provider', 'model', 'status',
        'input_tokens', 'output_tokens', 'total_tokens', 'estimated_cost_usd', 'user',
    ]
    list_filter = ['status', 'operation', 'provider', 'model', 'created_at']
    search_fields = ['operation', 'model', 'user__email']
    readonly_fields = [f.name for f in AIUsageRecord._meta.fields]
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False  # records are written only by the AI pipeline

    def has_change_permission(self, request, obj=None):
        return False  # audit log — read-only
