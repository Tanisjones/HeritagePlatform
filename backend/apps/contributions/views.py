from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.heritage.models import HeritageItem
from apps.heritage.serializers import HeritageItemDetailSerializer, HeritageItemCreateUpdateSerializer, HeritageItemListSerializer
from apps.moderation.permissions import IsOwnerOrCurator


class MyContributionsViewSet(viewsets.ModelViewSet):
    """
    Contributor self-service endpoints for their own heritage item submissions.
    """

    permission_classes = [permissions.IsAuthenticated, IsOwnerOrCurator]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'heritage_type', 'heritage_category', 'parish']
    search_fields = ['title', 'description', 'address']
    ordering_fields = ['created_at', 'updated_at', 'submission_date', 'last_review_date']
    ordering = ['-created_at']

    def get_queryset(self):
        return (
            HeritageItem.objects.filter(contributor=self.request.user)
            .select_related('parish', 'heritage_type', 'heritage_category', 'curator')
            .prefetch_related('images', 'audio', 'video', 'documents')
        )

    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return HeritageItemCreateUpdateSerializer
        if self.action == 'retrieve':
            return HeritageItemDetailSerializer
        return HeritageItemListSerializer

    @action(detail=True, methods=['get'])
    def feedback(self, request, pk=None):
        item = self.get_object()
        quality = getattr(item, 'quality_score', None)
        return Response(
            {
                'status': item.status,
                'curator_feedback': item.curator_feedback,
                'quality_score': None if not quality else {
                    'completeness_score': quality.completeness_score,
                    'accuracy_score': quality.accuracy_score,
                    'media_quality_score': quality.media_quality_score,
                    'total_score': quality.total_score,
                    'notes': quality.notes,
                    'scored_at': quality.scored_at,
                },
            }
        )

    @action(detail=True, methods=['post'])
    def resubmit(self, request, pk=None):
        item = self.get_object()
        if item.status not in ['rejected', 'changes_requested']:
            return Response(
                {'error': 'Only rejected or changes-requested contributions can be resubmitted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        item.status = 'pending'
        item.curator_feedback = ''
        item.curator = None
        item.last_review_date = None
        item.save(update_fields=['status', 'curator_feedback', 'curator', 'last_review_date'])
        return Response({'status': 'resubmitted'})

