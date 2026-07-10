"""
Staff-facing city onboarding (E2).

Creating a City in the admin gives you the record and the map framing —
nothing else. This command does the rest of the checklist in one shot,
idempotently:

  * ensures the platform base taxonomies exist (heritage types + categories,
    same slugs the seeders use — they are global, so this is a no-op on any
    instance that has ever been seeded);
  * creates the city's parishes by name;
  * grants per-city curator roles by user email;
  * prints a readiness checklist either way.

`--check` runs the checklist only (no writes). Demo content stays a separate
decision: `manage.py seed_city <slug>` when a data module exists.

Examples:
    manage.py bootstrap_city cuenca --parishes "El Sagrario,San Blas" --curator ana@cuenca.gob.ec
    manage.py bootstrap_city cuenca --check
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.cities.models import City, CityRole
from apps.heritage.models import HeritageCategory, HeritageItem, HeritageType, Parish

# Kept in sync with scripts/seed_city_engine.py — same slugs, so bootstrap and
# seeding converge on one taxonomy.
BASE_TYPES = [
    {"name": "Tangible", "slug": "tangible", "description": "Artefactos físicos, arquitectura y sitios."},
    {"name": "Intangible", "slug": "intangible", "description": "Tradiciones, historia oral, habilidades y conocimiento."},
]
BASE_CATEGORIES = [
    {"name": "Arquitectura", "slug": "architecture", "order": 1, "icon": "building"},
    {"name": "Arqueología", "slug": "archaeology", "order": 2, "icon": "archaeology"},
    {"name": "Gastronomía", "slug": "gastronomy", "order": 3, "icon": "utensils"},
    {"name": "Música y Danza", "slug": "music-dance", "order": 4, "icon": "music"},
    {"name": "Tradiciones Orales", "slug": "oral-traditions", "order": 5, "icon": "comments"},
    {"name": "Festividades", "slug": "festivities", "order": 6, "icon": "calendar-star"},
]


class Command(BaseCommand):
    help = (
        'Onboard an existing City: ensure base taxonomies, create parishes, '
        'grant curators, and print a readiness checklist. Idempotent.'
    )

    def add_arguments(self, parser):
        parser.add_argument('slug', help='Slug of an existing city (create it in the admin first)')
        parser.add_argument(
            '--parishes',
            help='Comma-separated parish names to create (e.g. "El Sagrario,San Blas")',
        )
        parser.add_argument(
            '--curator',
            action='append',
            default=[],
            metavar='EMAIL',
            help='Email of an existing user to grant the curator role (repeatable)',
        )
        parser.add_argument(
            '--check',
            action='store_true',
            help='Print the readiness checklist only; write nothing',
        )

    def handle(self, *args, **options):
        city = City.objects.filter(slug=options['slug']).first()
        if city is None:
            available = ', '.join(City.objects.values_list('slug', flat=True)) or '(none)'
            raise CommandError(
                f'Unknown city "{options["slug"]}" — create it in the Django admin first '
                f'(name, slug and map center). Available: {available}'
            )

        if not options['check']:
            self._bootstrap(city, options)

        self._checklist(city)

    # ------------------------------------------------------------------ write

    def _bootstrap(self, city, options):
        User = get_user_model()

        # Validate curators up front: all-or-nothing, so a typo doesn't leave
        # a half-granted roster.
        curators = []
        missing = []
        for email in options['curator']:
            user = User.objects.filter(email=email).first()
            (curators.append(user) if user else missing.append(email))
        if missing:
            raise CommandError(
                'No user with email: ' + ', '.join(missing)
                + '. Users must register (or be created in the admin) before they can be granted.'
            )

        for definition in BASE_TYPES:
            _, created = HeritageType.objects.get_or_create(slug=definition['slug'], defaults=definition)
            if created:
                self.stdout.write(f'Created heritage type "{definition["name"]}"')
        for definition in BASE_CATEGORIES:
            _, created = HeritageCategory.objects.get_or_create(slug=definition['slug'], defaults=definition)
            if created:
                self.stdout.write(f'Created category "{definition["name"]}"')

        for raw in (options['parishes'] or '').split(','):
            name = ' '.join(raw.split())
            if not name:
                continue
            _, created = Parish.objects.get_or_create(name=name, city=city)
            self.stdout.write(
                f'Parish "{name}": {"created" if created else "already exists"}'
            )

        for user in curators:
            _, created = CityRole.objects.get_or_create(
                user=user, city=city, role=CityRole.ROLE_CURATOR
            )
            self.stdout.write(
                f'Curator {user.email}: {"granted" if created else "already granted"}'
            )

    # ------------------------------------------------------------------ check

    def _checklist(self, city):
        parishes = Parish.objects.filter(city=city).count()
        curators = CityRole.objects.filter(city=city, role=CityRole.ROLE_CURATOR).count()
        items = HeritageItem.objects.filter(city=city)
        published = items.filter(status='published').count()
        pending = items.filter(status='pending').count()

        def mark(ok):
            return self.style.SUCCESS('✓') if ok else self.style.WARNING('✗')

        self.stdout.write('')
        self.stdout.write(self.style.MIGRATE_HEADING(f'Readiness — {city.name} ({city.slug})'))
        self.stdout.write(f'  {mark(city.is_active)} active')
        self.stdout.write(f'  {mark(city.center is not None)} map center set (zoom {city.default_zoom})')
        self.stdout.write(f'  {mark(bool(city.hero_image))} hero image')
        self.stdout.write(f'  {mark(bool(city.brand_color))} brand color' + (f' ({city.brand_color})' if city.brand_color else ''))
        self.stdout.write(f'  {mark(bool(city.logo))} logo')
        self.stdout.write(f'  {mark(parishes > 0)} parishes: {parishes}')
        self.stdout.write(f'  {mark(curators > 0)} curators: {curators}')
        self.stdout.write(f'  {mark(published > 0)} published items: {published} (pending: {pending})')
        self.stdout.write('')
        if published == 0:
            self.stdout.write(
                '  Content is empty. Options: manage.py seed_city '
                f'{city.slug} (needs data/cities/{city.slug}.py) or '
                f'manage.py import_items <file> --city {city.slug}.'
            )
