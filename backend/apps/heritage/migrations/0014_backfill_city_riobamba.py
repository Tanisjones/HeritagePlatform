"""
All pre-multi-city parishes and heritage items belong to Riobamba.
"""

from django.db import migrations


def backfill_riobamba(apps, schema_editor):
    City = apps.get_model('cities', 'City')
    Parish = apps.get_model('heritage', 'Parish')
    HeritageItem = apps.get_model('heritage', 'HeritageItem')

    riobamba = City.objects.filter(slug='riobamba').first()
    if riobamba is None:
        # Fresh DB with no legacy content: nothing to backfill.
        return
    Parish.objects.filter(city__isnull=True).update(city=riobamba)
    HeritageItem.objects.filter(city__isnull=True).update(city=riobamba)


class Migration(migrations.Migration):

    dependencies = [
        ('heritage', '0013_add_city_fk'),
        ('cities', '0002_seed_riobamba'),
    ]

    operations = [
        migrations.RunPython(backfill_riobamba, migrations.RunPython.noop),
    ]
