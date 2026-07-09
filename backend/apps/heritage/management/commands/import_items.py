"""
Staff-facing bulk import of heritage items from CSV or GeoJSON (B6).

Lets a city's culture office onboard dozens of items without writing a
data/cities/<slug>.py module. Text-only by design: media files are not
imported (attach them later through the admin or the app).

CSV columns (header names case-insensitive; BOM tolerated):
    title*, description*, latitude* (or lat), longitude* (or lng/lon),
    type, category, parish, period, address, tags, external_registry_url

GeoJSON: a FeatureCollection of Point features; the same keys go in each
feature's `properties` and coordinates come from the geometry.

`type`/`category` accept a slug or exact (case-insensitive) name; `tags` is a
`;`- or `,`-separated list. Validation is all-or-nothing: every row is checked
first and any error aborts the run before a single write, so a re-run after
fixing the file never double-imports half a batch. Rows whose (title, city)
already exist are skipped unless --update.

Examples:
    manage.py import_items items.csv --city riobamba
    manage.py import_items items.geojson --city cuenca --status published
    manage.py import_items items.csv --city riobamba --dry-run
"""

import csv
import json
from pathlib import Path

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.cities.models import City
from apps.heritage.models import (
    HeritageCategory, HeritageItem, HeritageType, Parish, Tag,
)

# Header aliases → canonical row keys.
_FIELD_ALIASES = {
    'title': 'title',
    'titulo': 'title',
    'título': 'title',
    'description': 'description',
    'descripcion': 'description',
    'descripción': 'description',
    'latitude': 'latitude',
    'lat': 'latitude',
    'latitud': 'latitude',
    'longitude': 'longitude',
    'lng': 'longitude',
    'lon': 'longitude',
    'longitud': 'longitude',
    'type': 'type',
    'tipo': 'type',
    'heritage_type': 'type',
    'category': 'category',
    'categoria': 'category',
    'categoría': 'category',
    'heritage_category': 'category',
    'parish': 'parish',
    'parroquia': 'parish',
    'period': 'period',
    'periodo': 'period',
    'período': 'period',
    'historical_period': 'period',
    'address': 'address',
    'direccion': 'address',
    'dirección': 'address',
    'tags': 'tags',
    'etiquetas': 'tags',
    'external_registry_url': 'external_registry_url',
    'url': 'external_registry_url',
}

_VALID_PERIODS = [choice[0] for choice in HeritageItem.HISTORICAL_PERIOD_CHOICES]


def _normalize_keys(raw_row):
    """Map arbitrary header spellings onto canonical keys, values stripped."""
    row = {}
    for key, value in (raw_row or {}).items():
        if key is None:
            continue
        canonical = _FIELD_ALIASES.get(str(key).strip().lower())
        if canonical and value is not None:
            row[canonical] = str(value).strip()
    return row


def _split_tags(raw):
    parts = []
    for chunk in str(raw or '').replace(';', ',').split(','):
        name = ' '.join(chunk.split())
        if name and name.lower() not in [p.lower() for p in parts]:
            parts.append(name)
    return parts


