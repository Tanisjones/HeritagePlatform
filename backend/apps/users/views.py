from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.utils.translation import gettext_lazy as _

from apps.gamification.models import Level, UserBadge
from apps.gamification.serializers import UserBadgeSerializer
from apps.heritage.models import Annotation, HeritageItem
from apps.notifications.models import UserNotification
from apps.notifications.serializers import UserNotificationListSerializer

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

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """
        Aggregate the current user's profile, gamification and activity stats.

        Contribution counts come from HeritageItem: the old contributions.Contribution
        model was folded into HeritageItem's status machine, so a "contribution" is an
        item the user authored, and an approved one is a published item.
        """
        user = request.user
        profile = user.profile

        level = Level.objects.filter(number=profile.level).first()
        badges = (
            UserBadge.objects.filter(user=user)
            .select_related('badge')
            .order_by('-earned_at')
        )
        recent_badges = badges[:5]

        authored = HeritageItem.objects.filter(contributor=user)
        notifications = UserNotification.objects.filter(recipient=user)
        recent_notifications = notifications.order_by('-created_at')[:5]

        return Response({
            'user': {
                'id': str(user.id),
                'email': user.email,
                'full_name': user.get_full_name(),
                'role': profile.role.name if profile.role else None,
            },
            'gamification': {
                'total_points': profile.points,
                'current_level': {
                    'id': str(level.id) if level else None,
                    'name': level.name if level else None,
                    'level': profile.level,
                    'min_points': level.min_points if level else 0,
                    'max_points': level.max_points if level else 0,
                },
                'badges_count': badges.count(),
                'recent_badges': UserBadgeSerializer(recent_badges, many=True).data,
            },
            'activity': {
                'contributions_total': authored.count(),
                'contributions_approved': authored.filter(status='published').count(),
                'annotations_total': Annotation.objects.filter(user=user).count(),
            },
            'notifications': {
                'unread_count': notifications.filter(is_read=False).count(),
                'recent': UserNotificationListSerializer(recent_notifications, many=True).data,
            },
        })

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

