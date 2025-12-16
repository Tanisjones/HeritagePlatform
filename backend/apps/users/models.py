from django.contrib.auth.models import AbstractUser, UserManager as BaseUserManager
from django.contrib.gis.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Custom manager for User model with email as USERNAME_FIELD"""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password"""
        if not email:
            raise ValueError(_('The Email field must be set'))
        email = self.normalize_email(email)

        # Username is optional, so generate one from email if not provided
        if not extra_fields.get('username'):
            extra_fields['username'] = email.split('@')[0]

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser with the given email and password"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self.create_user(email, password, **extra_fields)


class UserRole(models.Model):
    """
    Predefined roles for users in the Heritage Platform.
    
    Roles define the level of access and permissions a user has.
    Common roles include:
    - Tourist: Read-only access to public content.
    - Contributor: Can submit heritage items.
    - Curator: content quality control.
    - Moderator: platform administration and report handling.
    """
    name = models.CharField(_('name'), max_length=50, unique=True)
    slug = models.SlugField(_('slug'), max_length=50, unique=True)
    permissions = models.JSONField(
        _('permissions'),
        default=dict,
        help_text=_('JSON object defining role permissions')
    )
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('user role')
        verbose_name_plural = _('user roles')
        ordering = ['name']

    def __str__(self):
        return self.name


class User(AbstractUser):
    """
    Custom User model extending Django's AbstractUser.
    Uses email as the primary identifier.
    """
    email = models.EmailField(_('email address'), unique=True)

    # Override username to make it optional
    username = models.CharField(
        _('username'),
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        help_text=_('Optional. 150 characters or fewer. Letters, digits and @/./+/-/_ only.')
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = UserManager()

    class Meta:
        verbose_name = _('user')
        verbose_name_plural = _('users')
        ordering = ['-date_joined']

    def __str__(self):
        return self.email


class UserProfile(models.Model):
    """
    Extended user profile with gamification and preferences.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('user')
    )
    display_name = models.CharField(
        _('display name'),
        max_length=100,
        blank=True,
        help_text=_('Public display name')
    )
    avatar = models.ImageField(
        _('avatar'),
        upload_to='avatars/',
        blank=True,
        null=True
    )
    bio = models.TextField(_('bio'), blank=True, max_length=500)
    location = models.PointField(
        _('location'),
        blank=True,
        null=True,
        help_text=_('User location coordinates')
    )
    preferred_language = models.CharField(
        _('preferred language'),
        max_length=5,
        choices=[
            ('es', _('Spanish')),
            ('en', _('English')),
        ],
        default='es'
    )
    role = models.ForeignKey(
        UserRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users',
        verbose_name=_('role')
    )

    # Gamification fields
    points = models.IntegerField(_('points'), default=0)
    level = models.IntegerField(_('level'), default=1)

    # Preferences
    notification_preferences = models.JSONField(
        _('notification preferences'),
        default=dict,
        help_text=_('User notification settings')
    )
    interests = models.JSONField(
        _('interests'),
        default=list,
        blank=True,
        help_text=_('User interests topics')
    )

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('user profile')
        verbose_name_plural = _('user profiles')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.display_name or self.user.email}'s profile"

    def add_points(self, points, reason=''):
        """Proxy to gamification service for adding points."""
        from apps.gamification.services import add_points
        add_points(self.user, points, reason)
