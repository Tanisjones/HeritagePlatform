from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid

class Contribution(models.Model):
    """
    Citizen contributions (new items, enrichments, corrections).
    """
    CONTRIBUTION_TYPE_CHOICES = [
        ('new_item', _('New Heritage Item')),
        ('enrichment', _('Enrichment (Media/Info)')),
        ('correction', _('Correction')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending Review')),
        ('approved', _('Approved')),
        ('rejected', _('Rejected')),
        ('changes_requested', _('Changes Requested')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    heritage_item = models.ForeignKey(
        'heritage.HeritageItem',
        on_delete=models.CASCADE,
        related_name='contributions',
        verbose_name=_('heritage item'),
        null=True, blank=True # Nullable for new items suggestions
    )
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='contributions',
        verbose_name=_('contributor')
    )
    
    contribution_type = models.CharField(_('contribution type'), max_length=50, choices=CONTRIBUTION_TYPE_CHOICES)
    status = models.CharField(_('status'), max_length=50, choices=STATUS_CHOICES, default='pending')
    
    content = models.JSONField(_('content'), default=dict) # The actual data being contributed
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    reviewed_at = models.DateTimeField(_('reviewed at'), null=True, blank=True)
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_contributions',
        verbose_name=_('reviewer')
    )

    class Meta:
        verbose_name = _('contribution')
        verbose_name_plural = _('contributions')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_contribution_type_display()} by {self.contributor}"

class ContributionReview(models.Model):
    """
    Review history for a contribution.
    """
    DECISION_CHOICES = [
        ('approve', _('Approve')),
        ('reject', _('Reject')),
        ('request_changes', _('Request Changes')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contribution = models.ForeignKey(
        Contribution,
        on_delete=models.CASCADE,
        related_name='reviews',
        verbose_name=_('contribution')
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='contribution_reviews',
        verbose_name=_('reviewer')
    )
    
    decision = models.CharField(_('decision'), max_length=50, choices=DECISION_CHOICES)
    feedback = models.TextField(_('feedback'), blank=True)
    
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('contribution review')
        verbose_name_plural = _('contribution reviews')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review of {self.contribution} by {self.reviewer}: {self.decision}"
