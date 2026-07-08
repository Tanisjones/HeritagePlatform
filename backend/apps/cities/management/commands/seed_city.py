from importlib import import_module

from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Seed one city's demo dataset from backend/data/cities/<slug>.py "
        "(e.g. `seed_city riobamba`). Onboarding a new city = adding one data "
        "module with CITY/PARISHES/ITEMS/ROUTES and running this command."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "slug",
            help="City data module under data/cities/ (dashes become underscores).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Wipe the seeded content tables first (affects ALL cities — same "
                 "behavior as the legacy seed_heritage --reset).",
        )
        parser.add_argument(
            "--skip-media-downloads",
            action="store_true",
            help="Avoid downloading remote media; creates dummy media instead.",
        )

    def handle(self, *args, **options):
        module_name = options["slug"].replace("-", "_")
        try:
            city_module = import_module(f"data.cities.{module_name}")
        except ImportError as exc:
            raise CommandError(
                f"No city data module 'data/cities/{module_name}.py' ({exc})."
            )

        from scripts.seed_city_engine import clean_database, create_city_data

        if options["reset"]:
            self.stdout.write(self.style.WARNING(
                "Reset requested: wiping seeded content tables (all cities)..."
            ))
            clean_database()

        self.stdout.write(f"Seeding city dataset '{options['slug']}'...")
        create_city_data(
            city_module,
            download_remote_media=not options["skip_media_downloads"],
        )
        self.stdout.write(self.style.SUCCESS("City seed complete."))
