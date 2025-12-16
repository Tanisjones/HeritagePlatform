"""
Views for notifications app.
"""

from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from .models import NotificationTemplate, UserNotification
from .serializers import (
    NotificationTemplateSerializer,
    UserNotificationSerializer,
    UserNotificationListSerializer
)


class IsAdminUser(permissions.BasePermission):
    """
    Custom permission to only allow admin users to access the view.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing notification templates.
    Only accessible by admin users.
    """
    queryset = NotificationTemplate.objects.all()
    serializer_class = NotificationTemplateSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'subject']


class UserNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for user notifications.
    Users can only view their own notifications.
    """
    serializer_class = UserNotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['notification_type', 'is_read']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Return only notifications for the current user."""
        return UserNotification.objects.filter(
            recipient=self.request.user
        ).select_related('recipient', 'content_type').order_by('-created_at')

    def get_serializer_class(self):
        """Use simplified serializer for list view."""
        if self.action == 'list':
            return UserNotificationListSerializer
        return UserNotificationSerializer

    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a notification as read.
        """
        notification = self.get_object()
        notification.mark_as_read()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """
        Mark all notifications as read for the current user.
        """
        from django.utils import timezone
        count = UserNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).update(is_read=True, read_at=timezone.now())
        return Response({
            'status': _('All notifications marked as read.'),
            'count': count
        })

    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """
        Get count of unread notifications for the current user.
        """
        count = UserNotification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return Response({'unread_count': count})
