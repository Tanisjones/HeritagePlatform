from django.core.management.base import BaseCommand

from apps.heritage.models import HeritageItem


class Command(BaseCommand):
    help = "Seed the database with the full Heritage demo dataset (users, heritage, media, LOM, routes, moderation)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing seeded data first (dangerous; wipes several app tables).",
        )
        parser.add_argument(
            "--skip-media-downloads",
            action="store_true",
            help="Avoid downloading remote media; creates dummy media instead.",
        )

    def handle(self, *args, **options):
        from scripts import seed_heritage as seed_module

        reset = bool(options["reset"])
        download_remote_media = not bool(options["skip_media_downloads"])

        already_seeded = HeritageItem.objects.exists()
        if already_seeded and not reset:
            self.stdout.write(
                self.style.WARNING(
                    "Heritage items already exist; skipping `seed_heritage`. Use `--reset` (or `docker compose down -v`) to reseed."
                )
            )
            return

        if reset:
            self.stdout.write(self.style.WARNING("Reset requested: deleting existing data before seeding..."))
            seed_module.clean_database()

        self.stdout.write("Seeding full Heritage dataset...")
        seed_module.create_initial_data(download_remote_media=download_remote_media)
        self.stdout.write(self.style.SUCCESS("Heritage seed complete."))

