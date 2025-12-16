from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class ContributionVersion(models.Model):
    CREATED_BY_TYPE_CHOICES = [
        ('contributor', _('Contributor')),
        ('curator', _('Curator')),
        ('system', _('System')),
    ]

    heritage_item = models.ForeignKey(
        'heritage.HeritageItem',
        on_delete=models.CASCADE,
        related_name='versions',
        verbose_name=_('heritage item'),
    )
    version_number = models.PositiveIntegerField(_('version number'))
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_versions',
        verbose_name=_('created by'),
    )
    created_by_type = models.CharField(
        _('created by type'),
        max_length=20,
        choices=CREATED_BY_TYPE_CHOICES,
        default='contributor',
    )
    data_snapshot = models.JSONField(_('data snapshot'), default=dict)
    changes_summary = models.TextField(_('changes summary'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('contribution version')
        verbose_name_plural = _('contribution versions')
        ordering = ['-version_number']
        constraints = [
            models.UniqueConstraint(
                fields=['heritage_item', 'version_number'],
                name='unique_version_per_heritage_item',
            ),
        ]
        indexes = [
            models.Index(fields=['heritage_item', '-version_number']),
        ]

    def save(self, *args, **kwargs):
        if not self.version_number:
            latest = (
                ContributionVersion.objects.filter(heritage_item=self.heritage_item)
                .order_by('-version_number')
                .first()
            )
            self.version_number = (latest.version_number if latest else 0) + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.heritage_item_id} v{self.version_number}"


class QualityScore(models.Model):
    heritage_item = models.OneToOneField(
        'heritage.HeritageItem',
        on_delete=models.CASCADE,
        related_name='quality_score',
        verbose_name=_('heritage item'),
    )
    completeness_score = models.PositiveIntegerField(
        _('completeness score'),
        validators=[MinValueValidator(0), MaxValueValidator(40)],
        default=0,
    )
    accuracy_score = models.PositiveIntegerField(
        _('accuracy score'),
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        default=0,
    )
    media_quality_score = models.PositiveIntegerField(
        _('media quality score'),
        validators=[MinValueValidator(0), MaxValueValidator(30)],
        default=0,
    )
    total_score = models.PositiveIntegerField(
        _('total score'),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=0,
    )
    scored_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quality_scores',
        verbose_name=_('scored by'),
    )
    scored_at = models.DateTimeField(_('scored at'), auto_now=True)
    notes = models.TextField(_('notes'), blank=True)

    class Meta:
        verbose_name = _('quality score')
        verbose_name_plural = _('quality scores')

    def calculate_total(self) -> int:
        return int(self.completeness_score) + int(self.accuracy_score) + int(self.media_quality_score)

    def save(self, *args, **kwargs):
        self.total_score = self.calculate_total()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.heritage_item_id} score {self.total_score}"


class ContributionFlag(models.Model):
    FLAG_TYPE_CHOICES = [
        ('spam', _('Spam')),
        ('inappropriate', _('Inappropriate')),
        ('duplicate', _('Duplicate')),
        ('expert_review_needed', _('Expert Review Needed')),
        ('copyright_issue', _('Copyright Issue')),
        ('inaccurate', _('Inaccurate')),
    ]

    STATUS_CHOICES = [
        ('open', _('Open')),
        ('under_review', _('Under Review')),
        ('resolved', _('Resolved')),
        ('dismissed', _('Dismissed')),
    ]

    heritage_item = models.ForeignKey(
        'heritage.HeritageItem',
        on_delete=models.CASCADE,
        related_name='flags',
        verbose_name=_('heritage item'),
    )
    flag_type = models.CharField(_('flag type'), max_length=30, choices=FLAG_TYPE_CHOICES)
    status = models.CharField(_('status'), max_length=20, choices=STATUS_CHOICES, default='open')
    flagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flags_created',
        verbose_name=_('flagged by'),
    )
    reason = models.TextField(_('reason'), blank=True)
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flags_resolved',
        verbose_name=_('resolved by'),
    )
    resolution_notes = models.TextField(_('resolution notes'), blank=True)
    resolved_at = models.DateTimeField(_('resolved at'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('contribution flag')
        verbose_name_plural = _('contribution flags')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['heritage_item', 'status']),
        ]

    def __str__(self):
        return f"{self.flag_type} ({self.status})"


class ReviewChecklist(models.Model):
    name = models.CharField(_('name'), max_length=200)
    description = models.TextField(_('description'), blank=True)
    is_active = models.BooleanField(_('is active'), default=True)
    applicable_to_types = models.ManyToManyField(
        'heritage.HeritageType',
        blank=True,
        related_name='review_checklists',
        verbose_name=_('applicable to types'),
    )
    applicable_to_categories = models.ManyToManyField(
        'heritage.HeritageCategory',
        blank=True,
        related_name='review_checklists',
        verbose_name=_('applicable to categories'),
    )

    class Meta:
        verbose_name = _('review checklist')
        verbose_name_plural = _('review checklists')

    def __str__(self):
        return self.name


class ReviewChecklistItem(models.Model):
    checklist = models.ForeignKey(
        ReviewChecklist,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name=_('checklist'),
    )
    text = models.CharField(_('text'), max_length=500)
    help_text = models.TextField(_('help text'), blank=True)
    order = models.PositiveIntegerField(_('order'), default=0)
    is_required = models.BooleanField(_('is required'), default=False)

    class Meta:
        verbose_name = _('review checklist item')
        verbose_name_plural = _('review checklist items')
        ordering = ['order', 'id']

    def __str__(self):
        return self.text


class ReviewChecklistResponse(models.Model):
    heritage_item = models.ForeignKey(
        'heritage.HeritageItem',
        on_delete=models.CASCADE,
        related_name='checklist_responses',
        verbose_name=_('heritage item'),
    )
    checklist_item = models.ForeignKey(
        ReviewChecklistItem,
        on_delete=models.CASCADE,
        related_name='responses',
        verbose_name=_('checklist item'),
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checklist_responses',
        verbose_name=_('curator'),
    )
    is_checked = models.BooleanField(_('is checked'), default=False)
    notes = models.TextField(_('notes'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('review checklist response')
        verbose_name_plural = _('review checklist responses')
        constraints = [
            models.UniqueConstraint(
                fields=['heritage_item', 'checklist_item', 'curator'],
                name='unique_checklist_response_per_user',
            )
        ]

    def __str__(self):
        return f"{self.heritage_item_id} - {self.checklist_item_id}"


class CuratorNote(models.Model):
    heritage_item = models.ForeignKey(
        'heritage.HeritageItem',
        on_delete=models.CASCADE,
        related_name='curator_notes',
        verbose_name=_('heritage item'),
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='curator_notes',
        verbose_name=_('curator'),
    )
    content = models.TextField(_('content'))
    is_pinned = models.BooleanField(_('is pinned'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('curator note')
        verbose_name_plural = _('curator notes')
        ordering = ['-is_pinned', '-created_at']

    def __str__(self):
        return f"Note on {self.heritage_item_id}"
