from rest_framework import serializers
from rest_framework_gis.serializers import GeometryField

from .models import City


class CityRefSerializer(serializers.ModelSerializer):
    """Compact reference embedded on city-scoped content (items, routes, plans…)."""

    class Meta:
        model = City
        fields = ['id', 'slug', 'name']


class CitySerializer(serializers.ModelSerializer):
    """Full public representation for the /cities/ catalog."""
    center = GeometryField(read_only=True)
    boundary = GeometryField(read_only=True)

    class Meta:
        model = City
        fields = [
            'id', 'slug', 'name', 'description', 'country', 'country_name',
            'region', 'timezone', 'center', 'default_zoom', 'boundary',
            'default_language', 'hero_image', 'brand_color', 'logo', 'is_active',
        ]
