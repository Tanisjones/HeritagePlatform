from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _

from .models import User, UserProfile, UserRole
from apps.gamification.serializers import LevelSerializer
from apps.gamification.services import handle_registration, handle_profile_completion


class UserRoleSerializer(serializers.ModelSerializer):
    """Serializer for UserRole model"""

    class Meta:
        model = UserRole
        fields = ['id', 'name', 'slug', 'description']
        read_only_fields = ['id']


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for UserProfile model"""
    role = UserRoleSerializer(read_only=True)
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=UserRole.objects.all(),
        source='role',
        write_only=True,
        required=False
    )
    level_info = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            'display_name', 'avatar', 'bio', 'location',
            'preferred_language', 'role', 'role_id',
            'points', 'level', 'level_info', 'notification_preferences', 'interests',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['points', 'level', 'level_info', 'created_at', 'updated_at']

    def get_level_info(self, obj):
        from apps.gamification.models import Level

        level_obj = Level.objects.filter(number=obj.level).first()
        if not level_obj:
            return None
        return LevelSerializer(level_obj).data


class UserSerializer(serializers.ModelSerializer):
    """Serializer for User model with profile"""
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'first_name', 'last_name',
            'is_active', 'date_joined', 'profile'
        ]
        read_only_fields = ['id', 'date_joined']


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration"""
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    # Profile fields
    display_name = serializers.CharField(required=False, allow_blank=True)
    preferred_language = serializers.ChoiceField(
        choices=[('es', _('Spanish')), ('en', _('English'))],
        default='es'
    )
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=UserRole.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = User
        fields = [
            'email', 'username', 'password', 'password_confirm',
            'first_name', 'last_name', 'display_name',
            'preferred_language', 'role_id'
        ]
        extra_kwargs = {
            'username': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
        }

    def validate(self, attrs):
        """Validate password matching"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({
                'password_confirm': _('Passwords do not match.')
            })
        return attrs

    def create(self, validated_data):
        """Create user and profile"""
        # Remove password confirmation and profile fields
        validated_data.pop('password_confirm')
        display_name = validated_data.pop('display_name', '')
        preferred_language = validated_data.pop('preferred_language', 'es')
        role = validated_data.pop('role_id', None)

        # Extract email and password
        email = validated_data.pop('email')
        password = validated_data.pop('password')
        username = validated_data.pop('username', None)

        # Create user (username can be None since it's optional)
        user = User.objects.create_user(
            email=email,
            password=password,
            username=username,
            **validated_data
        )

        # Create or update profile
        profile, _ = UserProfile.objects.update_or_create(
            user=user,
            defaults={
                'display_name': display_name,
                'preferred_language': preferred_language,
                'role': role,
            }
        )

        handle_registration(user)
        handle_profile_completion(profile)

        return user


class LoginSerializer(serializers.Serializer):
    """Serializer for user login"""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate credentials and authenticate user"""
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(
                request=self.context.get('request'),
                username=email,
                password=password
            )

            if not user:
                raise serializers.ValidationError(
                    _('Unable to log in with provided credentials.'),
                    code='authorization'
                )

            if not user.is_active:
                raise serializers.ValidationError(
                    _('User account is disabled.'),
                    code='authorization'
                )
        else:
            raise serializers.ValidationError(
                _('Must include "email" and "password".'),
                code='authorization'
            )

        attrs['user'] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """Serializer for password change"""
    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, attrs):
        """Validate passwords"""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': _('Passwords do not match.')
            })
        return attrs

    def validate_old_password(self, value):
        """Validate old password"""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                _('Old password is incorrect.')
            )
        return value


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile"""
    role_id = serializers.PrimaryKeyRelatedField(
        queryset=UserRole.objects.all(),
        source='role',
        required=False,
        allow_null=True
    )

    # Allow updating user fields too
    first_name = serializers.CharField(source='user.first_name', required=False)
    last_name = serializers.CharField(source='user.last_name', required=False)

    class Meta:
        model = UserProfile
        fields = [
            'display_name', 'avatar', 'bio', 'location',
            'preferred_language', 'role_id', 'notification_preferences', 'interests',
            'first_name', 'last_name'
        ]

    def update(self, instance, validated_data):
        """Update profile and user fields"""
        # Extract user fields
        user_data = validated_data.pop('user', {})

        # Update user fields
        for attr, value in user_data.items():
            setattr(instance.user, attr, value)
        instance.user.save()

        # Update profile fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        handle_profile_completion(instance)

        return instance
