"""
Grant existing curators/moderators their Riobamba CityRole.

Before multi-city, `UserProfile.role` with slug 'curator'/'moderator' granted
platform-wide powers. Enforcement moves to per-city CityRole assignments;
every pre-existing curator/moderator was de facto a Riobamba one.

`profile.role` itself is left untouched (it keeps global capabilities such as
'teacher'; 'curator'/'moderator' slugs become vestigial labels).
"""

from django.db import migrations

GOVERNANCE_SLUGS = ('curator', 'moderator')


def backfill_city_roles(apps, schema_editor):
    """Kept as a plain function on purpose so tests can call it directly."""
    City = apps.get_model('cities', 'City')
    CityRole = apps.get_model('cities', 'CityRole')
    UserProfile = apps.get_model('users', 'UserProfile')

    riobamba = City.objects.filter(slug='riobamba').first()
    if riobamba is None:
        return

    profiles = UserProfile.objects.filter(
        role__slug__in=GOVERNANCE_SLUGS,
    ).select_related('role')
    for profile in profiles:
        CityRole.objects.get_or_create(
            user_id=profile.user_id,
            city=riobamba,
            role=profile.role.slug,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('cities', '0002_seed_riobamba'),
        ('users', '0004_userprofile_interests_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_city_roles, migrations.RunPython.noop),
    ]
