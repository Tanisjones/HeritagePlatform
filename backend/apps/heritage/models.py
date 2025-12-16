from django.contrib.gis.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
import mimetypes
from pathlib import Path
import uuid


class HeritageCategory(models.Model):
    """
    Hierarchical categories for heritage classification.
    Based on UNESCO and INPC (Ecuador) heritage categories.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_('name'), max_length=200)
    slug = models.SlugField(_('slug'), max_length=200, unique=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('parent category')
    )
    icon = models.CharField(
        _('icon'),
        max_length=50,
        blank=True,
        help_text=_('Icon name for frontend display')
    )
    description = models.TextField(_('description'), blank=True)
    order = models.IntegerField(_('order'), default=0)

    class Meta:
        verbose_name = _('heritage category')
        verbose_name_plural = _('heritage categories')
        ordering = ['order', 'name']
        unique_together = [['parent', 'slug']]

    def __str__(self):
        if self.parent:
            return f"{self.parent.name} > {self.name}"
        return self.name

    def get_ancestors(self):
        """Get all ancestor categories"""
        ancestors = []
        category = self.parent
        while category:
            ancestors.insert(0, category)
            category = category.parent
        return ancestors


class HeritageType(models.Model):
    """
    Main heritage types: tangible, intangible
    """
    name = models.CharField(_('name'), max_length=100, unique=True)
    slug = models.SlugField(_('slug'), max_length=100, unique=True)
    description = models.TextField(_('description'), blank=True)

    class Meta:
        verbose_name = _('heritage type')
        verbose_name_plural = _('heritage types')
        ordering = ['name']

    def __str__(self):
        return self.name


class Parish(models.Model):
    """
    Administrative divisions (parishes) within the canton.
    """
    name = models.CharField(_('name'), max_length=200)
    canton = models.CharField(_('canton'), max_length=200, default='Riobamba')
    province = models.CharField(_('province'), max_length=200, default='Chimborazo')
    boundary = models.MultiPolygonField(_('boundary'), null=True, blank=True)

    # Additional metadata
    population = models.IntegerField(_('population'), null=True, blank=True)
    area_km2 = models.FloatField(_('area (km²)'), null=True, blank=True)

    class Meta:
        verbose_name = _('parish')
        verbose_name_plural = _('parishes')
        ordering = ['canton', 'name']
        unique_together = [['name', 'canton']]

    def __str__(self):
        return f"{self.name}, {self.canton}"


class MediaFile(models.Model):
    """
    Media storage for heritage items (images, audio, video).
    """
    FILE_TYPE_CHOICES = [
        ('image', _('Image')),
        ('audio', _('Audio')),
        ('video', _('Video')),
        ('document', _('Document')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    file = models.FileField(
        _('file'),
        upload_to='heritage/%Y/%m/',
        validators=[FileExtensionValidator(
            allowed_extensions=['jpg', 'jpeg', 'png', 'gif', 'webp', 'mp3', 'wav', 'mp4', 'webm', 'pdf', 'txt', 'html']
        )],
        null=True,
        blank=True
    )
    text_content = models.TextField(_('text content'), blank=True)
    file_type = models.CharField(_('file type'), max_length=20, choices=FILE_TYPE_CHOICES)
    mime_type = models.CharField(_('MIME type'), max_length=100, blank=True)
    size = models.IntegerField(_('file size (bytes)'), null=True, blank=True)

    # Image-specific fields
    width = models.IntegerField(_('width'), null=True, blank=True)
    height = models.IntegerField(_('height'), null=True, blank=True)

    # Audio/Video-specific fields
    duration = models.DurationField(_('duration'), null=True, blank=True)

    # Metadata
    alt_text = models.CharField(_('alternative text'), max_length=500, blank=True)
    caption = models.TextField(_('caption'), blank=True)

    # Tracking
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='uploaded_media',
        verbose_name=_('uploaded by')
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('media file')
        verbose_name_plural = _('media files')
        ordering = ['-created_at']

    _EXTENSIONS_BY_TYPE = {
        'image': {'jpg', 'jpeg', 'png', 'gif', 'webp'},
        'audio': {'mp3', 'wav'},
        'video': {'mp4', 'webm'},
        # Text is represented as a document with mime_type text/plain for now.
        'document': {'pdf', 'txt', 'html'},
    }

    def clean(self):
        super().clean()

        # Cross-field validation: file_type must match extension.
        if self.file_type and self.file and getattr(self.file, 'name', None):
            ext = Path(self.file.name).suffix.lower().lstrip('.')
            allowed = self._EXTENSIONS_BY_TYPE.get(self.file_type)
            if allowed is not None and ext and ext not in allowed:
                raise ValidationError(
                    {
                        'file': _(
                            'File extension "%(ext)s" is not allowed for type "%(type)s".'
                        )
                        % {'ext': ext, 'type': self.file_type}
                    }
                )

    def save(self, *args, **kwargs):
        # Populate basic metadata best-effort.
        if self.file and getattr(self.file, 'name', None):
            if not self.mime_type:
                guessed, _ = mimetypes.guess_type(self.file.name)
                if guessed:
                    self.mime_type = guessed

            if self.size is None:
                try:
                    # FieldFile.size may require storage access; keep best-effort.
                    self.size = self.file.size
                except Exception:
                    pass

        # Enforce model-level constraints.
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.file_type}: {self.file.name}"


class HeritageItem(models.Model):
    """
    Composite Data Object (CDO) - Core heritage item model.
    Represents both tangible and intangible heritage with geospatial data.
    """
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('pending', _('Pending Review')),
        ('changes_requested', _('Changes Requested')),
        ('published', _('Published')),
        ('rejected', _('Rejected')),
        ('archived', _('Archived')),
    ]

    HISTORICAL_PERIOD_CHOICES = [
        ('pre-columbian', _('Pre-Columbian')),
        ('colonial', _('Colonial')),
        ('republican', _('Republican')),
        ('contemporary', _('Contemporary')),
        ('unknown', _('Unknown')),
    ]

    # Core identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(_('title'), max_length=500)
    description = models.TextField(_('description'))
    status = models.CharField(
        _('status'),
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft'
    )

    # Geospatial data
    location = models.PointField(_('location'), help_text=_('Geographic coordinates'))
    address = models.CharField(_('address'), max_length=500, blank=True)
    parish = models.ForeignKey(
        Parish,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='heritage_items',
        verbose_name=_('parish')
    )

    # Heritage classification
    heritage_type = models.ForeignKey(
        HeritageType,
        on_delete=models.PROTECT,
        related_name='heritage_items',
        verbose_name=_('heritage type')
    )
    heritage_category = models.ForeignKey(
        HeritageCategory,
        on_delete=models.PROTECT,
        related_name='heritage_items',
        verbose_name=_('heritage category')
    )
    historical_period = models.CharField(
        _('historical period'),
        max_length=50,
        choices=HISTORICAL_PERIOD_CHOICES,
        blank=True
    )

    # Media attachments
    main_image = models.ForeignKey(
        MediaFile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='heritage_items_main',
        verbose_name=_('main image')
    )

    images = models.ManyToManyField(
        MediaFile,
        related_name='heritage_items_as_image',
        blank=True,
        limit_choices_to={'file_type': 'image'},
        verbose_name=_('images')
    )
    audio = models.ManyToManyField(
        MediaFile,
        related_name='heritage_items_as_audio',
        blank=True,
        limit_choices_to={'file_type': 'audio'},
        verbose_name=_('audio files')
    )
    video = models.ManyToManyField(
        MediaFile,
        related_name='heritage_items_as_video',
        blank=True,
        limit_choices_to={'file_type': 'video'},
        verbose_name=_('video files')
    )
    documents = models.ManyToManyField(
        MediaFile,
        related_name='heritage_items_as_document',
        blank=True,
        limit_choices_to={'file_type': 'document'},
        verbose_name=_('documents')
    )

    # External references
    external_registry_url = models.URLField(
        _('external registry URL'),
        blank=True,
        help_text=_('Link to official heritage registry')
    )

    # Contributor tracking
    contributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='contributed_heritage',
        verbose_name=_('contributor')
    )
    curator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='curated_heritage',
        verbose_name=_('curator')
    )
    curator_feedback = models.TextField(_('curator feedback'), blank=True)
    priority = models.IntegerField(_('priority'), default=0)
    submission_date = models.DateTimeField(_('submission date'), null=True, blank=True)
    last_review_date = models.DateTimeField(_('last review date'), null=True, blank=True)
    moderator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='moderated_heritage',
        verbose_name=_('moderator')
    )
    moderator_feedback = models.TextField(_('moderator feedback'), blank=True)

    # Timestamps
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    # Statistics
    view_count = models.IntegerField(_('view count'), default=0)
    favorite_count = models.IntegerField(_('favorite count'), default=0)

    class Meta:
        verbose_name = _('heritage item')
        verbose_name_plural = _('heritage items')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['heritage_type', 'heritage_category']),
            models.Index(fields=['parish']),
            models.Index(fields=['status', '-submission_date']),
            models.Index(fields=['curator', 'status']),
            models.Index(fields=['priority', '-submission_date']),
        ]

    def __str__(self):
        return self.title

    def increment_view_count(self):
        """Increment view counter"""
        self.view_count += 1
        self.save(update_fields=['view_count'])

    @property
    def is_published(self):
        """Check if item is published"""
        return self.status == 'published'


class HeritageRelation(models.Model):
    """
    Links between heritage items to establish relationships.
    """
    RELATION_TYPE_CHOICES = [
        ('part_of', _('Part of')),
        ('related_to', _('Related to')),
        ('inspired_by', _('Inspired by')),
        ('located_near', _('Located near')),
        ('same_period', _('Same historical period')),
    ]

    from_item = models.ForeignKey(
        HeritageItem,
        on_delete=models.CASCADE,
        related_name='relations_from',
        verbose_name=_('from item')
    )
    to_item = models.ForeignKey(
        HeritageItem,
        on_delete=models.CASCADE,
        related_name='relations_to',
        verbose_name=_('to item')
    )
    relation_type = models.CharField(
        _('relation type'),
        max_length=50,
        choices=RELATION_TYPE_CHOICES
    )
    description = models.TextField(_('description'), blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)

    class Meta:
        verbose_name = _('heritage relation')
        verbose_name_plural = _('heritage relations')
        unique_together = [['from_item', 'to_item', 'relation_type']]

    def __str__(self):
        return f"{self.from_item} {self.get_relation_type_display()} {self.to_item}"


class Annotation(models.Model):
    """
    Community annotations for heritage items.
    Allows users to add comments, observations, and additional information to heritage items.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    heritage_item = models.ForeignKey(
        HeritageItem,
        on_delete=models.CASCADE,
        related_name='annotations',
        verbose_name=_('heritage item')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='annotations',
        verbose_name=_('user')
    )
    content = models.TextField(_('content'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('annotation')
        verbose_name_plural = _('annotations')
        ordering = ['-created_at']

    def __str__(self):
        return f"Annotation by {self.user} on {self.heritage_item}"
