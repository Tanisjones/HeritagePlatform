"""
Admin configuration for routes app models.
"""

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import HeritageRoute, RouteStop, UserRouteProgress, RouteRating


class RouteStopInline(admin.TabularInline):
    """Inline admin for route stops."""
    model = RouteStop
    extra = 1
    fields = ['order', 'heritage_item', 'arrival_instructions', 'suggested_time']
    ordering = ['order']


@admin.register(HeritageRoute)
class HeritageRouteAdmin(GISModelAdmin):
    """Admin interface for Heritage Routes."""
    list_display = ['title', 'theme', 'difficulty', 'status', 'is_official', 'creator', 'view_count', 'average_rating', 'created_at']
    list_filter = ['difficulty', 'status', 'is_official', 'theme', 'best_season', 'wheelchair_accessible', 'created_at']
    search_fields = ['title', 'description', 'theme', 'creator__email', 'curator__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'view_count', 'completion_count', 'average_rating']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'title', 'description', 'theme')
        }),
        ('Route Details', {
            'fields': ('difficulty', 'estimated_duration', 'distance', 'path')
        }),
        ('Accessibility', {
            'fields': ('wheelchair_accessible', 'public_transit_accessible', 'accessibility_notes')
        }),
        ('Cost & Season', {
            'fields': ('estimated_cost', 'cost_notes', 'best_season')
        }),
        ('Languages', {
            'fields': ('available_languages',)
        }),
        ('Management', {
            'fields': ('creator', 'is_official', 'status', 'priority')
        }),
        ('Governance', {
            'fields': ('curator', 'curator_feedback', 'submission_date', 'last_review_date'),
            'classes': ('collapse',)
        }),
        ('Statistics', {
            'fields': ('view_count', 'completion_count', 'average_rating'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [RouteStopInline]


@admin.register(RouteStop)
class RouteStopAdmin(admin.ModelAdmin):
    """Admin interface for Route Stops."""
    list_display = ['route', 'order', 'heritage_item', 'suggested_time']
    list_filter = ['route']
    search_fields = ['route__title', 'heritage_item__title', 'arrival_instructions']
    readonly_fields = ['id']
    ordering = ['route', 'order']

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'route', 'heritage_item', 'order')
        }),
        ('Stop Details', {
            'fields': ('arrival_instructions', 'suggested_time')
        }),
    )


@admin.register(UserRouteProgress)
class UserRouteProgressAdmin(admin.ModelAdmin):
    """Admin interface for User Route Progress."""
    list_display = ['user', 'route', 'current_stop', 'started_at', 'completed_at']
    list_filter = ['started_at', 'completed_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name', 'route__title']
    readonly_fields = ['id', 'started_at']
    date_hierarchy = 'started_at'
    filter_horizontal = ['visited_stops']

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'user', 'route')
        }),
        ('Progress', {
            'fields': ('current_stop', 'visited_stops')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(RouteRating)
class RouteRatingAdmin(admin.ModelAdmin):
    """Admin interface for Route Ratings."""
    list_display = ['route', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['route__title', 'user__email', 'user__first_name', 'user__last_name', 'comment']
    readonly_fields = ['id', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('General Information', {
            'fields': ('id', 'route', 'user')
        }),
        ('Rating', {
            'fields': ('rating', 'comment')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
