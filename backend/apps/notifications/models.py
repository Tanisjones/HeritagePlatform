import uuid
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _


class NotificationTemplate(models.Model):
    name = models.CharField(_('name'), max_length=100, unique=True)
    subject = models.CharField(_('subject'), max_length=255)
    body = models.TextField(_('body'))
    is_html = models.BooleanField(_('is HTML'), default=True)

    class Meta:
        verbose_name = _('notification template')
        verbose_name_plural = _('notification templates')

    def __str__(self):
        return self.name


class UserNotification(models.Model):
    """
    In-app notifications for users.
    Supports various notification types and links to related objects via GenericForeignKey.
    """
    NOTIFICATION_TYPES = [
        ('contribution_approved', _('Contribution Approved')),
        ('contribution_rejected', _('Contribution Rejected')),
        ('changes_requested', _('Changes Requested')),
        ('curator_edit', _('Curator Edit')),
        ('contribution_flagged', _('Contribution Flagged')),
        ('contribution_resubmitted', _('Contribution Resubmitted')),
        ('annotation_reply', _('Annotation Reply')),
        ('badge_earned', _('Badge Earned')),
        ('level_up', _('Level Up')),
        ('moderation_needed', _('Moderation Needed')),
        ('system', _('System Notification')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('recipient')
    )
    notification_type = models.CharField(
        _('notification type'),
        max_length=50,
        choices=NOTIFICATION_TYPES
    )
    title = models.CharField(_('title'), max_length=255)
    message = models.TextField(_('message'))
    is_read = models.BooleanField(_('is read'), default=False)
    read_at = models.DateTimeField(_('read at'), null=True, blank=True)

    # Link to related object (e.g., HeritageItem, Contribution, Badge)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    object_id = models.UUIDField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')

    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('user notification')
        verbose_name_plural = _('user notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"{self.recipient.email} - {self.title}"

    def mark_as_read(self):
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            from django.utils import timezone
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
