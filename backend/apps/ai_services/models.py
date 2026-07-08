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


class AIUsageRecord(models.Model):
    """
    One row per AI operation attempt (success, error, or rate-limited), for the
    AI-economy dashboard. Records token usage and estimated cost — but NOT the
    prompt/response text (privacy + size).
    """

    STATUS_OK = 'ok'
    STATUS_ERROR = 'error'
    STATUS_RATE_LIMITED = 'rate_limited'
    STATUS_CHOICES = [
        (STATUS_OK, _('OK')),
        (STATUS_ERROR, _('Error')),
        (STATUS_RATE_LIMITED, _('Rate limited')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ai_usage_records',
        verbose_name=_('user'),
    )
    # Optional city context of the request (dashboard filtering). Nullable
    # forever: historical rows and city-less operations (e.g. translate).
    city = models.ForeignKey(
        'cities.City',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('city'),
    )
    operation = models.CharField(_('operation'), max_length=60)
    provider = models.CharField(_('provider'), max_length=40)
    model = models.CharField(_('model'), max_length=120)
    input_tokens = models.IntegerField(_('input tokens'), null=True, blank=True)
    output_tokens = models.IntegerField(_('output tokens'), null=True, blank=True)
    total_tokens = models.IntegerField(_('total tokens'), null=True, blank=True)
    estimated_cost_usd = models.DecimalField(
        _('estimated cost (USD)'), max_digits=10, decimal_places=6, null=True, blank=True
    )
    duration_ms = models.IntegerField(_('duration (ms)'), null=True, blank=True)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default=STATUS_OK)
    error_type = models.CharField(_('error type'), max_length=80, blank=True)

    class Meta:
        verbose_name = _('AI usage record')
        verbose_name_plural = _('AI usage records')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['operation']),
            models.Index(fields=['provider', 'model']),
            models.Index(fields=['city', 'created_at']),
        ]

    def __str__(self):
        return f"{self.operation} · {self.provider}/{self.model} · {self.status}"