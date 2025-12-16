"""
Admin configuration for education app models.
"""

from django.contrib import admin
from .models import (
    LOMGeneral, LOMLifeCycle, LOMContributor, LOMEducational,
    LOMRights, LOMClassification, ResourceType, ResourceCategory,
    EducationalResource
)


class LOMContributorInline(admin.TabularInline):
    """Inline admin for LOM contributors."""
    model = LOMContributor
    extra = 1


class LOMClassificationInline(admin.TabularInline):
    """Inline admin for LOM classifications."""
    model = LOMClassification
    extra = 1


class LOMLifeCycleInline(admin.StackedInline):
    """Inline admin for LOM lifecycle."""
    model = LOMLifeCycle
    extra = 0
    max_num = 1


class LOMEducationalInline(admin.StackedInline):
    """Inline admin for LOM educational metadata."""
    model = LOMEducational
    extra = 0
    max_num = 1


class LOMRightsInline(admin.StackedInline):
    """Inline admin for LOM rights."""
    model = LOMRights
    extra = 0
    max_num = 1


@admin.register(LOMGeneral)
class LOMGeneralAdmin(admin.ModelAdmin):
    """Admin interface for LOM General metadata."""
    list_display = ['title', 'heritage_item', 'language', 'structure', 'aggregation_level', 'created_at']
    list_filter = ['language', 'structure', 'aggregation_level', 'created_at']
    search_fields = ['title', 'description', 'keywords']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'heritage_item', 'title', 'language')
        }),
        ('Description', {
            'fields': ('description', 'keywords', 'coverage')
        }),
        ('Structure', {
            'fields': ('structure', 'aggregation_level')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [
        LOMLifeCycleInline,
        LOMEducationalInline,
        LOMRightsInline,
        LOMClassificationInline,
    ]


@admin.register(LOMLifeCycle)
class LOMLifeCycleAdmin(admin.ModelAdmin):
    """Admin interface for LOM Life Cycle."""
    list_display = ['lom_general', 'version', 'status', 'updated_at']
    list_filter = ['status', 'created_at', 'updated_at']
    search_fields = ['lom_general__title', 'version']
    readonly_fields = ['id', 'created_at', 'updated_at']

    inlines = [LOMContributorInline]


@admin.register(LOMContributor)
class LOMContributorAdmin(admin.ModelAdmin):
    """Admin interface for LOM Contributors."""
    list_display = ['entity', 'role', 'date', 'lifecycle']
    list_filter = ['role', 'date']
    search_fields = ['entity', 'lifecycle__lom_general__title']
    readonly_fields = ['id']


@admin.register(LOMEducational)
class LOMEducationalAdmin(admin.ModelAdmin):
    """Admin interface for LOM Educational metadata."""
    list_display = [
        'lom_general', 'learning_resource_type', 'context',
        'intended_end_user_role', 'difficulty'
    ]
    list_filter = [
        'learning_resource_type', 'context', 'intended_end_user_role',
        'difficulty', 'interactivity_type', 'interactivity_level'
    ]
    search_fields = ['lom_general__title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('General', {
            'fields': ('id', 'lom_general', 'language')
        }),
        ('Resource Characteristics', {
            'fields': (
                'learning_resource_type', 'interactivity_type',
                'interactivity_level', 'semantic_density'
            )
        }),
        ('Target Audience', {
            'fields': (
                'intended_end_user_role', 'context',
                'typical_age_range', 'difficulty'
            )
        }),
        ('Learning Information', {
            'fields': ('typical_learning_time', 'description')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LOMRights)
class LOMRightsAdmin(admin.ModelAdmin):
    """Admin interface for LOM Rights."""
    list_display = ['lom_general', 'cost', 'copyright_and_other_restrictions', 'updated_at']
    list_filter = ['cost', 'copyright_and_other_restrictions', 'created_at']
    search_fields = ['lom_general__title', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(LOMClassification)
class LOMClassificationAdmin(admin.ModelAdmin):
    """Admin interface for LOM Classifications."""
    list_display = ['lom_general', 'purpose', 'taxon_source', 'taxon_entry']
    list_filter = ['purpose', 'created_at']
    search_fields = ['lom_general__title', 'taxon_source', 'taxon_entry', 'keywords']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('General', {
            'fields': ('id', 'lom_general', 'purpose')
        }),
        ('Taxonomy', {
            'fields': ('taxon_source', 'taxon_id', 'taxon_entry')
        }),
        ('Additional Information', {
            'fields': ('description', 'keywords')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ResourceType)
class ResourceTypeAdmin(admin.ModelAdmin):
    """Admin interface for Resource Types."""
    list_display = ['name', 'slug']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ResourceCategory)
class ResourceCategoryAdmin(admin.ModelAdmin):
    """Admin interface for Resource Categories."""
    list_display = ['name', 'slug']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(EducationalResource)
class EducationalResourceAdmin(admin.ModelAdmin):
    """Admin interface for Educational Resources."""
    list_display = ['title', 'resource_type', 'category', 'author', 'created_at']
    list_filter = ['resource_type', 'category', 'created_at']
    search_fields = ['title', 'description', 'content']
    readonly_fields = ['created_at', 'updated_at']
    filter_horizontal = ['related_heritage_items']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'description', 'resource_type', 'category', 'author')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Related Heritage Items', {
            'fields': ('related_heritage_items',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
