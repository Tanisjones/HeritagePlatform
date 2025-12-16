import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _


class PointTransaction(models.Model):
    """
    Log of all point transactions for users.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='point_transactions',
        verbose_name=_('user')
    )
    points = models.IntegerField(_('points'))
    reason = models.CharField(_('reason'), max_length=500)
    reference_type = models.CharField(
        _('reference type'),
        max_length=100,
        blank=True,
        help_text=_('Content type of related object')
    )
    reference_id = models.CharField(
        _('reference ID'),
        max_length=255,
        blank=True,
        help_text=_('ID of related object')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('point transaction')
        verbose_name_plural = _('point transactions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}: {'+' if self.points > 0 else ''}{self.points} - {self.reason}"


class Badge(models.Model):
    """
    Achievement badges that users can earn.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'))
    icon = models.ImageField(_('icon'), upload_to='badges/', blank=True, null=True)
    category = models.CharField(_('category'), max_length=100)
    points_value = models.IntegerField(_('points value'), default=0)
    requirements = models.JSONField(_('requirements'), default=dict)

    class Meta:
        verbose_name = _('badge')
        verbose_name_plural = _('badges')

    def __str__(self):
        return self.name


class Level(models.Model):
    """
    User levels based on accumulated points.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number = models.IntegerField(_('number'), unique=True)
    name = models.CharField(_('name'), max_length=100)
    min_points = models.IntegerField(_('minimum points'))
    max_points = models.IntegerField(_('maximum points'))
    benefits = models.JSONField(_('benefits'), default=dict)

    class Meta:
        verbose_name = _('level')
        verbose_name_plural = _('levels')
        ordering = ['number']

    def __str__(self):
        return f"Level {self.number}: {self.name}"


class UserBadge(models.Model):
    """
    A user's earned badge.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='badges',
        verbose_name=_('user')
    )
    badge = models.ForeignKey(
        Badge,
        on_delete=models.CASCADE,
        related_name='user_badges',
        verbose_name=_('badge')
    )
    earned_at = models.DateTimeField(_('earned at'), auto_now_add=True)

    class Meta:
        verbose_name = _('user badge')
        verbose_name_plural = _('user badges')
        unique_together = ('user', 'badge')

    def __str__(self):
        return f"{self.user.email} - {self.badge.name}"

