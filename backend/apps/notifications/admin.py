"""
Django admin configuration for notifications app.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import NotificationTemplate, UserNotification


@admin.register(NotificationTemplate)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """Admin interface for notification templates."""
    list_display = ['name', 'subject', 'is_html']
    list_filter = ['is_html']
    search_fields = ['name', 'subject', 'body']
    fieldsets = (
        (None, {
            'fields': ('name', 'subject', 'is_html')
        }),
        (_('Content'), {
            'fields': ('body',),
            'classes': ('wide',)
        }),
    )


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    """Admin interface for user notifications."""
    list_display = [
        'recipient', 'notification_type', 'title_preview',
        'is_read', 'created_at'
    ]
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['recipient__email', 'title', 'message']
    readonly_fields = ['id', 'created_at', 'read_at']
    raw_id_fields = ['recipient']
    date_hierarchy = 'created_at'

    fieldsets = (
        (None, {
            'fields': ('id', 'recipient', 'notification_type')
        }),
        (_('Content'), {
            'fields': ('title', 'message')
        }),
        (_('Status'), {
            'fields': ('is_read', 'read_at')
        }),
        (_('Related Object'), {
            'fields': ('content_type', 'object_id'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at',)
        }),
    )

    def title_preview(self, obj):
        """Show truncated title."""
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_preview.short_description = _('Title')

    def get_queryset(self, request):
        """Optimize queries with select_related."""
        return super().get_queryset(request).select_related('recipient')
