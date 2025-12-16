"""
Serializers for notifications app models.
"""

from rest_framework import serializers
from .models import NotificationTemplate, UserNotification


class NotificationTemplateSerializer(serializers.ModelSerializer):
    """Serializer for notification templates."""

    class Meta:
        model = NotificationTemplate
        fields = ['id', 'name', 'subject', 'body', 'is_html']


class UserNotificationSerializer(serializers.ModelSerializer):
    """Serializer for user notifications."""
    recipient_email = serializers.EmailField(source='recipient.email', read_only=True)
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )

    class Meta:
        model = UserNotification
        fields = [
            'id', 'recipient', 'recipient_email', 'notification_type',
            'notification_type_display', 'title', 'message', 'is_read',
            'read_at', 'content_type', 'object_id', 'created_at'
        ]
        read_only_fields = ['id', 'recipient', 'created_at', 'read_at']


class UserNotificationListSerializer(serializers.ModelSerializer):
    """Simplified serializer for listing user notifications."""
    notification_type_display = serializers.CharField(
        source='get_notification_type_display',
        read_only=True
    )

    class Meta:
        model = UserNotification
        fields = [
            'id', 'notification_type', 'notification_type_display',
            'title', 'message', 'is_read', 'created_at'
        ]
