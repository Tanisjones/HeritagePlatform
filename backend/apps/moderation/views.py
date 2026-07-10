from django.db.models import Count, F, Q
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.cities.models import CityRole
from apps.cities.request import get_request_city
from apps.users.permissions import user_city_ids
from apps.heritage.models import HeritageItem
from apps.notifications.models import UserNotification
from apps.gamification.services import handle_contribution_approved, reward_moderation_review

from .models import ContributionFlag, ContributionVersion, CuratorNote, QualityScore, ReviewChecklist, ReviewChecklistResponse
from .permissions import IsCurator
from .serializers import (
    ContributionFlagSerializer,
    ContributionVersionSerializer,
    CuratorNoteSerializer,
    CuratorQueueItemSerializer,
    CuratorReviewDetailSerializer,
    QualityScoreSerializer,
    ReviewChecklistResponseSerializer,
    ReviewChecklistSerializer,
)


class ModerationViewSet(viewsets.ModelViewSet):
    """
    Curator queue + review endpoints for HeritageItem contributions.
    """

    permission_classes = [IsCurator]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'heritage_type', 'heritage_category', 'parish', 'curator', 'city']
    search_fields = ['title', 'description', 'address']
    ordering_fields = ['created_at', 'updated_at', 'submission_date', 'priority']
    ordering = ['submission_date', 'created_at']

    def get_queryset(self):
        qs = (
            HeritageItem.objects.select_related(
                'contributor',
                'curator',
                'parish',
                'heritage_type',
                'heritage_category',
                'city',
            )
            .prefetch_related('images', 'audio', 'video', 'documents')
        )
        qs = self._scope_to_governed_cities(qs)
        if self.action == 'list':
            qs = self._scope_to_request_city(qs)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            return qs
        return qs.filter(status__in=['pending', 'changes_requested']).order_by('priority', 'submission_date', 'created_at')

    def _scope_to_governed_cities(self, qs):
        """Authorization: a non-staff curator only ever sees items in cities
        where they hold the role. Applies to every action, detail included."""
        user = self.request.user
        if user.is_authenticated and not user.is_staff:
            qs = qs.filter(city_id__in=user_city_ids(user, CityRole.ROLE_CURATOR))
        return qs

    def _scope_to_request_city(self, qs):
        """Queue presentation: narrow to the active request city when one is set.

        List-only. Applying this to detail actions would 404 a cross-city item a
        multi-city curator legitimately governs, since the active city travels on
        every request regardless of which item is open.
        """
        city = get_request_city(self.request)
        if city is not None:
            qs = qs.filter(city=city)
        return qs

    def get_serializer_class(self):
        if self.action == 'list':
            return CuratorQueueItemSerializer
        if self.action == 'retrieve':
            return CuratorReviewDetailSerializer
        if self.action in ['score']:
            return QualityScoreSerializer
        if self.action in ['flag', 'flags', 'resolve_flag']:
            return ContributionFlagSerializer
        if self.action in ['checklists', 'checklist']:
            return ReviewChecklistSerializer
        if self.action in ['checklist_response']:
            return ReviewChecklistResponseSerializer
        if self.action in ['notes']:
            return CuratorNoteSerializer
        if self.action in ['versions']:
            return ContributionVersionSerializer
        return CuratorReviewDetailSerializer

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        qs = qs.annotate(
            flags_open=Count('flags', filter=Q(flags__status__in=['open', 'under_review']), distinct=True),
            total_score=F('quality_score__total_score'),
        )
        page = self.paginate_queryset(qs)
        serializer = self.get_serializer(page if page is not None else qs, many=True)
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    def _notify(self, item: HeritageItem, notification_type: str, title: str, message: str):
        if not item.contributor_id:
            return
        UserNotification.objects.create(
            recipient_id=item.contributor_id,
            notification_type=notification_type,
            title=title,
            message=message,
            content_object=item,
        )

    def _create_version(self, item: HeritageItem, created_by, created_by_type: str, summary: str = ''):
        from django.core.serializers.json import DjangoJSONEncoder
        import json
        
        data = CuratorReviewDetailSerializer(item, context={'request': self.request}).data
        # Ensure UUIDs and other types are serialized to JSON-compatible format
        snapshot = json.loads(json.dumps(data, cls=DjangoJSONEncoder))

        ContributionVersion.objects.create(
            heritage_item=item,
            created_by=created_by if getattr(created_by, 'is_authenticated', False) else None,
            created_by_type=created_by_type,
            data_snapshot=snapshot,
            changes_summary=summary,
        )

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        item = self.get_object()

        # Handle Quality Score
        quality_score_data = request.data.get('quality_score')
        if quality_score_data:
            serializer = QualityScoreSerializer(data=quality_score_data)
            serializer.is_valid(raise_exception=True)
            QualityScore.objects.update_or_create(
                heritage_item=item,
                defaults={
                    'completeness_score': serializer.validated_data['completeness_score'],
                    'accuracy_score': serializer.validated_data['accuracy_score'],
                    'media_quality_score': serializer.validated_data['media_quality_score'],
                    'notes': serializer.validated_data.get('notes', ''),
                    'scored_by': request.user,
                },
            )

        # Handle Checklist Responses
        checklist_responses = request.data.get('checklist_responses')
        if checklist_responses and isinstance(checklist_responses, list):
             for entry in checklist_responses:
                serializer = ReviewChecklistResponseSerializer(data=entry)
                serializer.is_valid(raise_exception=True)
                ReviewChecklistResponse.objects.update_or_create(
                    heritage_item=item,
                    checklist_item=serializer.validated_data['checklist_item'],
                    curator=request.user,
                    defaults={
                        'is_checked': serializer.validated_data.get('is_checked', False),
                        'notes': serializer.validated_data.get('notes', ''),
                    },
                )

        item.status = 'published'
        item.curator = request.user
        item.last_review_date = timezone.now()
        if not item.submission_date:
            item.submission_date = item.created_at
        item.save(update_fields=['status', 'curator', 'last_review_date', 'submission_date'])

        handle_contribution_approved(item, moderator=request.user)
        self._create_version(item, request.user, 'curator', 'Approved')
        self._notify(item, 'contribution_approved', 'Contribution approved', 'Your contribution was approved and published.')
        return Response({'status': 'approved'})

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        item = self.get_object()
        feedback = request.data.get('feedback', '') or request.data.get('curator_feedback', '')
        item.status = 'rejected'
        item.curator = request.user
        item.curator_feedback = feedback
        item.last_review_date = timezone.now()
        item.save(update_fields=['status', 'curator', 'curator_feedback', 'last_review_date'])

        reward_moderation_review(request.user, item)
        self._create_version(item, request.user, 'curator', 'Rejected')
        self._notify(item, 'contribution_rejected', 'Contribution rejected', feedback or 'Your contribution was rejected.')
        return Response({'status': 'rejected'})

    @action(detail=True, methods=['post'], url_path='request-changes')
    def request_changes(self, request, pk=None):
        item = self.get_object()
        feedback = request.data.get('feedback', '') or request.data.get('curator_feedback', '')
        item.status = 'changes_requested'
        item.curator = request.user
        item.curator_feedback = feedback
        item.last_review_date = timezone.now()
        item.save(update_fields=['status', 'curator', 'curator_feedback', 'last_review_date'])

        self._create_version(item, request.user, 'curator', 'Changes requested')
        self._notify(item, 'changes_requested', 'Changes requested', feedback or 'A curator requested changes to your contribution.')
        return Response({'status': 'changes_requested'})

    @action(detail=True, methods=['get', 'post'])
    def score(self, request, pk=None):
        item = self.get_object()
        if request.method == 'GET':
            score = getattr(item, 'quality_score', None)
            if not score:
                return Response({}, status=status.HTTP_204_NO_CONTENT)
            return Response(QualityScoreSerializer(score).data)

        serializer = QualityScoreSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        score, _ = QualityScore.objects.update_or_create(
            heritage_item=item,
            defaults={
                'completeness_score': serializer.validated_data['completeness_score'],
                'accuracy_score': serializer.validated_data['accuracy_score'],
                'media_quality_score': serializer.validated_data['media_quality_score'],
                'notes': serializer.validated_data.get('notes', ''),
                'scored_by': request.user,
            },
        )
        self._create_version(item, request.user, 'curator', 'Quality scored')
        return Response(QualityScoreSerializer(score).data)

    @action(detail=True, methods=['post'])
    def flag(self, request, pk=None):
        item = self.get_object()
        serializer = ContributionFlagSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        flag = ContributionFlag.objects.create(
            heritage_item=item,
            flag_type=serializer.validated_data['flag_type'],
            status=serializer.validated_data.get('status', 'open'),
            reason=serializer.validated_data.get('reason', ''),
            flagged_by=request.user,
        )
        self._create_version(item, request.user, 'curator', f"Flagged: {flag.flag_type}")
        self._notify(item, 'contribution_flagged', 'Contribution flagged', 'Your contribution was flagged for review.')
        return Response(ContributionFlagSerializer(flag).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def flags(self, request, pk=None):
        item = self.get_object()
        flags_qs = item.flags.all().order_by('-created_at')
        return Response(ContributionFlagSerializer(flags_qs, many=True).data)

    @action(detail=False, methods=['patch'], url_path=r'flags/(?P<flag_id>[^/.]+)/resolve')
    def resolve_flag(self, request, flag_id=None):
        try:
            flag = ContributionFlag.objects.get(id=flag_id)
        except ContributionFlag.DoesNotExist:
            return Response({'error': 'Flag not found'}, status=status.HTTP_404_NOT_FOUND)
        flag.status = request.data.get('status', 'resolved')
        flag.resolution_notes = request.data.get('resolution_notes', '')
        flag.resolved_by = request.user
        flag.resolved_at = timezone.now()
        flag.save(update_fields=['status', 'resolution_notes', 'resolved_by', 'resolved_at', 'updated_at'])
        return Response(ContributionFlagSerializer(flag).data)

    @action(detail=False, methods=['get'])
    def checklists(self, request):
        qs = ReviewChecklist.objects.filter(is_active=True).order_by('id').prefetch_related('items')
        return Response(ReviewChecklistSerializer(qs, many=True).data)

    @action(detail=True, methods=['get'])
    def checklist(self, request, pk=None):
        item = self.get_object()
        qs = ReviewChecklist.objects.filter(is_active=True).prefetch_related('items')
        checklist = (
            qs.filter(applicable_to_types=item.heritage_type).first()
            or qs.filter(applicable_to_categories=item.heritage_category).first()
            or qs.first()
        )
        if not checklist:
            return Response({}, status=status.HTTP_204_NO_CONTENT)
        return Response(ReviewChecklistSerializer(checklist).data)

    @action(detail=True, methods=['post'], url_path='checklist-response')
    def checklist_response(self, request, pk=None):
        item = self.get_object()
        responses = request.data.get('responses')
        if not isinstance(responses, list):
            return Response({'error': 'responses must be a list'}, status=status.HTTP_400_BAD_REQUEST)

        saved = []
        for entry in responses:
            serializer = ReviewChecklistResponseSerializer(data=entry)
            serializer.is_valid(raise_exception=True)
            resp, _ = ReviewChecklistResponse.objects.update_or_create(
                heritage_item=item,
                checklist_item=serializer.validated_data['checklist_item'],
                curator=request.user,
                defaults={
                    'is_checked': serializer.validated_data.get('is_checked', False),
                    'notes': serializer.validated_data.get('notes', ''),
                },
            )
            saved.append(resp)

        self._create_version(item, request.user, 'curator', 'Checklist updated')
        return Response(ReviewChecklistResponseSerializer(saved, many=True).data)

    @action(detail=True, methods=['get', 'post'])
    def notes(self, request, pk=None):
        item = self.get_object()
        if request.method == 'GET':
            qs = item.curator_notes.all().order_by('-is_pinned', '-created_at')
            return Response(CuratorNoteSerializer(qs, many=True).data)

        serializer = CuratorNoteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = CuratorNote.objects.create(
            heritage_item=item,
            curator=request.user,
            content=serializer.validated_data['content'],
            is_pinned=serializer.validated_data.get('is_pinned', False),
        )
        self._create_version(item, request.user, 'curator', 'Curator note added')
        return Response(CuratorNoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def versions(self, request, pk=None):
        item = self.get_object()
        qs = item.versions.all().order_by('-version_number')
        return Response(ContributionVersionSerializer(qs, many=True).data)

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """D2 — claim an item ("asignarme"): records curator=me so other
        curators can see it's being handled. Re-claiming is allowed — the last
        curator to claim wins (small teams coordinate socially, not via locks)."""
        item = self.get_object()
        item.curator = request.user
        item.save(update_fields=['curator', 'updated_at'])
        return Response({'status': 'assigned', 'curator_email': request.user.email})

    BULK_MAX_ITEMS = 50

    @action(detail=False, methods=['post'])
    def bulk(self, request):
        """D2 — bulk approve/reject: {ids: [...], decision: approve|reject,
        feedback: ''}. Applies the same state change + notifications as the
        per-item actions but skips scoring/checklists (that's the point of
        bulk). Items outside the curator's cities or not in a moderatable
        status are skipped and reported, never failed."""
        ids = request.data.get('ids')
        decision = request.data.get('decision')
        feedback = request.data.get('feedback', '') or ''

        if decision not in ('approve', 'reject'):
            return Response({'error': 'decision must be "approve" or "reject".'}, status=status.HTTP_400_BAD_REQUEST)
        if not isinstance(ids, list) or not ids:
            return Response({'error': 'ids must be a non-empty list.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(ids) > self.BULK_MAX_ITEMS:
            return Response(
                {'error': f'At most {self.BULK_MAX_ITEMS} items per bulk call.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Governed-cities scope only: a selection made in all-cities mode must stay
        # actionable after the curator switches the active city.
        items = self._scope_to_governed_cities(
            HeritageItem.objects.filter(id__in=ids, status__in=['pending', 'changes_requested'])
        )

        processed = []
        for item in items:
            if decision == 'approve':
                item.status = 'published'
                item.curator = request.user
                item.last_review_date = timezone.now()
                if not item.submission_date:
                    item.submission_date = item.created_at
                item.save(update_fields=['status', 'curator', 'last_review_date', 'submission_date'])
                handle_contribution_approved(item, moderator=request.user)
                self._create_version(item, request.user, 'curator', 'Approved (bulk)')
                self._notify(item, 'contribution_approved', 'Contribution approved', 'Your contribution was approved and published.')
            else:
                item.status = 'rejected'
                item.curator = request.user
                item.curator_feedback = feedback
                item.last_review_date = timezone.now()
                item.save(update_fields=['status', 'curator', 'curator_feedback', 'last_review_date'])
                reward_moderation_review(request.user, item)
                self._create_version(item, request.user, 'curator', 'Rejected (bulk)')
                self._notify(item, 'contribution_rejected', 'Contribution rejected', feedback or 'Your contribution was rejected.')
            processed.append(str(item.id))

        skipped = [str(i) for i in ids if str(i) not in processed]
        return Response({'decision': decision, 'processed': processed, 'skipped': skipped})

    @action(detail=False, methods=['get'])
    def stats(self, request):
        qs = self._scope_to_request_city(
            self._scope_to_governed_cities(HeritageItem.objects.all())
        )
        flags = ContributionFlag.objects.filter(status__in=['open', 'under_review'])
        city = get_request_city(request)
        if city is not None:
            flags = flags.filter(heritage_item__city=city)

        # D1 — per-city workload breakdown across ALL the cities this curator
        # governs (staff: every city), regardless of the request-city scope:
        # that scope answers "what am I looking at", this answers "where else
        # is work piling up".
        user = request.user
        breakdown_qs = HeritageItem.objects.filter(status__in=['pending', 'changes_requested'])
        if not user.is_staff:
            breakdown_qs = breakdown_qs.filter(city_id__in=user_city_ids(user, CityRole.ROLE_CURATOR))
        breakdown = (
            breakdown_qs.values('city__slug', 'city__name')
            .annotate(
                pending=Count('id', filter=Q(status='pending')),
                changes_requested=Count('id', filter=Q(status='changes_requested')),
            )
            .order_by('city__name')
        )

        return Response(
            {
                'pending': qs.filter(status='pending').count(),
                'changes_requested': qs.filter(status='changes_requested').count(),
                'flagged_open': flags.count(),
                'reviewed_total': qs.filter(status__in=['published', 'rejected']).count(),
                'cities': [
                    {
                        'slug': row['city__slug'],
                        'name': row['city__name'],
                        'pending': row['pending'],
                        'changes_requested': row['changes_requested'],
                    }
                    for row in breakdown
                ],
            }
        )


class ReviewChecklistViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only access to active review checklists for curators.
    """

    permission_classes = [IsCurator]
    serializer_class = ReviewChecklistSerializer
    queryset = ReviewChecklist.objects.filter(is_active=True).prefetch_related('items').order_by('id')


class ContributionFlagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Curator flag management endpoints.
    """

    permission_classes = [IsCurator]
    serializer_class = ContributionFlagSerializer
    queryset = ContributionFlag.objects.select_related('heritage_item').order_by('-created_at')
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'flag_type']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['patch'], url_path='resolve')
    def resolve(self, request, pk=None):
        flag = self.get_object()
        flag.status = request.data.get('status', 'resolved')
        flag.resolution_notes = request.data.get('resolution_notes', '')
        flag.resolved_by = request.user
        flag.resolved_at = timezone.now()
        flag.save(update_fields=['status', 'resolution_notes', 'resolved_by', 'resolved_at', 'updated_at'])
        return Response(self.get_serializer(flag).data)
