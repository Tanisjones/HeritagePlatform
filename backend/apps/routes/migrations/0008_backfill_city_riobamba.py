"""
All pre-multi-city routes belong to Riobamba.
"""

from django.db import migrations


def backfill_riobamba(apps, schema_editor):
    City = apps.get_model('cities', 'City')
    HeritageRoute = apps.get_model('routes', 'HeritageRoute')

    riobamba = City.objects.filter(slug='riobamba').first()
    if riobamba is None:
        return
    HeritageRoute.objects.filter(city__isnull=True).update(city=riobamba)


class Migration(migrations.Migration):

    dependencies = [
        ('routes', '0007_add_city_fk'),
        ('cities', '0002_seed_riobamba'),
    ]

    operations = [
        migrations.RunPython(backfill_riobamba, migrations.RunPython.noop),
    ]
