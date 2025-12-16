from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from .models import AISuggestion
from .serializers import AISuggestionSerializer

class IsModerator(permissions.BasePermission):
    """
    Custom permission to only allow moderators to access the view.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_staff

class AISuggestionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing AI suggestions.
    """
    serializer_class = AISuggestionSerializer
    permission_classes = [IsModerator]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'suggestion_type', 'suggester']
    ordering_fields = ['created_at', 'confidence']
    ordering = ['-created_at']

    def get_queryset(self):
        return AISuggestion.objects.all().select_related(
            'heritage_item',
            'reviewed_by'
        ).order_by('-created_at')

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        """
        Approve an AI suggestion.
        """
        suggestion = self.get_object()
        suggestion.status = 'approved'
        suggestion.reviewed_by = request.user
        suggestion.save()
        
        # Apply the suggestion to the heritage item
        # This is a simplified example. A real implementation would be more robust.
        if suggestion.suggestion_type == 'keyword':
            suggestion.heritage_item.keywords.add(*suggestion.content)
        elif suggestion.suggestion_type == 'historical_period':
            suggestion.heritage_item.historical_period = suggestion.content
            
        suggestion.heritage_item.save()

        return Response({'status': _('Suggestion approved and applied.')})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject an AI suggestion.
        """
        suggestion = self.get_object()
        suggestion.status = 'rejected'
        suggestion.reviewed_by = request.user
        suggestion.save()
        return Response({'status': _('Suggestion rejected.')})