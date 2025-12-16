from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, UserRole
from .serializers import (
    UserSerializer, UserRegistrationSerializer, LoginSerializer,
    ChangePasswordSerializer, UserProfileSerializer,
    UserProfileUpdateSerializer, UserRoleSerializer
)


class UserRoleViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing user roles.
    Only reading is allowed - roles are managed by administrators.
    """
    queryset = UserRole.objects.all()
    serializer_class = UserRoleSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'


class UserViewSet(viewsets.GenericViewSet):
    """
    ViewSet for user authentication and profile management.

    Provides:
    - register: Create new user account
    - login: Authenticate and get JWT tokens
    - logout: Invalidate refresh token
    - me: Get/update current user profile
    - change_password: Change user password
    """
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]

    def get_serializer_class(self):
        """Return appropriate serializer class"""
        if self.action == 'register':
            return UserRegistrationSerializer
        elif self.action == 'login':
            return LoginSerializer
        elif self.action == 'change_password':
            return ChangePasswordSerializer
        elif self.action == 'me' and self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserSerializer

    def get_permissions(self):
        """Set permissions based on action"""
        if self.action in ['register', 'login']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['post'])
    def register(self, request):
        """
        Register a new user account.

        Returns user data and JWT tokens.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Return user data with tokens
        user_serializer = UserSerializer(user)
        return Response({
            'user': user_serializer.data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def login(self, request):
        """
        Authenticate user and return JWT tokens.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data['user']

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        # Return user data with tokens
        user_serializer = UserSerializer(user)
        return Response({
            'user': user_serializer.data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        })

    @action(detail=False, methods=['post'])
    def logout(self, request):
        """
        Logout user by blacklisting the refresh token.
        Requires 'rest_framework_simplejwt.token_blacklist' in INSTALLED_APPS.
        """
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': _('Refresh token is required.')},
                    status=status.HTTP_400_BAD_REQUEST
                )

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response(
                {'message': _('Successfully logged out.')},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get', 'put', 'patch'])
    def me(self, request):
        """
        Get or update current user profile.
        """
        if request.method == 'GET':
            serializer = UserSerializer(request.user)
            return Response(serializer.data)

        # Update profile
        profile = request.user.profile
        serializer = self.get_serializer(
            profile,
            data=request.data,
            partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Return updated user data
        user_serializer = UserSerializer(request.user)
        return Response(user_serializer.data)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """
        Change user password.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Set new password
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        return Response(
            {'message': _('Password changed successfully.')},
            status=status.HTTP_200_OK
        )

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Get user dashboard data with statistics.

        Returns:
        - User profile information
        - Gamification stats (points, level, badges)
        - Activity stats (contributions, annotations, etc.)
        - Recent notifications
        """
        user = request.user
        profile = user.profile

        # Get gamification data
        from apps.gamification.models import UserBadge
        total_points = profile.total_points
        current_level = profile.current_level
        badges_count = UserBadge.objects.filter(user=user).count()
        recent_badges = UserBadge.objects.filter(user=user).select_related(
            'badge'
        ).order_by('-earned_at')[:5]

        # Get activity statistics
        from apps.heritage.models import Contribution, Annotation
        contributions_count = Contribution.objects.filter(contributor=user).count()
        contributions_approved = Contribution.objects.filter(
            contributor=user,
            status='approved'
        ).count()
        annotations_count = Annotation.objects.filter(user=user).count()

        # Get recent notifications
        from apps.notifications.models import UserNotification
        unread_notifications = UserNotification.objects.filter(
            recipient=user,
            is_read=False
        ).count()
        recent_notifications = UserNotification.objects.filter(
            recipient=user
        ).order_by('-created_at')[:5]

        # Serialize badges
        from apps.gamification.serializers import UserBadgeSerializer
        badges_data = UserBadgeSerializer(recent_badges, many=True).data

        # Serialize notifications
        from apps.notifications.serializers import UserNotificationListSerializer
        notifications_data = UserNotificationListSerializer(
            recent_notifications,
            many=True
        ).data

        return Response({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.get_full_name(),
                'role': user.role.name if user.role else None,
            },
            'gamification': {
                'total_points': total_points,
                'current_level': {
                    'id': str(current_level.id) if current_level else None,
                    'name': current_level.name if current_level else None,
                    'level': current_level.level if current_level else 0,
                    'min_points': current_level.min_points if current_level else 0,
                    'max_points': current_level.max_points if current_level else 0,
                },
                'badges_count': badges_count,
                'recent_badges': badges_data,
            },
            'activity': {
                'contributions_total': contributions_count,
                'contributions_approved': contributions_approved,
                'annotations_total': annotations_count,
            },
            'notifications': {
                'unread_count': unread_notifications,
                'recent': notifications_data,
            }
        })
