import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _

class AISuggestion(models.Model):
    """
    Stores AI-generated suggestions for heritage items.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    heritage_item = models.ForeignKey(
        'heritage.HeritageItem',
        on_delete=models.CASCADE,
        related_name='ai_suggestions',
        verbose_name=_('heritage item')
    )
    suggester = models.CharField(_('suggester'), max_length=100)
    suggestion_type = models.CharField(_('suggestion type'), max_length=100)
    content = models.JSONField(_('content'))
    confidence = models.FloatField(_('confidence'), null=True, blank=True)
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_suggestions',
        verbose_name=_('reviewed by')
    )
    reviewed_at = models.DateTimeField(_('reviewed at'), null=True, blank=True)

    class Meta:
        verbose_name = _('AI suggestion')
        verbose_name_plural = _('AI suggestions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.suggestion_type} for {self.heritage_item.title}"