from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.conf import settings
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Q

from .models import (
    HeritageCategory, HeritageType, Parish, MediaFile,
    HeritageItem, HeritageRelation, Annotation
)
from .serializers import (
    HeritageCategorySerializer, HeritageTypeSerializer, ParishSerializer,
    MediaFileSerializer, MediaFileCreateSerializer,
    HeritageItemListSerializer, HeritageItemDetailSerializer,
    HeritageItemCreateUpdateSerializer, HeritageRelationSerializer,
    HeritageItemGeoJSONSerializer, HeritageItemContributionSerializer,
    AnnotationSerializer
)
from apps.cities.request import get_request_city, get_request_city_or_default
from apps.gamification.services import handle_contribution_created


def resolve_city_for_new_item(request, serializer):
    """City for a newly contributed heritage item: the explicit request city
    (?city=/X-City) wins; otherwise the submitted parish implies it (legacy
    clients without city context); otherwise the platform default city."""
    city = get_request_city(request)
    if city is not None:
        return city
    parish = serializer.validated_data.get('parish')
    if parish is not None and parish.city_id:
        return parish.city
    return get_request_city_or_default(request)
from apps.ai_services.services import get_ai_suggestions
from apps.ai_services.models import AISuggestion


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access to unauthenticated users
    and full access to authenticated users.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user and request.user.is_authenticated


class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Staff users (moderators) and curators can manage objects during moderation.
        profile = getattr(user, "profile", None)
        role = getattr(profile, "role", None)
        role_slug = getattr(role, "slug", None)
        if user.is_staff or role_slug == "curator":
            return True

        # Check if object has contributor field
        if hasattr(obj, 'contributor'):
            return obj.contributor == request.user
        if hasattr(obj, 'uploaded_by'):
            return obj.uploaded_by == request.user

        return False


class IsModeratorOrReadOnly(permissions.BasePermission):
    """
    Custom permission to allow read-only access to everyone, but only
    moderators/curators to edit.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if not user or not user.is_authenticated:
            return False

        # Staff users are moderators; curators are identified via profile.role.slug == "curator".
        profile = getattr(user, "profile", None)
        role = getattr(profile, "role", None)
        role_slug = getattr(role, "slug", None)
        return bool(user.is_staff or role_slug == "curator")


class HeritageCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing heritage categories.
    Provides list and detail views with hierarchical structure.
    """
    queryset = HeritageCategory.objects.filter(parent__isnull=True).order_by('order', 'name')
    serializer_class = HeritageCategorySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'

    @action(detail=False, methods=['get'])
    def all(self, request):
        """Get all categories including children"""
        categories = HeritageCategory.objects.all().order_by('order', 'name')
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class HeritageTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing heritage types (tangible/intangible).
    """
    queryset = HeritageType.objects.all()
    serializer_class = HeritageTypeSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


class ParishViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing parishes.
    """
    queryset = Parish.objects.all()
    serializer_class = ParishSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'canton']


class MediaFileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing media files.
    Allows upload and management of images, audio, and video.
    """
    queryset = MediaFile.objects.all()
    permission_classes = (
        [permissions.AllowAny]
        if settings.DEBUG
        else [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    )
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['file_type']
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def perform_create(self, serializer):
        serializer.save(uploaded_by=self.request.user if self.request.user.is_authenticated else None)

    def get_serializer_class(self):
        """Return appropriate serializer"""
        if self.action in ['create', 'update', 'partial_update']:
            return MediaFileCreateSerializer
        return MediaFileSerializer

    def get_queryset(self):
        """Filter to user's uploads if requested"""
        queryset = super().get_queryset()
        if self.request.query_params.get('my_uploads') == 'true':
            if self.request.user.is_authenticated:
                queryset = queryset.filter(uploaded_by=self.request.user)
        return queryset


