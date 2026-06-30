from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend

from apps.moderation.permissions import IsCurator

from .models import AISuggestion
from .serializers import AISuggestionSerializer


class AISuggestionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only listing of AI suggestions plus approve/reject actions.

    Read-only on purpose: suggestions are created by the system (on contribution
    creation) and only ever transition via the approve/reject actions, so the
    create/update/destroy verbs are intentionally not exposed — that prevents a
    client from flipping `status` to 'approved' without actually applying the
    suggestion, or injecting arbitrary content.
    """
    serializer_class = AISuggestionSerializer
    permission_classes = [IsCurator]
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

        Atomic: the suggestion is only marked approved if applying it succeeds,
        so we never leave a suggestion in 'approved' state with the change not
        actually persisted.
        """
        suggestion = self.get_object()
        item = suggestion.heritage_item

        try:
            with transaction.atomic():
                if suggestion.suggestion_type == 'keyword':
                    self._apply_keywords(item, suggestion.content)
                elif suggestion.suggestion_type == 'historical_period':
                    self._apply_historical_period(item, suggestion.content)

                suggestion.status = 'approved'
                suggestion.reviewed_by = request.user
                suggestion.reviewed_at = timezone.now()
                suggestion.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        except ValueError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response({'status': _('Suggestion approved and applied.')})

    @staticmethod
    def _apply_historical_period(item, content):
        """Validate the AI value against the field's choices before applying."""
        valid = {value for value, _label in item._meta.get_field('historical_period').choices}
        if not isinstance(content, str) or content not in valid:
            raise ValueError(_('Suggested historical period is not a valid option.'))
        item.historical_period = content
        # Full save (no update_fields) so auto_now `updated_at` is refreshed too.
        item.save()

    @staticmethod
    def _apply_keywords(item, content):
        """Merge a list (or comma string) of keywords into the item's LOMGeneral."""
        from apps.education.models import LOMGeneral

        # get_or_create is atomic against the OneToOne(heritage_item) constraint,
        # so concurrent keyword approvals for a LOM-less item can't both create.
        lom, _created = LOMGeneral.objects.get_or_create(
            heritage_item=item,
            defaults={
                'title': item.title,
                'description': item.description or "",
                'language': 'es',
            },
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
        # Full save so modeltranslation syncs the language column and updated_at bumps.
        lom.save()

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        """
        Reject an AI suggestion.
        """
        suggestion = self.get_object()
        suggestion.status = 'rejected'
        suggestion.reviewed_by = request.user
        suggestion.reviewed_at = timezone.now()
        suggestion.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])
        return Response({'status': _('Suggestion rejected.')})
