from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.gis.db.models import GeometryField
from django.contrib.gis.geos import Point
from django.db.models import Q, F, Count, Avg
from django.db.models.functions import Cast
from django.http import HttpResponse
from django.utils import timezone
from django.utils.http import content_disposition_header
from django_filters.rest_framework import DjangoFilterBackend

from apps.cities.models import CityRole
from apps.cities.request import get_request_city, get_request_city_or_default
from apps.users.permissions import IsCurator, user_city_ids
from .exports import build_gpx, build_kml, slugify_filename, GPX_CONTENT_TYPE, KML_CONTENT_TYPE
from .models import HeritageRoute, RouteStop, UserRouteProgress, RouteRating, RouteTheme
from .routing import haversine_m
from .serializers import (
    RouteListSerializer,
    RouteDetailSerializer,
    RouteCreateSerializer,
    UserRouteProgressSerializer,
    RouteRatingSerializer,
    RouteThemeSerializer,
)


class RouteViewSet(viewsets.ModelViewSet):
    """
    ViewSet for heritage routes with full CRUD and governance.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = [
        'difficulty', 'theme', 'is_official', 'wheelchair_accessible',
        'best_season', 'creator', 'status'
    ]
    search_fields = ['title', 'description', 'theme']
    ordering_fields = [
        'created_at', 'difficulty', 'distance', 'estimated_duration',
        'view_count', 'completion_count', 'average_rating'
    ]
    ordering = ['-created_at']

    def _visibility_filter(self, qs):
        """Restrict routes by the requesting user's role."""
        user = self.request.user
        if not user.is_authenticated:
            return qs.filter(status='published')
        if not user.is_staff:
            # Authenticated users see published + own routes (incl. their archived
            # ones, which are hidden from the public listing).
            visible = (
                Q(status='published') |
                Q(creator=user,
                  status__in=['draft', 'pending', 'rejected', 'changes_requested', 'archived'])
            )
            # City curators additionally see every state in THEIR cities (they
            # review pending routes — the approve/reject actions need this).
            curator_cities = user_city_ids(user, CityRole.ROLE_CURATOR)
            if curator_cities:
                visible = visible | Q(city_id__in=curator_cities)
            return qs.filter(visible)
        return qs

    def _city_filter(self, qs):
        """Multi-city scope: filter by the request city when one is set."""
        city = get_request_city(self.request)
        if city is not None:
            qs = qs.filter(city=city)
        return qs

    # Actions rendered by the lightweight RouteListSerializer (stop COUNT only).
    _LIST_ACTIONS = {'list', 'my_routes', 'active_routes', 'nearby', 'similar'}

    def get_queryset(self):
        """
        Full queryset for detail/write (prefetch stops + their media). List-style
        actions get the lightweight queryset instead (no stops→media prefetch).
        """
        if getattr(self, 'action', None) in self._LIST_ACTIONS:
            return self.list_queryset()
        qs = HeritageRoute.objects.select_related(
            'creator', 'curator', 'city'
        ).prefetch_related(
            'stops__heritage_item',
            'stops__heritage_item__images',
            # audio backs RouteStopSerializer.audio_url; without this it's an N+1.
            'stops__heritage_item__audio',
        )
        # No city filter here: detail/write must work for deep links to any
        # city's route regardless of the visitor's active city header.
        return self._visibility_filter(qs)

    def list_queryset(self):
        """
        Lightweight queryset for list-style endpoints (list/my/active/nearby/
        similar) served by RouteListSerializer, which only needs a stop COUNT —
        so the heavy stops→heritage_item→media prefetch is skipped.
        """
        qs = HeritageRoute.objects.select_related('creator', 'curator', 'city')
        return self._city_filter(self._visibility_filter(qs))

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return RouteListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RouteCreateSerializer
        return RouteDetailSerializer

    def perform_create(self, serializer):
        """Set creator and request-context city when creating a route."""
        serializer.save(
            creator=self.request.user,
            status='draft',
            city=get_request_city_or_default(self.request),
        )

    def retrieve(self, request, *args, **kwargs):
        """Retrieve route and increment view count."""
        instance = self.get_object()
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # Governance actions
    @action(detail=True, methods=['post'], permission_classes=[IsCurator])
    def approve(self, request, pk=None):
        """Curator approves route."""
        route = self.get_object()
        route.status = 'published'
        route.curator = request.user
        route.last_review_date = timezone.now()
        if not route.submission_date:
            route.submission_date = route.created_at
        route.save(update_fields=['status', 'curator', 'last_review_date', 'submission_date'])

        # Send notification to creator
        self._notify_creator(route, 'route_approved', 'Route approved',
                           'Your route has been approved and published.')

        return Response({'status': 'approved'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsCurator])
    def reject(self, request, pk=None):
        """Curator rejects route."""
        route = self.get_object()
        feedback = request.data.get('feedback', '')
        route.status = 'rejected'
        route.curator = request.user
        route.curator_feedback = feedback
        route.last_review_date = timezone.now()
        route.save(update_fields=['status', 'curator', 'curator_feedback', 'last_review_date'])

        self._notify_creator(route, 'route_rejected', 'Route rejected',
                           feedback or 'Your route was rejected.')

        return Response({'status': 'rejected'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], permission_classes=[IsCurator], url_path='request-changes')
    def request_changes(self, request, pk=None):
        """Curator requests changes to route."""
        route = self.get_object()
        feedback = request.data.get('feedback', '')
        route.status = 'changes_requested'
        route.curator = request.user
        route.curator_feedback = feedback
        route.last_review_date = timezone.now()
        route.save(update_fields=['status', 'curator', 'curator_feedback', 'last_review_date'])

        self._notify_creator(route, 'changes_requested', 'Changes requested',
                           feedback or 'A curator requested changes to your route.')

        return Response({'status': 'changes_requested'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def submit_for_review(self, request, pk=None):
        """Creator submits route for review."""
        route = self.get_object()

        # Check permission
        if route.creator != request.user:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        if route.status not in ['draft', 'changes_requested']:
            return Response(
                {'error': 'Route must be in draft or changes_requested status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        route.status = 'pending'
        route.submission_date = timezone.now()
        route.curator_feedback = ''  # Clear previous feedback
        route.save(update_fields=['status', 'submission_date', 'curator_feedback'])

        return Response({'status': 'pending'}, status=status.HTTP_200_OK)

    # Progress tracking actions
    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """Start a route (create UserRouteProgress)."""
        route = self.get_object()

        # Check if route is published
        if route.status != 'published':
            return Response(
                {'error': 'Route must be published to start'},
                status=status.HTTP_400_BAD_REQUEST
            )

        progress, created = UserRouteProgress.objects.get_or_create(
            user=request.user,
            route=route
        )

        if not created and progress.completed_at:
            # Reset if previously completed
            progress.completed_at = None
            progress.current_stop = None
            progress.visited_stops.clear()
            progress.save()
            created = True

        if not created:
            return Response(
                {'error': 'Route already started'},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = UserRouteProgressSerializer(progress, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='check-in')
    def check_in(self, request, pk=None):
        """Check in at a specific stop."""
        route = self.get_object()
        stop_id = request.data.get('stop_id')

        if not stop_id:
            return Response(
                {'error': 'stop_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            progress = UserRouteProgress.objects.get(user=request.user, route=route)
        except UserRouteProgress.DoesNotExist:
            return Response(
                {'error': 'Route not started'},
                status=status.HTTP_404_NOT_FOUND
            )

        if progress.completed_at:
            return Response(
                {'error': 'Route already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            stop = RouteStop.objects.get(id=stop_id, route=route)
        except RouteStop.DoesNotExist:
            return Response(
                {'error': 'Invalid stop'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Optional geolocation: validate proximity to the stop but never reject —
        # a manual check-in is always allowed; being far just returns a warning.
        proximity = self._check_in_proximity(request, stop)

        progress.current_stop = stop
        progress.visited_stops.add(stop)
        progress.save(update_fields=['current_stop'])

        serializer = UserRouteProgressSerializer(progress, context={'request': request})
        payload = serializer.data
        if proximity is not None:
            payload = {**payload, **proximity}
        return Response(payload, status=status.HTTP_200_OK)

    @staticmethod
    def _check_in_proximity(request, stop):
        """
        If the request carries latitude/longitude, return a dict describing how
        far the user is from the stop (and a 'far_from_stop' warning past the
        configured radius). Returns None when no coordinates were sent.
        """
        lat = request.data.get('latitude')
        lng = request.data.get('longitude')
        if lat is None or lng is None:
            return None
        try:
            lat = float(lat)
            lng = float(lng)
        except (TypeError, ValueError):
            return None

        location = getattr(stop.heritage_item, 'location', None)
        if location is None:
            return None

        distance_m = haversine_m((lng, lat), (float(location.x), float(location.y)))
        from django.conf import settings
        radius = float(getattr(settings, 'ROUTE_CHECKIN_RADIUS_M', 100))
        result = {'distance_m': round(distance_m, 1)}
        if distance_m > radius:
            result['warning'] = 'far_from_stop'
        return result

    @action(detail=True, methods=['post'], url_path='skip-stop')
    def skip_stop(self, request, pk=None):
        """Skip a stop but mark as visited."""
        route = self.get_object()
        stop_id = request.data.get('stop_id')

        if not stop_id:
            return Response(
                {'error': 'stop_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            progress = UserRouteProgress.objects.get(user=request.user, route=route)
            stop = RouteStop.objects.get(id=stop_id, route=route)
        except UserRouteProgress.DoesNotExist:
            return Response(
                {'error': 'Route not started'},
                status=status.HTTP_404_NOT_FOUND
            )
        except RouteStop.DoesNotExist:
            return Response(
                {'error': 'Invalid stop'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Mark as visited
        progress.visited_stops.add(stop)

        # Move to next stop
        next_stop = route.stops.filter(order__gt=stop.order).order_by('order').first()
        if next_stop:
            progress.current_stop = next_stop
            progress.save(update_fields=['current_stop'])

        serializer = UserRouteProgressSerializer(progress, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """Complete a route."""
        route = self.get_object()

        try:
            progress = UserRouteProgress.objects.get(user=request.user, route=route)
        except UserRouteProgress.DoesNotExist:
            return Response(
                {'error': 'Route not started'},
                status=status.HTTP_404_NOT_FOUND
            )

        if progress.completed_at:
            return Response(
                {'error': 'Route already completed'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Snapshot points/badges BEFORE the save so we can report exactly what the
        # completion awarded. Gamification is granted synchronously by the
        # post_save signal on UserRouteProgress (apps.gamification.signals /
        # services.handle_route_completed) when completed_at is set below.
        points_before, badges_before = self._award_snapshot(request.user)

        progress.completed_at = timezone.now()
        progress.save(update_fields=['completed_at'])

        # Update route statistics
        route.completion_count = F('completion_count') + 1
        route.save(update_fields=['completion_count'])
        route.refresh_from_db(fields=['completion_count'])

        points_after, badges_after = self._award_snapshot(request.user)
        new_badge_names = [b.name for bid, b in badges_after.items() if bid not in badges_before]

        serializer = UserRouteProgressSerializer(progress, context={'request': request})
        payload = dict(serializer.data)
        payload['awards'] = {
            'points': max(0, points_after - points_before),
            'badges': new_badge_names,
        }
        return Response(payload, status=status.HTTP_200_OK)

    @staticmethod
    def _award_snapshot(user):
        """
        Return (total_points, {badge_id: Badge}) for the user, read FRESH from the
        DB. Uses the authoritative profile.points total (updated atomically by
        add_points), so the completion delta is exact — not a transaction-window
        heuristic. Reads fresh (not the request user's cached relations) because the
        award happens between the two snapshots via the post_save signal.
        """
        from apps.gamification.models import UserBadge
        from apps.users.models import UserProfile

        points = (
            UserProfile.objects.filter(user=user)
            .values_list('points', flat=True)
            .first()
        ) or 0
        badges = {
            ub.badge_id: ub.badge
            for ub in UserBadge.objects.filter(user=user).select_related('badge')
        }
        return points, badges

    # Custom views
    @action(detail=False, methods=['get'], url_path='my-routes')
    def my_routes(self, request):
        """Routes created by current user."""
        queryset = self.get_queryset().filter(creator=request.user)
        page = self.paginate_queryset(queryset)
        serializer = RouteListSerializer(
            page if page else queryset,
            many=True,
            context={'request': request}
        )
        if page:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=False, methods=['get'], url_path='active-routes')
    def active_routes(self, request):
        """Routes user is currently exploring."""
        progress_ids = UserRouteProgress.objects.filter(
            user=request.user,
            completed_at__isnull=True
        ).values_list('route_id', flat=True)

        queryset = self.get_queryset().filter(id__in=progress_ids)
        page = self.paginate_queryset(queryset)
        serializer = RouteListSerializer(
            page if page else queryset,
            many=True,
            context={'request': request}
        )
        if page:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    # Geospatial discovery
    @action(detail=False, methods=['get'])
    def nearby(self, request):
        """
        Published routes near a location.

        Query params: latitude, longitude, radius (km, default 5). A route
        matches if its path passes within the radius, or (when it has no path
        yet) if any of its stops is within the radius.
        """
        try:
            latitude = float(request.query_params.get('latitude'))
            longitude = float(request.query_params.get('longitude'))
            radius = float(request.query_params.get('radius', 5))
        except (TypeError, ValueError):
            return Response(
                {'error': 'Invalid latitude, longitude, or radius parameters.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        point = Point(longitude, latitude, srid=4326)
        radius_m = radius * 1000.0
        base = self.list_queryset().filter(status='published')
        # Cast the 4326 geometry COLUMNS to geography so ST_DWithin measures the
        # radius in METRES (a plain geometry distance on 4326 is in degrees). A
        # route matches if its path passes within the radius, or (no path yet) if
        # any of its stops does.
        near = (
            base.annotate(
                path_geog=Cast('path', GeometryField(geography=True)),
                stop_geog=Cast('stops__heritage_item__location', GeometryField(geography=True)),
            )
            .filter(
                Q(path__isnull=False, path_geog__dwithin=(point, radius_m))
                | Q(path__isnull=True, stop_geog__dwithin=(point, radius_m))
            )
            .distinct()
        )

        page = self.paginate_queryset(near)
        serializer = RouteListSerializer(
            page if page is not None else near, many=True, context={'request': request}
        )
        if page is not None:
            return self.get_paginated_response(serializer.data)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def similar(self, request, pk=None):
        """Up to 6 published routes sharing this one's theme or its stops."""
        route = self.get_object()
        item_ids = list(route.stops.values_list('heritage_item_id', flat=True))
        candidates = self.list_queryset().filter(status='published').exclude(pk=route.pk)

        # Select candidates by theme OR overlapping stops via a subquery (so the
        # main queryset isn't inner-joined on stops); then count overlap with
        # distinct=True so the join multiplication doesn't inflate `shared`.
        overlap_ids = []
        if item_ids:
            overlap_ids = list(
                RouteStop.objects.filter(heritage_item_id__in=item_ids)
                .values_list('route_id', flat=True)
                .distinct()
            )

        selector = Q()
        # Prefer the curated theme category (robust); fall back to the legacy
        # free-text theme for routes not yet categorized.
        if route.theme_category_id:
            selector |= Q(theme_category_id=route.theme_category_id)
        elif route.theme:
            selector |= Q(theme__iexact=route.theme)
        if overlap_ids:
            selector |= Q(pk__in=overlap_ids)
        if not selector:
            return Response([])

        similar = (
            candidates.filter(selector)
            .annotate(
                shared=Count(
                    'stops',
                    filter=Q(stops__heritage_item_id__in=item_ids),
                    distinct=True,
                )
            )
            .order_by('-shared', '-average_rating', '-completion_count')[:6]
        )
        serializer = RouteListSerializer(similar, many=True, context={'request': request})
        return Response(serializer.data)

    # Export
    @action(detail=True, methods=['get'], url_path='export-gpx')
    def export_gpx(self, request, pk=None):
        """Download the route as a GPX 1.1 file (waypoints + track)."""
        route = self.get_object()
        return self._xml_download(build_gpx(route), GPX_CONTENT_TYPE, route, 'gpx')

    @action(detail=True, methods=['get'], url_path='export-kml')
    def export_kml(self, request, pk=None):
        """Download the route as a KML 2.2 file (placemarks + line)."""
        route = self.get_object()
        return self._xml_download(build_kml(route), KML_CONTENT_TYPE, route, 'kml')

    @staticmethod
    def _xml_download(xml, content_type, route, ext):
        """Wrap an XML string in an attachment response (mirrors education downloads)."""
        filename = f"{slugify_filename(route.title)}.{ext}"
        response = HttpResponse(xml, content_type=content_type)
        response['Content-Disposition'] = content_disposition_header(
            as_attachment=True, filename=filename
        )
        response['X-Content-Type-Options'] = 'nosniff'
        return response

    # Governance: archive
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive a published or rejected route (creator or staff)."""
        route = self.get_object()

        if route.creator != request.user and not request.user.is_staff:
            return Response({'error': 'Not authorized'}, status=status.HTTP_403_FORBIDDEN)

        if route.status not in ['published', 'rejected']:
            return Response(
                {'error': 'Only published or rejected routes can be archived'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        route.status = 'archived'
        route.last_review_date = timezone.now()
        route.save(update_fields=['status', 'last_review_date'])

        self._notify_creator(route, 'route_archived', 'Route archived',
                             'Your route has been archived.')

        return Response({'status': 'archived'}, status=status.HTTP_200_OK)

    # Rating
    @action(detail=True, methods=['get', 'post'], url_path='rate')
    def rate(self, request, pk=None):
        """Get or submit rating for a route."""
        route = self.get_object()

        if request.method == 'GET':
            rating = route.ratings.filter(user=request.user).first()
            if not rating:
                return Response({}, status=status.HTTP_204_NO_CONTENT)
            return Response(RouteRatingSerializer(rating, context={'request': request}).data)

        # POST - submit rating
        serializer = RouteRatingSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        rating, created = RouteRating.objects.update_or_create(
            route=route,
            user=request.user,
            defaults={
                'rating': serializer.validated_data['rating'],
                'comment': serializer.validated_data.get('comment', '')
            }
        )

        # Update average rating
        avg_rating = route.ratings.aggregate(Avg('rating'))['rating__avg']
        route.average_rating = avg_rating
        route.save(update_fields=['average_rating'])

        return Response(
            RouteRatingSerializer(rating, context={'request': request}).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def _notify_creator(self, route, notification_type, title, message):
        """Helper to send notification to route creator."""
        if not route.creator:
            return

        try:
            from apps.notifications.models import UserNotification
            UserNotification.objects.create(
                recipient=route.creator,
                notification_type=notification_type,
                title=title,
                message=message,
                content_object=route
            )
        except Exception:
            pass  # Fail silently if notifications not available


class UserRouteProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing user route progress.
    """
    serializer_class = UserRouteProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Return progress for current user only."""
        return (
            UserRouteProgress.objects.filter(user=self.request.user)
            .select_related('route', 'current_stop__heritage_item')
            .prefetch_related(
                'visited_stops__heritage_item',
                # audio backs RouteStopSerializer.audio_url on visited/current stops.
                'visited_stops__heritage_item__audio',
                'current_stop__heritage_item__audio',
            )
            .order_by('-started_at')
        )


class RouteThemeViewSet(viewsets.ReadOnlyModelViewSet):
    """Curated route themes (H.2) for the route-builder selector and discovery.

    Read-only + public: the vocabulary is seeded/managed in the admin, not authored
    through the API.
    """
    queryset = RouteTheme.objects.all()
    serializer_class = RouteThemeSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None
