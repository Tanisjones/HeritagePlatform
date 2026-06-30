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
        Approve an AI suggestion and apply it to the heritage item.
        """
        from django.utils import timezone

        suggestion = self.get_object()
        suggestion.status = 'approved'
        suggestion.reviewed_by = request.user
        suggestion.reviewed_at = timezone.now()
        suggestion.save()

        item = suggestion.heritage_item

        if suggestion.suggestion_type == 'keyword':
            # Keywords live on the LOM educational layer (LOMGeneral.keywords is a
            # comma-separated TextField), NOT on HeritageItem. Merge in the new
            # keywords, de-duplicated and order-preserving.
            self._apply_keywords(item, suggestion.content)
        elif suggestion.suggestion_type == 'historical_period':
            item.historical_period = suggestion.content
            item.save(update_fields=['historical_period'])

        return Response({'status': _('Suggestion approved and applied.')})

    @staticmethod
    def _apply_keywords(item, content):
        """Merge a list (or comma string) of keywords into the item's LOMGeneral."""
        from apps.education.models import LOMGeneral

        lom = LOMGeneral.objects.filter(heritage_item=item).first()
        if lom is None:
            # No LOM layer yet — create a minimal one so keywords have a home.
            lom = LOMGeneral.objects.create(
                heritage_item=item,
                title=item.title,
                description=item.description or "",
                language='es',
            )

        if isinstance(content, str):
            incoming = [k.strip() for k in content.split(',')]
        elif isinstance(content, (list, tuple)):
            incoming = [str(k).strip() for k in content]
        else:
            incoming = []

        existing = [k.strip() for k in (lom.keywords or '').split(',') if k.strip()]
        merged = list(existing)
        for kw in incoming:
            if kw and kw not in merged:
                merged.append(kw)

        lom.keywords = ', '.join(merged)
        lom.save(update_fields=['keywords'])

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject an AI suggestion.
        """
        from django.utils import timezone

        suggestion = self.get_object()
        suggestion.status = 'rejected'
        suggestion.reviewed_by = request.user
        suggestion.reviewed_at = timezone.now()
        suggestion.save()
        return Response({'status': _('Suggestion rejected.')})