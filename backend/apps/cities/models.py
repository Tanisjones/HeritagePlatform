"""
Multi-city tenancy models.

Every geographically scoped piece of content (parishes, heritage items,
routes, lesson plans, educational resources) carries a FK to a City.
Governance (curator/moderator) is granted per city via CityRole; staff and
superusers remain global. Users, taxonomies and gamification stay
platform-wide.
"""

from zoneinfo import available_timezones

from django.conf import settings
from django.contrib.gis.db import models
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


# First URL segments the SPA claims for itself (/<slug> is a city landing;
# static routes and the 'all' pseudo-city always win, so a city with one of
# these slugs would be unreachable).
RESERVED_CITY_SLUGS = frozenset({
    # SPA top-level routes
    'all', 'login', 'register', 'dashboard', 'profile', 'progress',
    'my-contributions', 'notifications', 'moderation', 'admin', 'teach',
    'explore', 'routes', 'heritage', 'education', 'learn', 'contribute',
    # Backend-owned prefixes (nginx proxies these to Django)
    'api', 'static', 'media',
    # Directories in the built frontend: nginx's `try_files $uri $uri/`
    # resolves a real directory before the SPA fallback, so a city named
    # after one of these 403s instead of rendering its landing page.
    'assets', 'icons', 'img',
})


def validate_city_slug(value):
    if value in RESERVED_CITY_SLUGS:
        raise ValidationError(
            _('"%(value)s" is reserved by the platform and cannot be a city slug.'),
            params={'value': value},
        )


class City(models.Model):
    """
    A city/municipality hosting its own heritage content on the shared platform.
    """
    name = models.CharField(_('name'), max_length=200)
    slug = models.SlugField(_('slug'), max_length=100, unique=True, validators=[validate_city_slug])
    description = models.TextField(_('description'), blank=True)
    country = models.CharField(
        _('country code'),
        max_length=2,
        default='EC',
        help_text=_('ISO 3166-1 alpha-2 country code, e.g. EC, PE, ES'),
    )
    country_name = models.CharField(_('country name'), max_length=100, default='Ecuador')
    region = models.CharField(_('region/province'), max_length=200, blank=True)
    timezone = models.CharField(
        _('timezone'),
        max_length=64,
        default='America/Guayaquil',
        help_text=_('IANA timezone name, e.g. America/Guayaquil'),
    )

    # Map framing for this city (used by the SPA and the admin widgets)
    center = models.PointField(_('map center'), help_text=_('Default map center for this city'))
    default_zoom = models.PositiveSmallIntegerField(_('default zoom'), default=13)
    boundary = models.MultiPolygonField(_('boundary'), null=True, blank=True)

    default_language = models.CharField(
        _('default language'),
        max_length=5,
        choices=[('es', 'Español'), ('en', 'English')],
        default='es',
    )
    hero_image = models.ImageField(
        _('hero image'),
        upload_to='cities/heroes/',
        null=True,
        blank=True,
        help_text=_('Landing-page hero image for this city'),
    )
    # Per-city branding (C3): the SPA re-themes its primary palette around
    # brand_color and shows the logo in the header when set. Both optional —
    # cities without branding keep the global platform look.
    brand_color = models.CharField(
        _('brand color'),
        max_length=7,
        blank=True,
        validators=[RegexValidator(r'^#[0-9a-fA-F]{6}$', _('Use a #RRGGBB hex color.'))],
        help_text=_('Hex color like #b55a3a; used as the accent color in the app'),
    )
    logo = models.ImageField(
        _('logo'),
        upload_to='cities/logos/',
        null=True,
        blank=True,
        help_text=_('Small square-ish logo shown next to the platform brand'),
    )
    is_active = models.BooleanField(_('active'), default=True)
    order = models.IntegerField(_('display order'), default=0)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('city')
        verbose_name_plural = _('cities')
        ordering = ['order', 'name']

    def __str__(self):
        return self.name

    def clean(self):
        if self.timezone and self.timezone not in available_timezones():
            raise ValidationError({
                'timezone': _('Unknown IANA timezone: %(tz)s') % {'tz': self.timezone},
            })

    def save(self, *args, **kwargs):
        # Field validators only run through full_clean(), i.e. admin forms and
        # DRF serializers — and CityViewSet is read-only. Every city the
        # platform actually creates comes from seed_city, bootstrap_city, a
        # data migration or loaddata, all of which call save() directly, so
        # enforce the reserved-slug rule here or it never runs.
        validate_city_slug(self.slug)
        super().save(*args, **kwargs)

    @classmethod
    def get_default(cls):
        """First active city by display order — fallback for writes without city context."""
        return cls.objects.filter(is_active=True).order_by('order', 'name').first()


class CityRole(models.Model):
    """
    Per-city governance grant. A user with a 'curator' CityRole moderates
    content only for that city; staff/superusers are global. Platform-wide
    capabilities (tourist/contributor/teacher) stay on UserProfile.role.
    """
    ROLE_CURATOR = 'curator'
    ROLE_MODERATOR = 'moderator'
    ROLE_CHOICES = [
        (ROLE_CURATOR, _('Curator')),
        (ROLE_MODERATOR, _('Moderator')),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='city_roles',
        verbose_name=_('user'),
    )
    city = models.ForeignKey(
        City,
        on_delete=models.CASCADE,
        related_name='role_assignments',
        verbose_name=_('city'),
    )
    role = models.CharField(_('role'), max_length=20, choices=ROLE_CHOICES)
    granted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='granted_city_roles',
        verbose_name=_('granted by'),
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('city role')
        verbose_name_plural = _('city roles')
        constraints = [
            models.UniqueConstraint(fields=['user', 'city', 'role'], name='unique_user_city_role'),
        ]
        indexes = [
            models.Index(fields=['user', 'role']),
            models.Index(fields=['city', 'role']),
        ]

    def __str__(self):
        return f"{self.user} — {self.role} @ {self.city.slug}"
