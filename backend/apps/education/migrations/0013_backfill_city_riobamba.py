"""
All pre-multi-city educational resources and lesson plans belong to Riobamba.

(CurriculumStandard rows got country='EC'/framework='MinEduc' via the field
defaults in 0012 — no data step needed for them.)
"""

from django.db import migrations


def backfill_riobamba(apps, schema_editor):
    City = apps.get_model('cities', 'City')
    EducationalResource = apps.get_model('education', 'EducationalResource')
    LessonPlan = apps.get_model('education', 'LessonPlan')

    riobamba = City.objects.filter(slug='riobamba').first()
    if riobamba is None:
        return
    EducationalResource.objects.filter(city__isnull=True).update(city=riobamba)
    LessonPlan.objects.filter(city__isnull=True).update(city=riobamba)


class Migration(migrations.Migration):

    dependencies = [
        ('education', '0012_add_city_fk'),
        ('cities', '0002_seed_riobamba'),
    ]

    operations = [
        migrations.RunPython(backfill_riobamba, migrations.RunPython.noop),
    ]
