"""Seed/refresh the curriculum-standard catalog from a data module (A.9).

Idempotent: update_or_create per (country, framework, code) — safe to re-run and
safe on top of the migration-seeded starter rows. Datasets live in
``data/curriculum/<name>.py`` (see ``ec_mineduc``) so adding a country or
framework is purely a data task, mirroring the ``data/cities/<slug>.py`` pattern.

    python manage.py seed_curriculum            # default: ec_mineduc
    python manage.py seed_curriculum --dataset ec_mineduc
"""

from importlib import import_module

from django.core.management.base import BaseCommand, CommandError

from apps.education.models import CurriculumStandard


class Command(BaseCommand):
    help = "Seed or refresh the curriculum-standard catalog from data/curriculum/<dataset>.py (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset', default='ec_mineduc',
            help="Data module under data/curriculum/ (default: ec_mineduc).",
        )

    def handle(self, *args, **options):
        dataset = options['dataset']
        try:
            module = import_module(f'data.curriculum.{dataset}')
        except ImportError as exc:
            raise CommandError(f"No curriculum dataset 'data/curriculum/{dataset}.py' ({exc})")

        country = module.COUNTRY
        framework = module.FRAMEWORK
        created = updated = 0
        for order, (code, subject, description) in enumerate(module.STANDARDS):
            defaults = {
                'subject': subject,
                'grade_level': module.grade_for(code),
                'description': description,
                'order': order,
            }
            # `description` is a translated field (es default) — keep the es
            # column explicitly in sync, like the 0011 seed migration does.
            if hasattr(CurriculumStandard, 'description_es'):
                defaults['description_es'] = description
            _, was_created = CurriculumStandard.objects.update_or_create(
                country=country, framework=framework, code=code,
                defaults=defaults,
            )
            if was_created:
                created += 1
            else:
                updated += 1

        total = CurriculumStandard.objects.filter(country=country, framework=framework).count()
        self.stdout.write(self.style.SUCCESS(
            f"Curriculum catalog '{dataset}' ({country}/{framework}): "
            f"{created} created, {updated} refreshed, {total} total."
        ))
