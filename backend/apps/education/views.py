"""
Views for education app (IEEE LOM metadata API endpoints).
"""

import json

from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import HttpResponse
from django.http import FileResponse
from django.utils.http import content_disposition_header
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters

from django.db.models import Prefetch

from .models import (
    LOMGeneral, LOMLifeCycle, LOMContributor, LOMEducational,
    LOMRights, LOMClassification, LOMRelation, AssessmentQuestion,
    EducationalResource, ResourceType, ResourceCategory,
    LessonPlan, LessonActivity
)
from .serializers import (
    LOMGeneralSerializer, LOMGeneralCreateSerializer, LOMGeneralWriteSerializer,
    LOMLifeCycleSerializer, LOMContributorSerializer,
    LOMEducationalSerializer, LOMRightsSerializer,
    LOMClassificationSerializer, LOMRelationSerializer, LOMRelationCreateSerializer,
    AssessmentQuestionSerializer, AssessmentQuestionPublicSerializer,
    EducationalResourceSerializer,
    ResourceTypeSerializer, ResourceCategorySerializer,
    LessonPlanSerializer, LessonPlanWriteSerializer
)
from apps.moderation.permissions import IsTeacher
from apps.heritage.models import HeritageItem
from apps.routes.models import HeritageRoute

from .scorm import (
    build_scorm_12_pif_zip, build_scorm_2004_pif_zip, build_cmi5_zip,
    build_collection_scorm_zip,
)
from .qti import build_qti_21_zip


def _role_slug(user):
    """Role slug ('curator'/'teacher'/…) for a user, or None. Mirrors moderation.permissions."""
    profile = getattr(user, "profile", None)
    role = getattr(profile, "role", None)
    return getattr(role, "slug", None)


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access to unauthenticated users
    and full access to authenticated users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class IsTeacherOrCuratorOrReadOnly(permissions.BasePermission):
    """Public reads; writes restricted to teachers, curators, or staff.

    Guards the LOM authoring surface (educational metadata + the AssessmentQuestion
    answer key). Plain authenticated users (tourists/contributors) must NOT be able
    to create or overwrite a learning object's questions/answers — mirrors the
    frontend's canEditLom gate (curator || teacher || is_staff).
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return bool(
            user and user.is_authenticated
            and (user.is_staff or _role_slug(user) in ('teacher', 'curator'))
        )


class LOMGeneralViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LOM General metadata.

    Provides CRUD operations for IEEE LOM metadata associated with heritage items.
    """
    queryset = LOMGeneral.objects.select_related(
        'heritage_item', 'lifecycle', 'educational', 'rights'
    ).prefetch_related('classifications', 'relations', 'questions', 'lifecycle__contributors')
    # Writes author the educational layer incl. the quiz answer key — teacher/
    # curator/staff only (a tourist must not be able to rewrite answers).
    permission_classes = [IsTeacherOrCuratorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'language': ['exact'],
        'structure': ['exact'],
        'aggregation_level': ['exact'],
        'heritage_item': ['exact'],
    }
    search_fields = ['title', 'description', 'keywords']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action in ['update', 'partial_update']:
            # Writable nested serializer: edit the whole LOM layer in one PATCH.
            return LOMGeneralWriteSerializer
        if self.action == 'create':
            return LOMGeneralCreateSerializer
        return LOMGeneralSerializer

    @action(detail=False, methods=['get'])
    def by_heritage_item(self, request):
        """
        Get LOM metadata for a specific heritage item.

        Query params:
        - heritage_item_id: UUID of the heritage item
        """
        heritage_item_id = request.query_params.get('heritage_item_id')
        if not heritage_item_id:
            return Response(
                {'error': 'heritage_item_id parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            lom = self.get_queryset().get(heritage_item_id=heritage_item_id)
            serializer = self.get_serializer(lom)
            return Response(serializer.data)
        except LOMGeneral.DoesNotExist:
            return Response(
                {'error': 'LOM metadata not found for this heritage item'},
                status=status.HTTP_404_NOT_FOUND
            )


class LOMLifeCycleViewSet(viewsets.ModelViewSet):
    """ViewSet for LOM Life Cycle metadata."""
    queryset = LOMLifeCycle.objects.select_related('lom_general').prefetch_related('contributors')
    serializer_class = LOMLifeCycleSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'lom_general']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']


class LOMContributorViewSet(viewsets.ModelViewSet):
    """ViewSet for LOM Contributors."""
    queryset = LOMContributor.objects.select_related('lifecycle__lom_general')
    serializer_class = LOMContributorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'lifecycle']
    search_fields = ['entity']
    ordering_fields = ['date']
    ordering = ['-date']


