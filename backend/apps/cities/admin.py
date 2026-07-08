from django.contrib.gis import admin

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


@admin.register(City)
class CityAdmin(CityMapWidgetMixin, admin.GISModelAdmin):
    list_display = ['name', 'slug', 'country', 'region', 'is_active', 'order']
    list_filter = ['country', 'is_active']
    search_fields = ['name', 'slug', 'region']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CityRole)
class CityRoleAdmin(admin.ModelAdmin):
    list_display = ['user', 'city', 'role', 'granted_by', 'created_at']
    list_filter = ['city', 'role']
    search_fields = ['user__email', 'user__username']
    raw_id_fields = ['user', 'granted_by']
    readonly_fields = ['created_at']
