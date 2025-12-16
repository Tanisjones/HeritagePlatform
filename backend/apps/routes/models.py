from django.contrib.gis.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import F
import uuid

class HeritageRoute(models.Model):
    """
    Tourist or educational route attempting to visit multiple heritage items.
    """
    DIFFICULTY_CHOICES = [
        ('easy', _('Easy')),
        ('medium', _('Medium')),
        ('hard', _('Hard')),
    ]
    
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending', _('Pending Review')),
        ('changes_requested', _('Changes Requested')),
        ('published', _('Published')),
        ('rejected', _('Rejected')),
        ('archived', _('Archived')),
    ]

    SEASON_CHOICES = [
        ('spring', _('Spring')),
        ('summer', _('Summer')),
        ('autumn', _('Autumn')),
        ('winter', _('Winter')),
        ('year_round', _('Year Round')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'))
    theme = models.CharField(_('theme'), max_length=100, blank=True)
    difficulty = models.CharField(_('difficulty'), max_length=20, choices=DIFFICULTY_CHOICES, default='medium')
    estimated_duration = models.DurationField(_('estimated duration'), null=True, blank=True)
    distance = models.FloatField(_('distance (km)'), null=True, blank=True)
    
    path = models.LineStringField(_('path'), null=True, blank=True)
    
    items = models.ManyToManyField(
        'heritage.HeritageItem',
        through='RouteStop',
        related_name='routes',
        verbose_name=_('heritage items')
    )
    
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_routes',
        verbose_name=_('creator')
    )
    
    is_official = models.BooleanField(_('is official'), default=False)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='draft')

    # Governance fields
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='curated_routes',
        verbose_name=_('curator')
    )
    curator_feedback = models.TextField(_('curator feedback'), blank=True)
    last_review_date = models.DateTimeField(_('last review date'), null=True, blank=True)
    submission_date = models.DateTimeField(_('submission date'), null=True, blank=True)
    priority = models.IntegerField(_('priority'), default=0)

    # Accessibility metadata
    wheelchair_accessible = models.BooleanField(_('wheelchair accessible'), default=False)
    public_transit_accessible = models.BooleanField(_('public transit accessible'), default=False)
    accessibility_notes = models.TextField(_('accessibility notes'), blank=True)

    # Seasonal and cost information
    best_season = models.CharField(
        _('best season'),
        max_length=50,
        choices=SEASON_CHOICES,
        blank=True
    )
    estimated_cost = models.DecimalField(
        _('estimated cost'),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )
    cost_notes = models.TextField(_('cost notes'), blank=True)

    # Language support
    available_languages = models.JSONField(
        _('available languages'),
        default=list,
        blank=True,
        help_text=_('Array of language codes, e.g., ["es", "en"]')
    )

    # Statistics (computed/cached)
    view_count = models.IntegerField(_('view count'), default=0)
    completion_count = models.IntegerField(_('completion count'), default=0)
    average_rating = models.FloatField(_('average rating'), null=True, blank=True)

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('heritage route')
        verbose_name_plural = _('heritage routes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['creator', 'status']),
            models.Index(fields=['-view_count']),
            models.Index(fields=['-completion_count']),
            models.Index(fields=['is_official', 'status']),
        ]

    def __str__(self):
        return self.title

    def increment_view_count(self):
        """Increment the view count for this route."""
        self.view_count = F('view_count') + 1
        self.save(update_fields=['view_count'])
        self.refresh_from_db(fields=['view_count'])

class RouteStop(models.Model):
    """
    Ordered stop in a route.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(HeritageRoute, on_delete=models.CASCADE, related_name='stops')
    heritage_item = models.ForeignKey('heritage.HeritageItem', on_delete=models.CASCADE, related_name='route_stops')
    
    order = models.IntegerField(_('order'), default=0)
    arrival_instructions = models.TextField(_('arrival instructions'), blank=True)
    suggested_time = models.DurationField(_('suggested time'), null=True, blank=True)

    class Meta:
        verbose_name = _('route stop')
        verbose_name_plural = _('route stops')
        ordering = ['route', 'order']
        unique_together = ['route', 'heritage_item']

    def __str__(self):
        return f"{self.route.title} - Stop {self.order}: {self.heritage_item.title}"

class UserRouteProgress(models.Model):
    """
    Track user progress through a route.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='route_progress',
        verbose_name=_('user')
    )
    route = models.ForeignKey(
        HeritageRoute,
        on_delete=models.CASCADE,
        related_name='user_progress',
        verbose_name=_('route')
    )
    
    started_at = models.DateTimeField(_('started at'), auto_now_add=True)
    completed_at = models.DateTimeField(_('completed at'), null=True, blank=True)
    
    current_stop = models.ForeignKey(
        RouteStop,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_users',
        verbose_name=_('current stop')
    )
    
    visited_stops = models.ManyToManyField(
        RouteStop,
        blank=True,
        related_name='visited_by_users',
        verbose_name=_('visited stops')
    )

    class Meta:
        verbose_name = _('user route progress')
        verbose_name_plural = _('user route progress')
        unique_together = ['user', 'route']

    def __str__(self):
        return f"{self.user} - {self.route}"


class RouteRating(models.Model):
    """
    User ratings for routes.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey(
        HeritageRoute,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_('route')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='route_ratings',
        verbose_name=_('user')
    )
    rating = models.IntegerField(
        _('rating'),
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Rating from 1 to 5 stars')
    )
    comment = models.TextField(_('comment'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('route rating')
        verbose_name_plural = _('route ratings')
        unique_together = ['route', 'user']
        indexes = [
            models.Index(fields=['route', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user} - {self.route.title}: {self.rating}/5"
