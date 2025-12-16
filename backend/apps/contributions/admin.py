"""
Admin configuration for contributions app models.
"""

from django.contrib import admin
from .models import Contribution, ContributionReview


class ContributionReviewInline(admin.TabularInline):
    """Inline admin for contribution reviews."""
    model = ContributionReview
    extra = 0
    readonly_fields = ['id', 'created_at']
    fields = ['reviewer', 'decision', 'feedback', 'created_at']


@admin.register(Contribution)
class ContributionAdmin(admin.ModelAdmin):
    """Admin interface for Contributions."""
    list_display = ['contribution_type', 'contributor', 'heritage_item', 'status', 'created_at', 'reviewed_at']
    list_filter = ['status', 'contribution_type', 'created_at', 'reviewed_at']
    search_fields = [
        'contributor__email', 'contributor__first_name', 'contributor__last_name',
        'heritage_item__title', 'reviewer__email'
    ]
    readonly_fields = ['id', 'created_at', 'reviewed_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'contribution_type', 'contributor', 'heritage_item')
        }),
        ('Content', {
            'fields': ('content',),
            'description': 'JSON data submitted by the contributor'
        }),
        ('Review', {
            'fields': ('status', 'reviewer', 'reviewed_at')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    inlines = [ContributionReviewInline]


@admin.register(ContributionReview)
class ContributionReviewAdmin(admin.ModelAdmin):
    """Admin interface for Contribution Reviews."""
    list_display = ['contribution', 'reviewer', 'decision', 'created_at']
    list_filter = ['decision', 'created_at']
    search_fields = [
        'contribution__contributor__email',
        'reviewer__email', 'reviewer__first_name', 'reviewer__last_name',
        'feedback'
    ]
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'contribution', 'reviewer', 'decision')
        }),
        ('Feedback', {
            'fields': ('feedback',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
