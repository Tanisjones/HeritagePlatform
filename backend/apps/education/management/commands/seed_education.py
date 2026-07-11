"""Seed shared educational content (EducationalResource + LessonPlan) for a city.

Idempotent, mirroring ``seed_curriculum`` / ``seed_city``: datasets live in
``data/education/<slug>.py`` (RESOURCES + LESSON_PLANS) so authoring content for
a city is a pure data task. Records are keyed by (title, city) via
``update_or_create`` — safe to re-run. Content that references heritage items,
routes or curriculum standards resolves those by their natural keys at seed
time and warns (never crashes) on a miss, so it degrades gracefully if a city's
heritage hasn't been seeded yet.

    python manage.py seed_education riobamba
    python manage.py seed_education tarragona

Requires the city to exist (run ``seed_city <slug>`` first). Rich-text fields
are sanitized on write with the same allowlist the API serializer uses, so
seeded HTML is identical to user-authored HTML.
"""

from importlib import import_module

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.cities.models import City
from apps.education.models import (
    CurriculumStandard,
    EducationalResource,
    LessonActivity,
    LessonPlan,
    ResourceCategory,
    ResourceType,
)
from apps.education.sanitize import sanitize_html
from apps.heritage.models import HeritageItem
from apps.routes.models import HeritageRoute

# Canonical resource types/categories created on demand (the tables ship empty).
_RESOURCE_TYPES = [
    ("Artículo", "articulo"),
    ("Guía didáctica", "guia-didactica"),
    ("Ficha de actividad", "ficha-actividad"),
    ("Galería comentada", "galeria-comentada"),
]
_RESOURCE_CATEGORIES = [
    ("Historia", "historia"),
    ("Arte y Arquitectura", "arte-arquitectura"),
    ("Gastronomía", "gastronomia"),
    ("Tradiciones", "tradiciones"),
    ("Patrimonio", "patrimonio"),
]