class Command(BaseCommand):
    help = (
        'Bulk-import heritage items from a CSV or GeoJSON file into one city. '
        'Text-only (no media). See the module docstring for the column format.'
    )

    def add_arguments(self, parser):
        parser.add_argument('file', help='Path to the .csv or .geojson/.json file')
        parser.add_argument('--city', required=True, help='Target city slug (e.g. riobamba)')
        parser.add_argument(
            '--status',
            choices=['draft', 'pending', 'published'],
            default='pending',
            help='Status for created items (default: pending — goes through moderation)',
        )
        parser.add_argument(
            '--update',
            action='store_true',
            help='Update items that already exist (matched by title within the city) instead of skipping them',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate and report without writing anything',
        )
        parser.add_argument(
            '--contributor',
            help='Email of the user to record as contributor (default: none)',
        )
        parser.add_argument(
            '--default-type',
            help='Heritage type slug used when a row has no `type` column (e.g. tangible)',
        )
        parser.add_argument(
            '--default-category',
            help='Heritage category slug used when a row has no `category` column',
        )

    # ------------------------------------------------------------------ load

    def _load_rows(self, path: Path):
        """Return a list of (row_number, row_dict) with canonical keys."""
        suffix = path.suffix.lower()
        if suffix == '.csv':
            with path.open(encoding='utf-8-sig', newline='') as fh:
                reader = csv.DictReader(fh)
                if not reader.fieldnames:
                    raise CommandError('The CSV file has no header row.')
                # Row numbers are file lines (header = line 1).
                return [(idx, _normalize_keys(raw)) for idx, raw in enumerate(reader, start=2)]

        if suffix in ('.geojson', '.json'):
            try:
                data = json.loads(path.read_text(encoding='utf-8-sig'))
            except json.JSONDecodeError as exc:
                raise CommandError(f'Invalid JSON: {exc}')
            if not isinstance(data, dict) or data.get('type') != 'FeatureCollection':
                raise CommandError('GeoJSON must be a FeatureCollection.')
            rows = []
            for idx, feature in enumerate(data.get('features') or [], start=1):
                row = _normalize_keys((feature or {}).get('properties') or {})
                geometry = (feature or {}).get('geometry') or {}
                if geometry.get('type') == 'Point':
                    coords = geometry.get('coordinates') or []
                    if len(coords) >= 2:
                        row.setdefault('longitude', str(coords[0]))
                        row.setdefault('latitude', str(coords[1]))
                rows.append((idx, row))
            return rows

        raise CommandError('Unsupported file type: use .csv or .geojson/.json')

    # -------------------------------------------------------------- validate

    def _resolve_taxonomy(self, model, raw, default_slug, label, errors, row_no):
        """Resolve a slug-or-name to a HeritageType/HeritageCategory row."""
        value = raw or default_slug or ''
        if not value:
            errors.append(f'Row {row_no}: missing {label} (add a `{label}` column or pass --default-{label})')
            return None
        obj = model.objects.filter(slug=value).first() or model.objects.filter(name__iexact=value).first()
        if obj is None:
            errors.append(f'Row {row_no}: unknown {label} "{value}" (use a slug or exact name)')
        return obj

    def _validate(self, rows, city, options):
        """Two-phase import, phase one: turn rows into ready-to-write dicts,
        collecting EVERY error (not just the first) so the file can be fixed
        in one pass."""
        errors = []
        warnings = []
        prepared = []
        seen_titles = set()

        parishes = {p.name.lower(): p for p in Parish.objects.filter(city=city)}

        for row_no, row in rows:
            title = row.get('title', '')
            description = row.get('description', '')
            if not title:
                errors.append(f'Row {row_no}: missing title')
                continue
            if len(title) > 500:
                errors.append(f'Row {row_no}: title longer than 500 characters')
                continue
            if not description:
                errors.append(f'Row {row_no}: missing description')

            if title.lower() in seen_titles:
                errors.append(f'Row {row_no}: duplicate title "{title}" within the file')
            seen_titles.add(title.lower())

            try:
                latitude = float(row.get('latitude', ''))
                longitude = float(row.get('longitude', ''))
            except (TypeError, ValueError):
                errors.append(f'Row {row_no}: missing or non-numeric latitude/longitude')
                continue
            if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
                errors.append(f'Row {row_no}: coordinates out of range (lat {latitude}, lng {longitude})')
                continue

            heritage_type = self._resolve_taxonomy(
                HeritageType, row.get('type'), options['default_type'], 'type', errors, row_no
            )
            heritage_category = self._resolve_taxonomy(
                HeritageCategory, row.get('category'), options['default_category'], 'category', errors, row_no
            )

            period = row.get('period', '')
            if period and period not in _VALID_PERIODS:
                errors.append(
                    f'Row {row_no}: invalid period "{period}" (valid: {", ".join(_VALID_PERIODS)})'
                )

            parish = None
            parish_name = row.get('parish', '')
            if parish_name:
                parish = parishes.get(parish_name.lower())
                if parish is None:
                    warnings.append(
                        f'Row {row_no}: parish "{parish_name}" not found in {city.name} — imported without parish'
                    )

            prepared.append({
                'row_no': row_no,
                'title': title,
                'description': description,
                'location': Point(longitude, latitude, srid=4326),
                'heritage_type': heritage_type,
                'heritage_category': heritage_category,
                'historical_period': period,
                'parish': parish,
                'address': row.get('address', ''),
                'external_registry_url': row.get('external_registry_url', ''),
                'tags': _split_tags(row.get('tags')),
            })

        return prepared, errors, warnings

    # ----------------------------------------------------------------- write

    def _ensure_lom(self, item):
        """Give created items the same minimal LOM layer a wizard contribution
        gets, so /learn and the education tooling pick them up."""
        from apps.education.models import LOMEducational, LOMGeneral, LOMLifeCycle

        if hasattr(item, 'lom_general'):
            return
        lom_general = LOMGeneral.objects.create(
            heritage_item=item,
            title=item.title,
            description=item.description or '',
            language='es',
        )
        LOMLifeCycle.objects.create(
            lom_general=lom_general,
            status='final' if item.status == 'published' else 'draft',
        )
        LOMEducational.objects.create(
            lom_general=lom_general,
            learning_resource_type='narrative_text',
        )

    def handle(self, *args, **options):
        path = Path(options['file'])
        if not path.exists():
            raise CommandError(f'File not found: {path}')

        city = City.objects.filter(slug=options['city']).first()
        if city is None:
            available = ', '.join(City.objects.values_list('slug', flat=True)) or '(none)'
            raise CommandError(f'Unknown city "{options["city"]}". Available: {available}')

        contributor = None
        if options['contributor']:
            from django.contrib.auth import get_user_model
            contributor = get_user_model().objects.filter(email=options['contributor']).first()
            if contributor is None:
                raise CommandError(f'No user with email {options["contributor"]}')

        rows = self._load_rows(path)
        if not rows:
            raise CommandError('The file contains no rows.')

        prepared, errors, warnings = self._validate(rows, city, options)

        for message in warnings:
            self.stdout.write(self.style.WARNING(message))
        if errors:
            for message in errors:
                self.stdout.write(self.style.ERROR(message))
            raise CommandError(
                f'{len(errors)} error(s) in {path.name} — nothing was imported. Fix the file and re-run.'
            )

        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS(
                f'Dry run OK: {len(prepared)} row(s) valid for {city.name} '
                f'({len(warnings)} warning(s)). Nothing written.'
            ))
            return

        created = updated = skipped = 0
        with transaction.atomic():
            for entry in prepared:
                row_no = entry.pop('row_no')
                tags = [
                    tag for tag in (Tag.get_or_create_normalized(name) for name in entry.pop('tags'))
                    if tag is not None
                ]
                existing = HeritageItem.objects.filter(
                    city=city, title__iexact=entry['title']
                ).first()

                if existing is not None:
                    if not options['update']:
                        skipped += 1
                        self.stdout.write(f'Row {row_no}: "{entry["title"]}" already exists — skipped')
                        continue
                    for field, value in entry.items():
                        setattr(existing, field, value)
                    existing.save()
                    if tags:
                        existing.tags.set(tags)
                    updated += 1
                    continue

                item = HeritageItem.objects.create(
                    city=city,
                    contributor=contributor,
                    status=options['status'],
                    submission_date=timezone.now(),
                    **entry,
                )
                if tags:
                    item.tags.set(tags)
                self._ensure_lom(item)
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f'Imported into {city.name}: {created} created, {updated} updated, '
            f'{skipped} skipped ({len(warnings)} warning(s)).'
        ))
