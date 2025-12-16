"""
Education app models for IEEE LOM (Learning Object Metadata) support.

This module implements the IEEE 1484.12.1 Learning Object Metadata standard
to support educational use of heritage items.
"""

import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class LOMGeneral(models.Model):
    """
    IEEE LOM General category - General information about the learning object.
    Maps to LOM section 1.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    heritage_item = models.OneToOneField(
        'heritage.HeritageItem',
        on_delete=models.CASCADE,
        related_name='lom_general'
    )

    # 1.2 Title
    title = models.CharField(
        _('title'),
        max_length=500,
        help_text=_('Name given to this learning object')
    )

    # 1.3 Language (primary language of the learning object)
    language = models.CharField(
        _('language'),
        max_length=10,
        default='es',
        choices=[
            ('es', _('Spanish')),
            ('en', _('English')),
            ('qu', _('Quechua')),
        ],
        help_text=_('Primary language of the learning object')
    )

    # 1.4 Description
    description = models.TextField(
        _('description'),
        help_text=_('Description of the content of this learning object')
    )

    # 1.5 Keywords
    keywords = models.TextField(
        _('keywords'),
        blank=True,
        help_text=_('Keywords or phrases describing the topic (comma-separated)')
    )

    # 1.6 Coverage (temporal/spatial characteristics)
    coverage = models.TextField(
        _('coverage'),
        blank=True,
        help_text=_('Time, culture, geography or region to which this learning object applies')
    )

    # 1.7 Structure (organizational structure)
    structure = models.CharField(
        _('structure'),
        max_length=20,
        default='atomic',
        choices=[
            ('atomic', _('Atomic - indivisible object')),
            ('collection', _('Collection - set of objects')),
            ('networked', _('Networked - connected objects')),
            ('hierarchical', _('Hierarchical - tree structure')),
            ('linear', _('Linear - ordered sequence')),
        ],
        help_text=_('Underlying organizational structure')
    )

    # 1.8 Aggregation Level
    aggregation_level = models.IntegerField(
        _('aggregation level'),
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(4)],
        choices=[
            (1, _('Level 1 - Raw media/fragment')),
            (2, _('Level 2 - Lesson/unit')),
            (3, _('Level 3 - Course/module')),
            (4, _('Level 4 - Program/curriculum')),
        ],
        help_text=_('Functional granularity of this learning object')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('LOM General Metadata')
        verbose_name_plural = _('LOM General Metadata')

    def __str__(self):
        return f"LOM General: {self.title}"


class LOMLifeCycle(models.Model):
    """
    IEEE LOM Life Cycle category - History and current state.
    Maps to LOM section 2.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lom_general = models.OneToOneField(
        LOMGeneral,
        on_delete=models.CASCADE,
        related_name='lifecycle'
    )

    # 2.1 Version
    version = models.CharField(
        _('version'),
        max_length=50,
        blank=True,
        help_text=_('Edition of this learning object')
    )

    # 2.2 Status
    status = models.CharField(
        _('status'),
        max_length=20,
        default='draft',
        choices=[
            ('draft', _('Draft')),
            ('final', _('Final')),
            ('revised', _('Revised')),
            ('unavailable', _('Unavailable')),
        ],
        help_text=_('Completion status or condition')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('LOM Life Cycle')
        verbose_name_plural = _('LOM Life Cycles')

    def __str__(self):
        return f"LOM Life Cycle: {self.lom_general.title} v{self.version}"


class LOMContributor(models.Model):
    """
    IEEE LOM Contributor - People or organizations that contributed to the lifecycle.
    Maps to LOM section 2.3.
    """
    ROLE_CHOICES = [
        ('author', _('Author')),
        ('publisher', _('Publisher')),
        ('unknown', _('Unknown')),
        ('initiator', _('Initiator')),
        ('terminator', _('Terminator')),
        ('validator', _('Validator')),
        ('editor', _('Editor')),
        ('graphical_designer', _('Graphical Designer')),
        ('technical_implementer', _('Technical Implementer')),
        ('content_provider', _('Content Provider')),
        ('technical_validator', _('Technical Validator')),
        ('educational_validator', _('Educational Validator')),
        ('script_writer', _('Script Writer')),
        ('instructional_designer', _('Instructional Designer')),
        ('subject_matter_expert', _('Subject Matter Expert')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lifecycle = models.ForeignKey(
        LOMLifeCycle,
        on_delete=models.CASCADE,
        related_name='contributors'
    )

    role = models.CharField(
        _('role'),
        max_length=30,
        choices=ROLE_CHOICES,
        help_text=_('Kind of contribution')
    )

    entity = models.CharField(
        _('entity'),
        max_length=200,
        help_text=_('Name of contributing person or organization')
    )

    date = models.DateField(
        _('date'),
        null=True,
        blank=True,
        help_text=_('Date of contribution')
    )

    class Meta:
        verbose_name = _('LOM Contributor')
        verbose_name_plural = _('LOM Contributors')

    def __str__(self):
        return f"{self.get_role_display()}: {self.entity}"


class LOMEducational(models.Model):
    """
    IEEE LOM Educational category - Educational/pedagogic characteristics.
    Maps to LOM section 5.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lom_general = models.OneToOneField(
        LOMGeneral,
        on_delete=models.CASCADE,
        related_name='educational'
    )

    # 5.1 Interactivity Type
    interactivity_type = models.CharField(
        _('interactivity type'),
        max_length=20,
        default='expositive',
        choices=[
            ('active', _('Active - learning by doing')),
            ('expositive', _('Expositive - learning by reading/watching')),
            ('mixed', _('Mixed - combination')),
        ],
        help_text=_('Type of interactivity supported')
    )

    # 5.2 Learning Resource Type
    learning_resource_type = models.CharField(
        _('learning resource type'),
        max_length=30,
        default='narrative_text',
        choices=[
            ('image', _('Image')),
            ('audio', _('Audio')),
            ('video', _('Video')),
            ('document', _('Document')),
            ('exercise', _('Exercise')),
            ('simulation', _('Simulation')),
            ('questionnaire', _('Questionnaire')),
            ('diagram', _('Diagram')),
            ('figure', _('Figure')),
            ('graph', _('Graph')),
            ('index', _('Index')),
            ('slide', _('Slide')),
            ('table', _('Table')),
            ('narrative_text', _('Narrative Text')),
            ('exam', _('Exam')),
            ('experiment', _('Experiment')),
            ('problem_statement', _('Problem Statement')),
            ('self_assessment', _('Self Assessment')),
            ('lecture', _('Lecture')),
        ],
        help_text=_('Specific kind of learning object')
    )

    # 5.3 Interactivity Level
    interactivity_level = models.CharField(
        _('interactivity level'),
        max_length=20,
        default='medium',
        choices=[
            ('very_low', _('Very Low')),
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('very_high', _('Very High')),
        ],
        help_text=_('Degree of interactivity')
    )

    # 5.4 Semantic Density
    semantic_density = models.CharField(
        _('semantic density'),
        max_length=20,
        default='medium',
        choices=[
            ('very_low', _('Very Low')),
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('very_high', _('Very High')),
        ],
        help_text=_('Subjective measure of learning object usefulness')
    )

    # 5.5 Intended End User Role
    intended_end_user_role = models.CharField(
        _('intended end user role'),
        max_length=20,
        default='learner',
        choices=[
            ('teacher', _('Teacher')),
            ('author', _('Author')),
            ('learner', _('Learner')),
            ('manager', _('Manager')),
        ],
        help_text=_('Principal user(s) for which this learning object was designed')
    )

    # 5.6 Context
    context = models.CharField(
        _('context'),
        max_length=30,
        default='other',
        choices=[
            ('school', _('School - Primary/Secondary Education')),
            ('higher_education', _('Higher Education - University')),
            ('training', _('Training - Professional Development')),
            ('other', _('Other')),
        ],
        help_text=_('Principal environment within which learning is intended to occur')
    )

    # 5.7 Typical Age Range
    typical_age_range = models.CharField(
        _('typical age range'),
        max_length=50,
        blank=True,
        help_text=_('Age of the typical intended user (e.g., "7-9", "18+")')
    )

    # 5.8 Difficulty
    difficulty = models.CharField(
        _('difficulty'),
        max_length=20,
        default='medium',
        choices=[
            ('very_easy', _('Very Easy')),
            ('easy', _('Easy')),
            ('medium', _('Medium')),
            ('difficult', _('Difficult')),
            ('very_difficult', _('Very Difficult')),
        ],
        help_text=_('How hard it is to work through this learning object')
    )

    # 5.9 Typical Learning Time
    typical_learning_time = models.CharField(
        _('typical learning time'),
        max_length=50,
        blank=True,
        help_text=_('Approximate time it takes to work with this learning object (e.g., "PT30M" for 30 minutes)')
    )

    # 5.10 Description
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Comments on how this learning object is to be used')
    )

    # 5.11 Language (languages the learner is expected to understand)
    language = models.CharField(
        _('language'),
        max_length=10,
        default='es',
        choices=[
            ('es', _('Spanish')),
            ('en', _('English')),
            ('qu', _('Quechua')),
        ],
        help_text=_('Human language of the intended user')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('LOM Educational Metadata')
        verbose_name_plural = _('LOM Educational Metadata')

    def __str__(self):
        return f"LOM Educational: {self.lom_general.title}"


class LOMRights(models.Model):
    """
    IEEE LOM Rights category - Intellectual property rights and conditions of use.
    Maps to LOM section 6.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lom_general = models.OneToOneField(
        LOMGeneral,
        on_delete=models.CASCADE,
        related_name='rights'
    )

    # 6.1 Cost
    cost = models.BooleanField(
        _('cost'),
        default=False,
        help_text=_('Whether use of this learning object requires payment')
    )

    # 6.2 Copyright and Other Restrictions
    copyright_and_other_restrictions = models.BooleanField(
        _('copyright and other restrictions'),
        default=True,
        help_text=_('Whether copyright or other restrictions apply')
    )

    # 6.3 Description
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Comments on the conditions of use of this learning object')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('LOM Rights')
        verbose_name_plural = _('LOM Rights')

    def __str__(self):
        return f"LOM Rights: {self.lom_general.title}"


class LOMClassification(models.Model):
    """
    IEEE LOM Classification category - Where this learning object falls within a classification system.
    Maps to LOM section 9.
    """
    PURPOSE_CHOICES = [
        ('discipline', _('Discipline - Disciplinary taxonomy')),
        ('idea', _('Idea - Idea taxonomy')),
        ('prerequisite', _('Prerequisite - Prerequisites')),
        ('educational_objective', _('Educational Objective - Learning objectives')),
        ('accessibility_restrictions', _('Accessibility Restrictions - Access limitations')),
        ('educational_level', _('Educational Level - Grade level')),
        ('skill_level', _('Skill Level - Skill requirements')),
        ('security_level', _('Security Level - Security classification')),
        ('competency', _('Competency - Competencies addressed')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lom_general = models.ForeignKey(
        LOMGeneral,
        on_delete=models.CASCADE,
        related_name='classifications'
    )

    # 9.1 Purpose
    purpose = models.CharField(
        _('purpose'),
        max_length=40,
        choices=PURPOSE_CHOICES,
        help_text=_('Characteristic described by this classification')
    )

    # 9.2 Taxon Path (simplified as single fields)
    taxon_source = models.CharField(
        _('taxon source'),
        max_length=200,
        help_text=_('Name of the classification system')
    )

    taxon_id = models.CharField(
        _('taxon id'),
        max_length=100,
        blank=True,
        help_text=_('Identifier of the taxon')
    )

    taxon_entry = models.CharField(
        _('taxon entry'),
        max_length=500,
        help_text=_('Label of the taxon')
    )

    # 9.3 Description
    description = models.TextField(
        _('description'),
        blank=True,
        help_text=_('Description of the learning object relative to its classification')
    )

    # 9.4 Keywords
    keywords = models.TextField(
        _('keywords'),
        blank=True,
        help_text=_('Keywords describing the classification (comma-separated)')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('LOM Classification')
        verbose_name_plural = _('LOM Classifications')

    def __str__(self):
        return f"{self.get_purpose_display()}: {self.taxon_entry}"


class LOMRelation(models.Model):
    """
    IEEE LOM Relation category - Relationships between learning objects.
    Maps to LOM section 7.

    This implementation supports relations to:
    - another HeritageItem (CDO)
    - a MediaFile (e.g., two images of the same element)
    - an external URL
    """

    KIND_CHOICES = [
        ('is_part_of', _('Is part of')),
        ('has_part', _('Has part')),
        ('is_version_of', _('Is version of')),
        ('has_version', _('Has version')),
        ('is_format_of', _('Is format of')),
        ('has_format', _('Has format')),
        ('references', _('References')),
        ('is_referenced_by', _('Is referenced by')),
        ('is_similar_to', _('Is similar to')),
        ('requires', _('Requires')),
        ('is_required_by', _('Is required by')),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    lom_general = models.ForeignKey(
        LOMGeneral,
        on_delete=models.CASCADE,
        related_name='relations',
        verbose_name=_('LOM general')
    )

    kind = models.CharField(
        _('kind'),
        max_length=40,
        choices=KIND_CHOICES,
        help_text=_('Type of relationship')
    )

    target_heritage_item = models.ForeignKey(
        'heritage.HeritageItem',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lom_relations_targeting_item',
        verbose_name=_('target heritage item')
    )

    target_media_file = models.ForeignKey(
        'heritage.MediaFile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lom_relations_targeting_media',
        verbose_name=_('target media file')
    )

    target_url = models.URLField(
        _('target URL'),
        blank=True,
        help_text=_('External relation target')
    )

    description = models.TextField(_('description'), blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('LOM Relation')
        verbose_name_plural = _('LOM Relations')
        ordering = ['-updated_at']

    def clean(self):
        super().clean()
        targets = [
            bool(self.target_heritage_item_id),
            bool(self.target_media_file_id),
            bool(self.target_url),
        ]
        if sum(1 for t in targets if t) != 1:
            raise ValidationError(
                _('Exactly one target must be set: heritage item, media file, or URL.')
            )

    def __str__(self):
        target = (
            self.target_heritage_item
            or self.target_media_file
            or self.target_url
            or '—'
        )
        return f"{self.lom_general.title} {self.get_kind_display()} {target}"


class ResourceType(models.Model):
    """
    Type of educational resource (e.g., lesson plan, article, video).
    """
    name = models.CharField(_('name'), max_length=100, unique=True)
    slug = models.SlugField(_('slug'), max_length=100, unique=True)

    class Meta:
        verbose_name = _('resource type')
        verbose_name_plural = _('resource types')

    def __str__(self):
        return self.name

class ResourceCategory(models.Model):
    """
    Category for educational resources (e.g., History, Art, Architecture).
    """
    name = models.CharField(_('name'), max_length=100, unique=True)
    slug = models.SlugField(_('slug'), max_length=100, unique=True)

    class Meta:
        verbose_name = _('resource category')
        verbose_name_plural = _('resource categories')

    def __str__(self):
        return self.name

class EducationalResource(models.Model):
    """
    A standalone educational resource, such as a lesson plan, article, or video.
    """
    title = models.CharField(_('title'), max_length=200)
    description = models.TextField(_('description'))
    resource_type = models.ForeignKey(
        ResourceType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resources',
        verbose_name=_('resource type')
    )
    category = models.ForeignKey(
        ResourceCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resources',
        verbose_name=_('category')
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='educational_resources',
        verbose_name=_('author')
    )
    content = models.TextField(_('content'))
    related_heritage_items = models.ManyToManyField(
        'heritage.HeritageItem',
        blank=True,
        related_name='educational_resources',
        verbose_name=_('related heritage items')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('educational resource')
        verbose_name_plural = _('educational resources')
        ordering = ['-created_at']

    def __str__(self):
        return self.title
