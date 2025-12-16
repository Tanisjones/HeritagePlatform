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

from .models import (
    LOMGeneral, LOMLifeCycle, LOMContributor, LOMEducational,
    LOMRights, LOMClassification, LOMRelation, EducationalResource, ResourceType, ResourceCategory
)
from .serializers import (
    LOMGeneralSerializer, LOMGeneralCreateSerializer,
    LOMLifeCycleSerializer, LOMContributorSerializer,
    LOMEducationalSerializer, LOMRightsSerializer,
    LOMClassificationSerializer, LOMRelationSerializer, LOMRelationCreateSerializer, EducationalResourceSerializer,
    ResourceTypeSerializer, ResourceCategorySerializer
)
from apps.moderation.permissions import IsTeacher
from apps.heritage.models import HeritageItem

from .scorm import build_scorm_12_pif_zip


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access to unauthenticated users
    and full access to authenticated users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class LOMGeneralViewSet(viewsets.ModelViewSet):
    """
    ViewSet for LOM General metadata.

    Provides CRUD operations for IEEE LOM metadata associated with heritage items.
    """
    queryset = LOMGeneral.objects.select_related(
        'heritage_item', 'lifecycle', 'educational', 'rights'
    ).prefetch_related('classifications', 'relations', 'lifecycle__contributors')
    permission_classes = [IsAuthenticatedOrReadOnly]
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
        if self.action in ['create', 'update', 'partial_update']:
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
    Teacher-only endpoint for downloading LOM "packages".
    Currently exposed as JSON exports of LOMGeneral + related metadata.
    """

    queryset = LOMGeneral.objects.select_related(
        'heritage_item', 'lifecycle', 'educational', 'rights'
    ).prefetch_related('classifications', 'lifecycle__contributors')
    serializer_class = LOMGeneralSerializer
    permission_classes = [permissions.AllowAny]
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


class SCORMPackageViewSet(viewsets.ViewSet):
    """Generate SCORM 1.2 packages for a single heritage item.

    This endpoint bundles all media (images, audio, video, documents) and embeds
    all available LOM data (JSON + a simple LOM XML) into the package.

    Route (via router): /api/v1/education/scorm-packages/{heritage_item_id}/download/
    """

    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        item = get_object_or_404(HeritageItem, pk=pk)

        lom = (
            LOMGeneral.objects.select_related('lifecycle', 'educational', 'rights')
            .prefetch_related('classifications', 'relations', 'lifecycle__contributors')
            .filter(heritage_item=item)
            .first()
        )
        lom_data = LOMGeneralSerializer(lom).data if lom else {}

        # Bundle all media attached to the heritage item.
        media_by_id = {}
        for qs in (item.images.all(), item.audio.all(), item.video.all(), item.documents.all()):
            for mf in qs:
                media_by_id[str(mf.id)] = mf
        media_files = list(media_by_id.values())

        zip_file, filename = build_scorm_12_pif_zip(
            title=item.title,
            description=item.description,
            lom_data=lom_data,
            media_files=media_files,
        )

        # Ensure Chrome/macOS get a usable filename and can validate the payload as a ZIP.
        # (Blob-based downloads sometimes ignore filenames; explicit headers help.)
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