class HeritageItemViewSet(viewsets.ModelViewSet):
    """
    ViewSet for heritage items (CDO - Composite Data Objects).

    Provides:
    - List and detail views with filtering
    - Create, update, delete operations
    - Nearby items search (geospatial)
    - GeoJSON export for maps
    - User contributions filtering
    """
    queryset = HeritageItem.objects.select_related(
        'heritage_type', 'heritage_category', 'parish', 'contributor'
    ).prefetch_related('images', 'audio', 'video', 'documents')
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly, IsModeratorOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'status': ['exact'],
        'heritage_type': ['exact'],
        'heritage_category': ['exact'],
        'parish': ['exact'],
        'historical_period': ['exact'],
    }
    search_fields = ['title', 'description', 'address']
    ordering_fields = ['created_at', 'updated_at', 'view_count', 'favorite_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Return appropriate serializer based on action"""
        if self.action == 'list':
            return HeritageItemListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return HeritageItemCreateUpdateSerializer
        elif self.action == 'geojson':
            return HeritageItemGeoJSONSerializer
        return HeritageItemDetailSerializer

    def perform_create(self, serializer):
        """Pin server-controlled fields on create: the creator is the contributor
        and new items enter the moderation queue as 'pending'. status/contributor
        are read-only on the write serializer, so they can't be spoofed from the
        request body; transitions out of 'pending' happen via moderation only.
        The city comes from the request context (?city=/X-City), never the body."""
        serializer.save(
            contributor=self.request.user if self.request.user.is_authenticated else None,
            status='pending',
            city=resolve_city_for_new_item(self.request, serializer),
        )

    def update(self, request, *args, **kwargs):
        # `status` is read-only on the write serializer (so ordinary users can't
        # self-publish). Status transitions are a staff/moderator action and are
        # applied here explicitly rather than through the serializer body.
        instance = self.get_object()
        new_status = request.data.get('status')
        if new_status is not None and new_status != instance.status:
            if not request.user.is_staff:
                return Response(
                    {'status': _('Only moderators can change the status of an item.')},
                    status=status.HTTP_403_FORBIDDEN,
                )
            instance.status = new_status
            instance.moderator = request.user
            if 'moderator_feedback' in request.data:
                instance.moderator_feedback = request.data['moderator_feedback']
            instance.save(update_fields=['status', 'moderator', 'moderator_feedback', 'updated_at'])
        return super().update(request, *args, **kwargs)

    def get_queryset(self):
        """
        Filter queryset based on query parameters.
        Non-authenticated users only see published items.
        """
        queryset = super().get_queryset()

        # Optional media presence filters (boolean query params)
        has_images = self.request.query_params.get('has_images')
        has_audio = self.request.query_params.get('has_audio')
        has_video = self.request.query_params.get('has_video')
        has_documents = self.request.query_params.get('has_documents')
        text_only = self.request.query_params.get('text_only')

        def is_true(v: str | None) -> bool:
            return str(v).lower() in ('1', 'true', 'yes', 'on')

        if any(map(is_true, [has_images, has_audio, has_video, has_documents, text_only])):
            queryset = queryset.annotate(
                images_count=Count('images', distinct=True),
                audio_count=Count('audio', distinct=True),
                video_count=Count('video', distinct=True),
                documents_count=Count('documents', distinct=True),
            )

        if is_true(has_images):
            queryset = queryset.filter(lom_general__educational__learning_resource_type__in=['image', 'figure', 'slide', 'diagram', 'graph'])
        if is_true(has_audio):
             queryset = queryset.filter(lom_general__educational__learning_resource_type='audio')
        if is_true(has_video):
             queryset = queryset.filter(lom_general__educational__learning_resource_type='video')
        if is_true(has_documents):
             queryset = queryset.filter(lom_general__educational__learning_resource_type__in=['document', 'table', 'report', 'questionnaire'])
        if is_true(text_only):
             queryset = queryset.filter(lom_general__educational__learning_resource_type='narrative_text')

        # Filter by status for non-authenticated users
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(status='published')
        elif not self.request.user.is_staff:
            # Authenticated users see published items + their own contributions
            queryset = queryset.filter(
                status='published'
            ) | queryset.filter(
                contributor=self.request.user,
                status__in=['draft', 'pending', 'rejected']
            )

        # Filter by user contributions
        if self.request.query_params.get('my_contributions') == 'true':
            if self.request.user.is_authenticated:
                queryset = queryset.filter(contributor=self.request.user)

        return queryset

    def retrieve(self, request, *args, **kwargs):
        """Increment view count when retrieving a heritage item"""
        instance = self.get_object()
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        Get heritage items near a specific location.

        Query params:
        - latitude: Latitude coordinate
        - longitude: Longitude coordinate
        - radius: Search radius in kilometers (default: 5)
        """
        try:
            latitude = float(request.query_params.get('latitude'))
            longitude = float(request.query_params.get('longitude'))
            radius = float(request.query_params.get('radius', 5))
        except (TypeError, ValueError):
            return Response(
                {'error': _('Invalid latitude, longitude, or radius parameters.')},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create point from coordinates
        point = Point(longitude, latitude, srid=4326)

        # Find items within radius
        queryset = self.get_queryset().filter(
            location__distance_lte=(point, D(km=radius))
        ).order_by('location')

        # Paginate results
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = HeritageItemListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)

        serializer = HeritageItemListSerializer(queryset, many=True, context={'request': request})
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def geojson(self, request):
        """
        Get heritage items as GeoJSON for map display.
        Applies same filters as list view.
        """
        queryset = self.filter_queryset(self.get_queryset())

        # Limit to 1000 items for performance
        queryset = queryset[:1000]

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def relations(self, request, pk=None):
        """Get all relations for a heritage item"""
        item = self.get_object()
        relations_from = HeritageRelation.objects.filter(from_item=item)
        relations_to = HeritageRelation.objects.filter(to_item=item)

        serializer = HeritageRelationSerializer(
            list(relations_from) + list(relations_to),
            many=True,
            context={'request': request}
        )
        return Response(serializer.data)


class ContributionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for citizen science contributions.
    Allows authenticated users to submit new heritage items.
    """
    queryset = HeritageItem.objects.all()
    serializer_class = HeritageItemContributionSerializer
    permission_classes = [permissions.AllowAny] if settings.DEBUG else [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """
        Set contributor to current user and status to 'pending'.
        Awards points for the contribution and generates AI suggestions.
        Creates initial LOM metadata.
        """
        from django.db import transaction
        from apps.education.models import LOMGeneral, LOMEducational, LOMLifeCycle

        # The wizard's optional "Capa educativa" payload was validated by the
        # contribution serializer (as a write-only nested field), so errors
        # already surfaced as 400 with an ``educational.<field>`` path. Pop it out
        # of validated_data before save() so it doesn't reach HeritageItem's
        # constructor; we attach it to the LOM below.
        edu_fields = dict(serializer.validated_data.pop('educational', None) or {})

        contributor = self.request.user if self.request.user.is_authenticated else None

        # Wrap the item + its LOM layer in one transaction so a failure part-way
        # doesn't leave a half-built record.
        with transaction.atomic():
            contribution = serializer.save(
                contributor=contributor,
                status='pending',
                city=resolve_city_for_new_item(self.request, serializer),
            )

            # 1. Create LOM General
            lom_general = LOMGeneral.objects.create(
                heritage_item=contribution,
                title=contribution.title,
                description=contribution.description or "",
                language='es',  # Default to Spanish
            )

            # 2. Create LOM Life Cycle
            LOMLifeCycle.objects.create(
                lom_general=lom_general,
                status='draft'  # Matches contribution pending/draft status
            )

            # 3. Determine Learning Resource Type (inferred from uploaded media).
            resource_type = 'narrative_text'
            if contribution.images.exists():
                resource_type = 'image'
            elif contribution.audio.exists():
                resource_type = 'audio'
            elif contribution.video.exists():
                resource_type = 'video'
            elif contribution.documents.exists():
                # Check if it's a narrative text
                first_doc = contribution.documents.first()
                if first_doc.mime_type == 'text/html' or first_doc.file.name.endswith('narrative_text.html'):
                    resource_type = 'narrative_text'
                else:
                    resource_type = 'document'

            # 4. Create LOM Educational. The inferred resource type only fills in
            # when the wizard left it blank, so an explicit contributor choice is
            # respected; everything else is the (pre-validated) wizard payload or
            # model defaults.
            edu_fields.setdefault('learning_resource_type', resource_type)
            LOMEducational.objects.create(
                lom_general=lom_general,
                **edu_fields,
            )

        handle_contribution_created(contribution)

        # Generate and save AI suggestions
        ai_suggestions = get_ai_suggestions(contribution)
        for suggestion in ai_suggestions:
            AISuggestion.objects.create(
                heritage_item=contribution,
                suggester=suggestion['suggester'],
                suggestion_type=suggestion['suggestion_type'],
                content=suggestion['content'],
                confidence=suggestion['confidence']
            )




class HeritageRelationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing relationships between heritage items.
    """
    queryset = HeritageRelation.objects.select_related('from_item', 'to_item')
    serializer_class = HeritageRelationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['relation_type', 'from_item', 'to_item']


class AnnotationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for community annotations on heritage items.
    Users can add, view, update, and delete their own annotations.
    """
    serializer_class = AnnotationSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['heritage_item', 'user']
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']

    def get_queryset(self):
        return Annotation.objects.select_related('user', 'heritage_item').order_by('-created_at')

    def perform_create(self, serializer):
        # Automatically award points for creating an annotation
        annotation = serializer.save(user=self.request.user)
        try:
            from apps.gamification.services import add_points
            add_points(
                self.request.user,
                10,  # Points for annotation
                "annotation_created",
                annotation
            )
        except Exception as e:
            # Log but don't fail the creation if gamification fails
            print(f"Gamification error: {e}")