class Command(BaseCommand):
    help = (
        "Seed shared educational content (resources + lesson plans) for a city "
        "from data/education/<slug>.py (idempotent). Run seed_city <slug> first."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "slug",
            help="Education data module under data/education/ (dashes -> underscores).",
        )
        parser.add_argument(
            "--author-email",
            default=None,
            help="Email of the author user (default: the seeded curator, else the first superuser).",
        )

    def handle(self, *args, **options):
        module_name = options["slug"].replace("-", "_")
        try:
            module = import_module(f"data.education.{module_name}")
        except ImportError as exc:
            raise CommandError(
                f"No education data module 'data/education/{module_name}.py' ({exc})."
            )

        city_slug = getattr(module, "CITY_SLUG", options["slug"])
        try:
            city = City.objects.get(slug=city_slug)
        except City.DoesNotExist:
            raise CommandError(
                f"City '{city_slug}' does not exist. Run `seed_city {city_slug}` first."
            )

        author = self._resolve_author(options["author_email"])

        types = {slug: self._get_type(name, slug) for name, slug in _RESOURCE_TYPES}
        cats = {slug: self._get_category(name, slug) for name, slug in _RESOURCE_CATEGORIES}

        with transaction.atomic():
            n_res = self._seed_resources(module, city, author, types, cats)
            n_plans, n_acts = self._seed_lesson_plans(module, city, author)

        self.stdout.write(self.style.SUCCESS(
            f"Education content for '{city.slug}': {n_res} resources, "
            f"{n_plans} lesson plans ({n_acts} activities)."
        ))

    # --- helpers ------------------------------------------------------------

    def _resolve_author(self, email):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if email:
            user = User.objects.filter(email=email).first()
            if not user:
                raise CommandError(f"No user with email '{email}'.")
            return user
        # Prefer the seeded test curator, else any superuser.
        return (
            User.objects.filter(email="b@b.com").first()
            or User.objects.filter(is_superuser=True).order_by("id").first()
        )

    def _get_type(self, name, slug):
        obj, _ = ResourceType.objects.get_or_create(slug=slug, defaults={"name": name})
        return obj

    def _get_category(self, name, slug):
        obj, _ = ResourceCategory.objects.get_or_create(slug=slug, defaults={"name": name})
        return obj

    def _resolve_items(self, city, titles):
        """Resolve heritage items by title within the city; warn on misses."""
        found = []
        for t in titles:
            item = HeritageItem.objects.filter(city=city, title=t).first()
            if item:
                found.append(item)
            else:
                self.stdout.write(self.style.WARNING(
                    f"  · heritage item not found (skipped link): {t!r}"
                ))
        return found

    def _seed_resources(self, module, city, author, types, cats):
        count = 0
        for r in getattr(module, "RESOURCES", []):
            defaults = {
                "description": r["description"],
                "content": sanitize_html(r["content"]),
                "author": author,
                "resource_type": types.get(r.get("type", "articulo")),
                "category": cats.get(r.get("category", "patrimonio")),
            }
            obj, _ = EducationalResource.objects.update_or_create(
                title=r["title"], city=city, defaults=defaults,
            )
            items = self._resolve_items(city, r.get("related_items", []))
            obj.related_heritage_items.set(items)
            count += 1
            self.stdout.write(f"  resource: {obj.title}")
        return count

    def _seed_lesson_plans(self, module, city, author):
        n_plans = n_acts = 0
        for p in getattr(module, "LESSON_PLANS", []):
            route = None
            if p.get("route_title"):
                route = HeritageRoute.objects.filter(city=city, title=p["route_title"]).first()
                if not route:
                    self.stdout.write(self.style.WARNING(
                        f"  · route not found (skipped link): {p['route_title']!r}"
                    ))
            defaults = {
                "summary": p.get("summary", ""),
                "objectives": p.get("objectives", []),
                "subject": p.get("subject", ""),
                "grade_level": p.get("grade_level", ""),
                "audience": p.get("audience", "teacher"),
                "curriculum_alignment": p.get("curriculum_alignment", ""),
                "pedagogical_approach": p.get("pedagogical_approach", ""),
                "estimated_total_minutes": p.get("estimated_total_minutes"),
                "status": p.get("status", LessonPlan.STATUS_PUBLISHED),
                "visibility": p.get("visibility", LessonPlan.VISIBILITY_PUBLIC),
                "author": author,
                "related_route": route,
            }
            plan, _ = LessonPlan.objects.update_or_create(
                title=p["title"], city=city, defaults=defaults,
            )

            # Curriculum standards (by code; country-scoped to the city).
            codes = p.get("standard_codes", [])
            if codes:
                stds = CurriculumStandard.objects.filter(
                    country=city.country, code__in=codes
                )
                missing = set(codes) - set(stds.values_list("code", flat=True))
                for m in sorted(missing):
                    self.stdout.write(self.style.WARNING(
                        f"  · standard not found (skipped link): {m}"
                    ))
                plan.standards.set(stds)

            # Activities: positional, so rebuild them on every run.
            plan.activities.all().delete()
            for order, a in enumerate(p.get("activities", []), start=1):
                item = None
                if a.get("heritage_item_title"):
                    item = HeritageItem.objects.filter(
                        city=city, title=a["heritage_item_title"]
                    ).first()
                    if not item:
                        self.stdout.write(self.style.WARNING(
                            f"  · activity item not found (unlinked): {a['heritage_item_title']!r}"
                        ))
                LessonActivity.objects.create(
                    lesson=plan,
                    order=order,
                    title=a["title"],
                    activity_type=a.get("activity_type", "explore"),
                    instructions=sanitize_html(a.get("instructions", "")),
                    duration_minutes=a.get("duration_minutes"),
                    materials=a.get("materials", ""),
                    heritage_item=item,
                    route=route if a.get("bind_route") else None,
                )
                n_acts += 1
            n_plans += 1
            self.stdout.write(f"  lesson plan: {plan.title} ({plan.activities.count()} activities)")
        return n_plans, n_acts
