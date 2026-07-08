"""
Shared test helpers for city-scoped tests across apps.

Every content model requires a City after the multi-city refactor; test
setUps use `make_city()` instead of hand-rolling one per module.
"""

from django.contrib.gis.geos import Point

from .models import City, CityRole


def make_city(slug='test-city', name='Test City', **kwargs):
    defaults = {
        'name': name,
        'country': 'EC',
        'country_name': 'Ecuador',
        'region': 'Test Region',
        'timezone': 'America/Guayaquil',
        'center': Point(-78.6479, -1.6735, srid=4326),
        'default_zoom': 13,
        'default_language': 'es',
        'is_active': True,
    }
    defaults.update(kwargs)
    city, _ = City.objects.get_or_create(slug=slug, defaults=defaults)
    return city


def make_city_curator(user, city, role=CityRole.ROLE_CURATOR, granted_by=None):
    assignment, _ = CityRole.objects.get_or_create(
        user=user,
        city=city,
        role=role,
        defaults={'granted_by': granted_by},
    )
    return assignment
