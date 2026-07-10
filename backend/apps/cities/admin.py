from django.contrib.gis import admin
from django.db.models import Count, Q
from django.utils.translation import gettext_lazy as _

from .models import City, CityRole


class CityMapWidgetMixin:
    """
    GISModelAdmin mixin: center the map widget on the object's city (or the
    default city) at request time instead of hardcoding one location.

    Only affects the empty-value default framing of the widget; when the
    field already has geometry the widget centers on it.
    """

    def _city_for_widget(self, obj):
        if isinstance(obj, City):
            return obj
        city = getattr(obj, 'city', None)
        if city is not None:
            return city
        return City.get_default()

    def get_form(self, request, obj=None, **kwargs):
        city = self._city_for_widget(obj)
        if city is not None and city.center is not None:
            attrs = {
                'default_lon': city.center.x,
                'default_lat': city.center.y,
                'default_zoom': city.default_zoom,
            }
        else:
            # No city yet (fresh install): world view.
            attrs = {'default_lon': 0, 'default_lat': 0, 'default_zoom': 2}
        self.gis_widget_kwargs = {'attrs': attrs}
        return super().get_form(request, obj, **kwargs)


class CityRoleAssignmentInline(admin.TabularInline):
    """E1 — the city's governance roster on the City change page."""
    model = CityRole
    fk_name = 'city'
    extra = 0
    autocomplete_fields = ['user']
    fields = ['user', 'role', 'granted_by', 'created_at']
    readonly_fields = ['granted_by', 'created_at']


@admin.register(City)
class CityAdmin(CityMapWidgetMixin, admin.GISModelAdmin):
    inlines = [CityRoleAssignmentInline]
    list_display = [
        'name', 'slug', 'country', 'is_active', 'order',
        # E3 — per-city workload and content at a glance.
        'items_total', 'items_pending', 'routes_total', 'plans_total', 'curators_total',
    ]
    list_filter = ['country', 'is_active']
    search_fields = ['name', 'slug', 'region']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    def get_queryset(self, request):
        # E3 — every count in ONE query; distinct=True on each keeps the
        # multi-join Counts from multiplying one another.
        return super().get_queryset(request).annotate(
            _items=Count('heritage_items', distinct=True),
            _pending=Count(
                'heritage_items',
                filter=Q(heritage_items__status='pending'),
                distinct=True,
            ),
            _routes=Count('routes', distinct=True),
            _plans=Count('lesson_plans', distinct=True),
            _curators=Count(
                'role_assignments',
                filter=Q(role_assignments__role=CityRole.ROLE_CURATOR),
                distinct=True,
            ),
        )

    @admin.display(description=_('Items'), ordering='_items')
    def items_total(self, obj):
        return obj._items

    @admin.display(description=_('Pending'), ordering='_pending')
    def items_pending(self, obj):
        return obj._pending

    @admin.display(description=_('Routes'), ordering='_routes')
    def routes_total(self, obj):
        return obj._routes

    @admin.display(description=_('Lesson plans'), ordering='_plans')
    def plans_total(self, obj):
        return obj._plans

    @admin.display(description=_('Curators'), ordering='_curators')
    def curators_total(self, obj):
        return obj._curators

    def save_formset(self, request, form, formset, change):
        # Same auto-stamp as the User admin: record who granted each role.
        if formset.model is CityRole:
            instances = formset.save(commit=False)
            for obj in instances:
                if not obj.granted_by_id:
                    obj.granted_by = request.user
                obj.save()
            for obj in formset.deleted_objects:
                obj.delete()
            formset.save_m2m()
            return
        super().save_formset(request, form, formset, change)


@admin.register(CityRole)
class CityRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'role', 'granted_by', 'created_at']
    list_filter = ['city', 'role']
    search_fields = ['user__email', 'user__username']
    raw_id_fields = ['user', 'granted_by']
    readonly_fields = ['created_at']
