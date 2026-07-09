from django.contrib.gis import admin
from django.utils.translation import gettext_lazy as _

from apps.cities.admin import CityMapWidgetMixin

from .models import (
    HeritageCategory, HeritageType, Parish, MediaFile,
    HeritageItem, HeritageRelation, Annotation, Tag
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at']


@admin.register(HeritageCategory)
class HeritageCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'slug', 'order']
    list_filter = ['parent']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['order', 'name']


@admin.register(HeritageType)
class HeritageTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Parish)
class ParishAdmin(CityMapWidgetMixin, admin.GISModelAdmin):
    list_display = ['name', 'city', 'canton', 'province', 'population', 'area_km2']
    list_filter = ['city', 'canton', 'province']
    search_fields = ['name']


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ['file', 'file_type', 'uploaded_by', 'created_at', 'size']
    list_filter = ['file_type', 'created_at']
    search_fields = ['alt_text', 'caption']
    raw_id_fields = ['uploaded_by']
    readonly_fields = ['created_at', 'size', 'width', 'height', 'duration']


@admin.register(HeritageItem)
class HeritageItemAdmin(CityMapWidgetMixin, admin.GISModelAdmin):
    list_display = ['title', 'city', 'heritage_type', 'heritage_category', 'parish', 'status', 'contributor', 'created_at']
    list_filter = ['city', 'status', 'heritage_type', 'heritage_category', 'historical_period', 'created_at']
    search_fields = ['title', 'description', 'address', 'tags__name']
    raw_id_fields = ['contributor', 'parish']
    readonly_fields = ['id', 'created_at', 'updated_at', 'view_count', 'favorite_count']
    filter_horizontal = ['images', 'audio', 'video', 'tags']

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('id', 'title', 'description', 'status')
        }),
        (_('Location'), {
            # `city` is required — without it here, adding an item through the
            # admin would crash on the NOT NULL constraint.
            'fields': ('city', 'location', 'address', 'parish')
        }),
        (_('Classification'), {
            'fields': ('heritage_type', 'heritage_category', 'historical_period', 'tags')
        }),
        (_('Media'), {
            'fields': ('images', 'audio', 'video')
        }),
        (_('Metadata'), {
            'fields': ('external_registry_url', 'contributor', 'created_at', 'updated_at')
        }),
        (_('Statistics'), {
            'fields': ('view_count', 'favorite_count')
        }),
    )


@admin.register(HeritageRelation)
class HeritageRelationAdmin(admin.ModelAdmin):
    list_display = ['from_item', 'relation_type', 'to_item', 'created_at']
    list_filter = ['relation_type', 'created_at']
    search_fields = ['from_item__title', 'to_item__title', 'description']
    raw_id_fields = ['from_item', 'to_item']
    readonly_fields = ['created_at']


@admin.register(Annotation)
class AnnotationAdmin(admin.ModelAdmin):
    list_display = ['user', 'heritage_item', 'content_preview', 'created_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['user__email', 'heritage_item__title', 'content']
    raw_id_fields = ['user', 'heritage_item']
    readonly_fields = ['id', 'created_at', 'updated_at']

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = _('Content Preview')
