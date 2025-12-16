"""
Admin configuration for gamification app models.
"""

from django.contrib import admin
from .models import Badge, Level, PointTransaction, UserBadge


@admin.register(Badge)
class BadgeAdmin(admin.ModelAdmin):
    """Admin interface for Badges."""
    list_display = ['name', 'category', 'points_value']
    list_filter = ['category']
    search_fields = ['name', 'description', 'category']
    readonly_fields = ['id']

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'name', 'description', 'icon')
        }),
        ('Classification', {
            'fields': ('category', 'points_value')
        }),
        ('Requirements', {
            'fields': ('requirements',),
            'description': 'JSON object defining badge requirements'
        }),
    )


@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    """Admin interface for Levels."""
    list_display = ['number', 'name', 'min_points', 'max_points']
    list_filter = ['number']
    search_fields = ['name']
    readonly_fields = ['id']
    ordering = ['number']

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'number', 'name')
        }),
        ('Points Range', {
            'fields': ('min_points', 'max_points')
        }),
        ('Benefits', {
            'fields': ('benefits',),
            'description': 'JSON object defining level benefits'
        }),
    )


@admin.register(PointTransaction)
class PointTransactionAdmin(admin.ModelAdmin):
    """Admin interface for Point Transactions."""
    list_display = ['user', 'points', 'reason', 'reference_type', 'created_at']
    list_filter = ['reference_type', 'created_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'reason', 'reference_id']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'user', 'points', 'reason')
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id'),
            'description': 'Links this transaction to a related object'
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserBadge)
class UserBadgeAdmin(admin.ModelAdmin):
    """Admin interface for User Badges."""
    list_display = ['user', 'badge', 'earned_at']
    list_filter = ['badge__category', 'earned_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'badge__name']
    readonly_fields = ['id', 'earned_at']
    date_hierarchy = 'earned_at'

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'user', 'badge')
        }),
        ('Timestamps', {
            'fields': ('earned_at',),
            'classes': ('collapse',)
        }),
    )
