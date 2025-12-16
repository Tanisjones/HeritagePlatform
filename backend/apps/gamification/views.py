from rest_framework import viewsets, permissions
from .models import Badge, Level, UserBadge, PointTransaction
from .serializers import BadgeSerializer, LevelSerializer, UserBadgeSerializer, PointTransactionSerializer

class BadgeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing badges.
    """
    queryset = Badge.objects.all().order_by('category', 'name')
    serializer_class = BadgeSerializer
    permission_classes = [permissions.AllowAny]

class LevelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing levels.
    """
    queryset = Level.objects.all().order_by('number')
    serializer_class = LevelSerializer
    permission_classes = [permissions.AllowAny]

class UserBadgeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing user badges.
    """
    serializer_class = UserBadgeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return UserBadge.objects.filter(user=self.request.user).select_related('user', 'badge').order_by('-earned_at')

class PointTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing point transactions.
    """
    serializer_class = PointTransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return PointTransaction.objects.filter(user=self.request.user).select_related('user').order_by('-created_at')