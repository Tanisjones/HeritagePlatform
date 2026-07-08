"""
Seed the founding city: all pre-multi-city content belongs to Riobamba.

Data migration only — reversible by deleting the slug.
"""

from django.contrib.gis.geos import Point
from django.db import migrations


def seed_riobamba(apps, schema_editor):
    City = apps.get_model('cities', 'City')
    City.objects.get_or_create(
        slug='riobamba',
        defaults={
            # Historical models have no modeltranslation descriptors: set the
            # base column and the es column explicitly (es is the default lang).
            'name': 'Riobamba',
            'name_es': 'Riobamba',
            'country': 'EC',
            'country_name': 'Ecuador',
            'country_name_es': 'Ecuador',
            'region': 'Chimborazo',
            'timezone': 'America/Guayaquil',
            'center': Point(-78.6479, -1.6735, srid=4326),
            'default_zoom': 13,
            'default_language': 'es',
            'is_active': True,
            'order': 0,
        },
    )


def unseed_riobamba(apps, schema_editor):
    City = apps.get_model('cities', 'City')
    City.objects.filter(slug='riobamba').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('cities', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_riobamba, unseed_riobamba),
    ]
