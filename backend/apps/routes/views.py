from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q, F, Count, Avg
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend

from .models import HeritageRoute, RouteStop, UserRouteProgress, RouteRating
from .serializers import (
    RouteListSerializer,
    RouteDetailSerializer,
    RouteCreateSerializer,
    UserRouteProgressSerializer,
    RouteRatingSerializer
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

    def get_queryset(self):
        """Filter queryset based on user authentication and role."""
        qs = HeritageRoute.objects.select_related(
            'creator', 'curator'
        ).prefetch_related(
            'stops__heritage_item',
            'stops__heritage_item__images'
        )

        # Filter by status for non-authenticated users
        if not self.request.user.is_authenticated:
            qs = qs.filter(status='published')
        elif not self.request.user.is_staff:
            # Authenticated users see published + own routes
            qs = qs.filter(
                Q(status='published') |
                Q(creator=self.request.user, status__in=['draft', 'pending', 'rejected', 'changes_requested'])
            )

        return qs

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return RouteListSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RouteCreateSerializer
        return RouteDetailSerializer

    def perform_create(self, serializer):
        """Set creator when creating a route."""
        serializer.save(creator=self.request.user, status='draft')

    def retrieve(self, request, *args, **kwargs):
        """Retrieve route and increment view count."""
        instance = self.get_object()
        instance.increment_view_count()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # Governance actions
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
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

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser], url_path='request-changes')
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

        progress.current_stop = stop
        progress.visited_stops.add(stop)
        progress.save(update_fields=['current_stop'])

        serializer = UserRouteProgressSerializer(progress, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

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

        progress.completed_at = timezone.now()
        progress.save(update_fields=['completed_at'])

        # Update route statistics
        route.completion_count = F('completion_count') + 1
        route.save(update_fields=['completion_count'])
        route.refresh_from_db(fields=['completion_count'])

        # TODO: Award gamification points (future phase)
        # from apps.gamification.services import add_points
        # add_points(request.user, 30, "Route completed", route, unique_reference=True)

        serializer = UserRouteProgressSerializer(progress, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

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
        return UserRouteProgress.objects.filter(
            user=self.request.user
        ).select_related('route', 'current_stop').prefetch_related('visited_stops').order_by('-started_at')