class LOMEducationalViewSet(viewsets.ModelViewSet):
    """ViewSet for LOM Educational metadata."""
    queryset = LOMEducational.objects.select_related('lom_general')
    serializer_class = LOMEducationalSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = [
        'learning_resource_type', 'interactivity_type', 'context',
        'intended_end_user_role', 'difficulty', 'lom_general'
    ]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']


class LOMRightsViewSet(viewsets.ModelViewSet):
    """ViewSet for LOM Rights metadata."""
    queryset = LOMRights.objects.select_related('lom_general')
    serializer_class = LOMRightsSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['cost', 'copyright_and_other_restrictions', 'lom_general']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']


class LOMClassificationViewSet(viewsets.ModelViewSet):
    """ViewSet for LOM Classifications."""
    queryset = LOMClassification.objects.select_related('lom_general')
    serializer_class = LOMClassificationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['purpose', 'lom_general']
    search_fields = ['taxon_source', 'taxon_entry', 'keywords']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class LOMRelationViewSet(viewsets.ModelViewSet):
    """ViewSet for LOM Relations (LOM section 7)."""

    queryset = LOMRelation.objects.select_related(
        'lom_general', 'target_heritage_item', 'target_media_file'
    )
    serializer_class = LOMRelationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['kind', 'lom_general', 'target_heritage_item', 'target_media_file']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return LOMRelationCreateSerializer
        return LOMRelationSerializer


class ResourceTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing resource types.
    """
    queryset = ResourceType.objects.all()
    serializer_class = ResourceTypeSerializer
    permission_classes = [permissions.AllowAny]


class ResourceCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing resource categories.
    """
    queryset = ResourceCategory.objects.all()
    serializer_class = ResourceCategorySerializer
    permission_classes = [permissions.AllowAny]


class EducationalResourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing educational resources.
    """
    queryset = EducationalResource.objects.all()
    serializer_class = EducationalResourceSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['resource_type', 'category']
    search_fields = ['title', 'description', 'content']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-created_at']


class LOMPackageViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Endpoint for downloading LOM "packages" (JSON exports of LOMGeneral +
    related metadata).

    Listing/reading is public so the ``/learn`` catalogue works for anonymous
    visitors, but downloading a package requires authentication (removing the
    old "teacher-only" claim that was contradicted by ``AllowAny``).
    """

    queryset = LOMGeneral.objects.select_related(
        'heritage_item', 'lifecycle', 'educational', 'rights'
    ).prefetch_related('classifications', 'relations', 'questions', 'lifecycle__contributors')
    serializer_class = LOMGeneralSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_permissions(self):
        # Downloading a package is an authenticated action; browsing is public.
        if self.action == 'download':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['language', 'structure', 'aggregation_level']
    ordering_fields = ['created_at', 'updated_at', 'title']
    ordering = ['-updated_at']

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        lom = self.get_object()
        data = self.get_serializer(lom).data
        filename = f"lom-package-{str(lom.id)[:8]}.json"
        response = HttpResponse(
            content=json.dumps(data, ensure_ascii=False),
            content_type="application/json",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


# Maximum number of items that may be bundled into a single collection package.
MAX_COLLECTION_ITEMS = 50

# Single-item package formats keyed by ?format= query param.
_SINGLE_ITEM_BUILDERS = {
    'scorm12': build_scorm_12_pif_zip,
    'scorm2004': build_scorm_2004_pif_zip,
    'cmi5': build_cmi5_zip,
}


def _gather_item_media(item):
    """Return a de-duplicated list of every MediaFile attached to a heritage item."""
    media_by_id = {}
    for qs in (item.images.all(), item.audio.all(), item.video.all(), item.documents.all()):
        for mf in qs:
            media_by_id[str(mf.id)] = mf
    return list(media_by_id.values())


def _lom_data_for_item(item):
    """Serialize the item's LOMGeneral (or {} when it has none)."""
    lom = (
        LOMGeneral.objects.select_related('lifecycle', 'educational', 'rights')
        .prefetch_related('classifications', 'relations', 'questions', 'lifecycle__contributors')
        .filter(heritage_item=item)
        .first()
    )
    return LOMGeneralSerializer(lom).data if lom else {}


def _zip_file_response(zip_file, filename):
    """Wrap a file-like zip in a FileResponse with the download headers used
    across the SCORM/cmi5/QTI endpoints (attachment name + nosniff + length)."""
    try:
        zip_file.seek(0, 2)
        size = zip_file.tell()
        zip_file.seek(0)
    except Exception:
        size = None

    response = FileResponse(zip_file, content_type='application/zip')
    response['Content-Disposition'] = content_disposition_header(as_attachment=True, filename=filename)
    if size is not None:
        response['Content-Length'] = str(size)
    response['X-Content-Type-Options'] = 'nosniff'
    return response


class SCORMPackageViewSet(viewsets.ViewSet):
    """Generate a learning package for a single heritage item.

    Bundles all media (images, audio, video, documents) and embeds all available
    LOM data (JSON + valid IEEE LOM XML) into the package. The ``?variant=`` query
    param selects the packaging profile: ``scorm12`` (default), ``scorm2004`` or
    ``cmi5``.

    NB: the param is ``variant``, NOT ``format`` — ``format`` is reserved by DRF
    content negotiation, and an unrecognised value there yields a 404 before the
    view runs.

    Route (via router): /api/v1/education/scorm-packages/{heritage_item_id}/download/?variant=scorm12

    Downloading requires authentication; the ``/learn`` catalogue itself stays
    public.
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        item = get_object_or_404(HeritageItem, pk=pk)

        variant = request.query_params.get('variant', 'scorm12')
        builder = _SINGLE_ITEM_BUILDERS.get(variant)
        if builder is None:
            return Response(
                {'error': f"Unknown variant '{variant}'. Use one of: {', '.join(_SINGLE_ITEM_BUILDERS)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lom_data = _lom_data_for_item(item)
        media_files = _gather_item_media(item)

        zip_file, filename = builder(
            title=item.title,
            description=item.description,
            lom_data=lom_data,
            media_files=media_files,
        )
        return _zip_file_response(zip_file, filename)


class AssessmentQuestionViewSet(viewsets.ModelViewSet):
    """CRUD for assessment/quiz questions attached to a learning object.

    Browsing is public (so quizzes render in the ``/learn`` catalogue) BUT
    anonymous readers get an answer-key-free serializer — the ``correct`` flags
    and ``correct_response`` are only visible to authenticated users. Writing
    requires authentication. A QTI 2.1 export (which embeds the answer key) is
    available to authenticated users at
    ``/api/v1/lom-questions/export-qti/?lom_general=<uuid>``.
    """

    queryset = AssessmentQuestion.objects.select_related('lom_general')
    serializer_class = AssessmentQuestionSerializer
    # Answer-key writes are teacher/curator/staff only (see IsTeacherOrCuratorOrReadOnly).
    permission_classes = [IsTeacherOrCuratorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['lom_general', 'question_type']
    ordering_fields = ['order', 'created_at', 'updated_at']
    ordering = ['order']

    def get_serializer_class(self):
        # Anonymous reads must not leak the answer key; authenticated users
        # (curators/teachers authoring) get the full serializer.
        user = getattr(self.request, 'user', None)
        if not (user and user.is_authenticated):
            return AssessmentQuestionPublicSerializer
        return AssessmentQuestionSerializer

    def get_permissions(self):
        # The QTI package embeds correct answers, so require auth for export.
        if self.action == 'export_qti':
            return [permissions.IsAuthenticated()]
        return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='export-qti')
    def export_qti(self, request):
        """Export a learning object's questions as an IMS QTI 2.1 package.

        Query param: ``lom_general`` (UUID) — required. Requires authentication
        because the package contains the answer key.
        """
        lom_general_id = request.query_params.get('lom_general')
        if not lom_general_id:
            return Response(
                {'error': 'lom_general query parameter is required'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lom = get_object_or_404(LOMGeneral, pk=lom_general_id)
        questions = list(lom.questions.all())
        if not questions:
            return Response(
                {'error': 'This learning object has no questions to export'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        zip_file, filename = build_qti_21_zip(
            title=lom.title,
            questions=questions,
            identifier=str(lom.id),
        )
        return _zip_file_response(zip_file, filename)


class RoutePackageViewSet(viewsets.ViewSet):
    """Generate a collection learning package for a whole heritage route.

    Loads the route, walks its ordered stops, and bundles each stop's heritage
    item (with its LOM + media) into ONE package titled after the route. The
    ``?variant=`` query param selects ``scorm12`` (default) or ``scorm2004``.

    cmi5 is intentionally NOT accepted here: a cmi5 *collection* isn't modelled,
    and silently downgrading it to SCORM 2004 would hand the user a mislabelled
    file. Callers wanting cmi5 should export single items.

    NB: the param is ``variant``, NOT ``format`` — ``format`` is reserved by DRF
    content negotiation (an unknown value there 404s before the view runs).

    Route (via router): /api/v1/education/route-packages/{route_id}/download/?variant=scorm12
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        route = get_object_or_404(HeritageRoute, pk=pk)

        variant = request.query_params.get('variant', 'scorm12')
        if variant not in ('scorm12', 'scorm2004'):
            return Response(
                {'error': (
                    f"Unsupported route package variant '{variant}'. "
                    "Route packages support: scorm12, scorm2004."
                )},
                status=status.HTTP_400_BAD_REQUEST,
            )
        package_format = variant

        entries = []
        for stop in route.stops.order_by('order').select_related('heritage_item'):
            item = stop.heritage_item
            if item is None:
                continue
            entries.append({
                'heritage_item': item,
                'lom_data': _lom_data_for_item(item),
                'media_files': _gather_item_media(item),
            })

        if not entries:
            return Response(
                {'error': 'This route has no stops to package'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        zip_file, filename = build_collection_scorm_zip(
            title=route.title,
            description=route.description,
            entries=entries,
            package_format=package_format,
        )
        return _zip_file_response(zip_file, filename)


class CollectionPackageViewSet(viewsets.ViewSet):
    """Export an arbitrary set of heritage items as ONE collection package.

    Route (via router): /api/v1/education/collection-packages/download/?ids=<uuid>,<uuid>&variant=scorm12

    ``ids`` is a comma-separated list of HeritageItem UUIDs (max
    ``MAX_COLLECTION_ITEMS``). ``variant`` is ``scorm12`` (default) or
    ``scorm2004``. Requires authentication.

    NB: the param is ``variant``, NOT ``format`` — ``format`` is reserved by DRF
    content negotiation (an unknown value there 404s before the view runs).
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def download(self, request):
        raw_ids = request.query_params.get('ids', '')
        ids = [i.strip() for i in raw_ids.split(',') if i.strip()]

        if not ids:
            return Response(
                {'error': 'ids query parameter is required (comma-separated HeritageItem UUIDs)'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if len(ids) > MAX_COLLECTION_ITEMS:
            return Response(
                {'error': f'Too many items requested ({len(ids)}); maximum is {MAX_COLLECTION_ITEMS}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        variant = request.query_params.get('variant', 'scorm12')
        if variant not in ('scorm12', 'scorm2004'):
            return Response(
                {'error': f"Unknown variant '{variant}'. Use one of: scorm12, scorm2004."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Preserve the caller's ordering; skip ids that don't resolve.
        items_by_id = {str(i.id): i for i in HeritageItem.objects.filter(id__in=ids)}
        entries = []
        for item_id in ids:
            item = items_by_id.get(item_id)
            if item is None:
                continue
            entries.append({
                'heritage_item': item,
                'lom_data': _lom_data_for_item(item),
                'media_files': _gather_item_media(item),
            })

        if not entries:
            return Response(
                {'error': 'None of the requested ids matched a heritage item'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        zip_file, filename = build_collection_scorm_zip(
            title='Heritage Collection',
            description=f'Collection of {len(entries)} heritage items',
            entries=entries,
            package_format=variant,
        )
        return _zip_file_response(zip_file, filename)


class LessonPlanViewSet(viewsets.ModelViewSet):
    """
    Structured lesson plans (pedagogical authoring · Pilar P).

    Reads: published + public plans are visible to everyone; an author sees their
    own plans in any state; curators/staff see all. Writes: teachers/staff only,
    and a plan is edited by its author (or a curator).
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['subject', 'grade_level', 'status', 'related_route']
    search_fields = ['title', 'summary', 'subject']
    ordering_fields = ['updated_at', 'created_at', 'title']
    ordering = ['-updated_at']

    def get_serializer_class(self):
        if self.action in ('create', 'update', 'partial_update'):
            return LessonPlanWriteSerializer
        return LessonPlanSerializer

    def get_permissions(self):
        # Reading is open (list/retrieve filtered by visibility). Exporting a
        # package is available to any authenticated user (matches the other
        # /education/*-packages exports). Everything else (create/update/state
        # transitions/duplicate) is teacher-gated.
        if self.action in ('list', 'retrieve'):
            return [permissions.AllowAny()]
        if self.action == 'export_scorm':
            return [permissions.IsAuthenticated()]
        return [IsTeacher()]

    def get_queryset(self):
        # Prefetch activities WITH their bound content so the serializer's
        # heritage_item_title / route_title / educational_resource_title reads don't
        # trigger a query per activity (N+1 on every list/retrieve).
        activities_qs = LessonActivity.objects.select_related(
            'heritage_item', 'route', 'educational_resource'
        )
        qs = LessonPlan.objects.all().prefetch_related(
            Prefetch('activities', queryset=activities_qs)
        )
        user = self.request.user
        if user and user.is_authenticated and (user.is_staff or _role_slug(user) == 'curator'):
            return qs
        published_public = qs.filter(
            status=LessonPlan.STATUS_PUBLISHED, visibility=LessonPlan.VISIBILITY_PUBLIC
        )
        if user and user.is_authenticated:
            # Own plans (any state) OR published-public.
            return (qs.filter(author=user) | published_public).distinct()
        return published_public

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _require_owner_or_curator(self, plan):
        user = self.request.user
        if user.is_staff or _role_slug(user) == 'curator' or plan.author_id == user.id:
            return
        from rest_framework.exceptions import PermissionDenied
        raise PermissionDenied('You can only edit your own lesson plans.')

    def perform_update(self, serializer):
        self._require_owner_or_curator(serializer.instance)
        serializer.save()

    def perform_destroy(self, instance):
        self._require_owner_or_curator(instance)
        instance.delete()

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """Clone a plan (and its activities) as a fresh draft owned by the caller."""
        source = self.get_object()
        clone = LessonPlan.objects.create(
            title=f"{source.title} (copy)",
            summary=source.summary,
            objectives=list(source.objectives or []),
            subject=source.subject,
            grade_level=source.grade_level,
            audience=source.audience,
            curriculum_alignment=source.curriculum_alignment,
            pedagogical_approach=source.pedagogical_approach,
            estimated_total_minutes=source.estimated_total_minutes,
            related_route=source.related_route,
            status=LessonPlan.STATUS_DRAFT,
            visibility=LessonPlan.VISIBILITY_PRIVATE,
            author=request.user,
        )
        for activity in source.activities.all():
            activity.pk = None
            activity.id = None
            activity.lesson = clone
            activity.save()
        return Response(LessonPlanSerializer(clone, context={'request': request}).data,
                        status=status.HTTP_201_CREATED)

    # ---- state machine: draft → review → published → archived --------------
    #
    # submit (draft/changes → review), publish (review/draft → published),
    # archive (any → archived). Only the owner or a curator/staff may transition;
    # publishing is additionally restricted to curators/staff (a teacher submits,
    # a curator publishes) and requires at least one activity.

    # Allowed source states per transition — the state machine is directional
    # (draft → review → published → archived), with sensible back-edges. Anything
    # not listed is rejected with 409, so a published plan can't jump back to review
    # nor an archived plan re-publish out of order.
    _ALLOWED_SOURCES = {
        LessonPlan.STATUS_REVIEW: {LessonPlan.STATUS_DRAFT},
        LessonPlan.STATUS_PUBLISHED: {LessonPlan.STATUS_DRAFT, LessonPlan.STATUS_REVIEW},
        LessonPlan.STATUS_ARCHIVED: {
            LessonPlan.STATUS_DRAFT, LessonPlan.STATUS_REVIEW, LessonPlan.STATUS_PUBLISHED,
        },
    }

    def _transition(self, request, *, to_status, require_curator=False, require_activities=False):
        plan = self.get_object()
        self._require_owner_or_curator(plan)
        user = request.user
        is_curator = user.is_staff or _role_slug(user) == 'curator'
        if require_curator and not is_curator:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('Only a curator can publish a lesson plan.')
        # Source-state guard: reject out-of-order transitions (e.g. published→review).
        if plan.status not in self._ALLOWED_SOURCES.get(to_status, set()):
            return Response(
                {'detail': f"Cannot move a '{plan.status}' plan to '{to_status}'."},
                status=status.HTTP_409_CONFLICT,
            )
        if require_activities and not plan.activities.exists():
            return Response(
                {'detail': 'A lesson plan needs at least one activity before it can be published.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        update_fields = ['status', 'updated_at']
        plan.status = to_status
        # Publishing makes the plan publicly visible; without this a default-private
        # plan would be "published" yet still 404 on the public detail route.
        if to_status == LessonPlan.STATUS_PUBLISHED and plan.visibility == LessonPlan.VISIBILITY_PRIVATE:
            plan.visibility = LessonPlan.VISIBILITY_PUBLIC
            update_fields.append('visibility')
        plan.save(update_fields=update_fields)
        return Response(LessonPlanSerializer(plan, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        """Owner sends a draft for review (draft → review)."""
        return self._transition(request, to_status=LessonPlan.STATUS_REVIEW)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        """Curator publishes a plan (draft/review → published); requires ≥1 activity
        and makes a private plan public."""
        return self._transition(
            request, to_status=LessonPlan.STATUS_PUBLISHED,
            require_curator=True, require_activities=True,
        )

    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Retire a plan (any non-archived state → archived)."""
        return self._transition(request, to_status=LessonPlan.STATUS_ARCHIVED)

    @action(detail=True, methods=['get'], url_path='export-scorm')
    def export_scorm(self, request, pk=None):
        """Bundle the heritage items referenced by this plan's activities into ONE
        SCORM collection package titled after the plan.

        ``?variant=scorm12|scorm2004`` (default scorm12). Only activities that link
        a heritage_item contribute content; the activity ORDER is preserved. A plan
        with no linked items → 400 (nothing to package).
        """
        plan = self.get_object()

        variant = request.query_params.get('variant', 'scorm12')
        if variant not in ('scorm12', 'scorm2004'):
            return Response(
                {'error': f"Unknown variant '{variant}'. Use one of: scorm12, scorm2004."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entries = []
        seen_item_ids = set()
        for activity in plan.activities.order_by('order').select_related('heritage_item'):
            item = activity.heritage_item
            if item is None or item.id in seen_item_ids:
                continue
            seen_item_ids.add(item.id)
            entries.append({
                'heritage_item': item,
                'lom_data': _lom_data_for_item(item),
                'media_files': _gather_item_media(item),
            })

        if not entries:
            return Response(
                {'error': 'This lesson plan has no activities linked to heritage items to package.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        zip_file, filename = build_collection_scorm_zip(
            title=plan.title,
            description=plan.summary or '',
            entries=entries,
            package_format=variant,
        )
        return _zip_file_response(zip_file, filename)
