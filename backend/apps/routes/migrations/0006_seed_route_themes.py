"""Seed a curated RouteTheme vocabulary and backfill existing routes (H.2).

Idempotent: uses get_or_create by slug, and only fills theme_category where it is
still null, matching a route's legacy free-text `theme` (case-insensitive, exact or
substring) to a seeded theme. Reversible: the reverse only detaches the seeded
themes from routes and deletes them (leaving the `theme` string intact).
"""

from django.db import migrations


# Curated themes for Riobamba's heritage routes (es-first; en filled in too).
SEED_THEMES = [
    {"slug": "colonial-architecture", "es": "Arquitectura colonial", "en": "Colonial architecture",
     "color": "#c76b4a", "aliases": ["colonial", "arquitectura", "architecture"]},
    {"slug": "religious-heritage", "es": "Patrimonio religioso", "en": "Religious heritage",
     "color": "#9a4a2f", "aliases": ["religios", "iglesia", "church", "religious"]},
    {"slug": "history-independence", "es": "Historia e independencia", "en": "History & independence",
     "color": "#2a9d8f", "aliases": ["histor", "independencia", "history"]},
    {"slug": "gastronomy", "es": "Gastronomía", "en": "Gastronomy",
     "color": "#e68d72", "aliases": ["gastronom", "comida", "food", "cuisine"]},
    {"slug": "nature-landscape", "es": "Naturaleza y paisaje", "en": "Nature & landscape",
     "color": "#52b3a8", "aliases": ["natur", "paisaje", "landscape", "nature"]},
    {"slug": "traditions-culture", "es": "Tradiciones y cultura", "en": "Traditions & culture",
     "color": "#b55a3a", "aliases": ["tradicion", "cultura", "culture", "festiv"]},
]


def seed_and_backfill(apps, schema_editor):
    RouteTheme = apps.get_model("routes", "RouteTheme")
    HeritageRoute = apps.get_model("routes", "HeritageRoute")

    theme_by_slug = {}
    for order, spec in enumerate(SEED_THEMES):
        theme, _created = RouteTheme.objects.get_or_create(
            slug=spec["slug"],
            defaults={
                "name": spec["es"],
                "name_es": spec["es"],
                "name_en": spec["en"],
                "color": spec["color"],
                "order": order,
            },
        )
        theme_by_slug[spec["slug"]] = theme

    # Backfill: attach a curated theme to routes that only have a free-text one.
    for route in HeritageRoute.objects.filter(theme_category__isnull=True).exclude(theme=""):
        raw = (route.theme or "").strip().lower()
        if not raw:
            continue
        matched = None
        for spec in SEED_THEMES:
            names = [spec["es"].lower(), spec["en"].lower()] + spec["aliases"]
            if any(raw == n or n in raw or raw in n for n in names):
                matched = theme_by_slug[spec["slug"]]
                break
        if matched is not None:
            route.theme_category = matched
            route.save(update_fields=["theme_category"])


def unseed(apps, schema_editor):
    RouteTheme = apps.get_model("routes", "RouteTheme")
    HeritageRoute = apps.get_model("routes", "HeritageRoute")
    slugs = [s["slug"] for s in SEED_THEMES]
    HeritageRoute.objects.filter(theme_category__slug__in=slugs).update(theme_category=None)
    RouteTheme.objects.filter(slug__in=slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("routes", "0005_routetheme_heritageroute_theme_category"),
    ]

    operations = [
        migrations.RunPython(seed_and_backfill, unseed),
    ]
