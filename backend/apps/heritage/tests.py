import json
import tempfile
from pathlib import Path

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient
from rest_framework import status
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish, MediaFile, Tag
from apps.cities.testing import make_city, make_city_curator

User = get_user_model()

class HeritageModelTest(TestCase):
    def setUp(self):
        self.city = make_city()
        self.user = User.objects.create_user(email='contributor@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parent_cat = HeritageCategory.objects.create(name='Parent', slug='parent')
        self.category.parent = self.parent_cat
        self.category.save()
        self.parish = Parish.objects.create(city=self.city, name='Test Parish', canton='Riobamba')

    def test_create_heritage_item(self):
        item = HeritageItem.objects.create(city=self.city, 
            title='Test Item',
            description='Test Description',
            heritage_type=self.type,
            heritage_category=self.category,
            parish=self.parish,
            location=Point(-78.6, -1.6),
            contributor=self.user,
            status='published'
        )
        self.assertEqual(item.title, 'Test Item')
        self.assertEqual(item.status, 'published')
        self.assertTrue(item.location)

    def test_category_hierarchy(self):
        self.assertEqual(self.category.parent, self.parent_cat)
        self.assertEqual(self.category.get_ancestors(), [self.parent_cat])

    def test_parish_str(self):
        self.assertEqual(str(self.parish), 'Test Parish, Riobamba')

    def test_media_file_creation(self):
        media = MediaFile.objects.create(
            file='test.jpg',
            file_type='image',
            uploaded_by=self.user
        )
        self.assertEqual(str(media), 'image: test.jpg')

    def test_media_file_type_extension_mismatch_rejected(self):
        with self.assertRaises(ValidationError):
            MediaFile.objects.create(
                file='test.jpg',
                file_type='audio',
                uploaded_by=self.user
            )

    def test_text_resource_as_document_txt_allowed(self):
        media = MediaFile.objects.create(
            file='test.txt',
            file_type='document',
            uploaded_by=self.user
        )
        self.assertEqual(media.file_type, 'document')

class HeritageAPITest(TestCase):
    def setUp(self):
        self.city = make_city()
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(city=self.city, name='Test Parish', canton='Riobamba')
        
        self.item1 = HeritageItem.objects.create(city=self.city, 
            title='Public Item',
            description='Public Desc',
            heritage_type=self.type,
            heritage_category=self.category,
            parish=self.parish,
            location=Point(0,0),
            status='published'
        )
        self.item2 = HeritageItem.objects.create(city=self.city, 
            title='Draft Item',
            description='Draft Desc',
            heritage_type=self.type,
            heritage_category=self.category,
            parish=self.parish,
            location=Point(0,0),
            contributor=self.user,
            status='draft'
        )

    def test_list_published_items_anonymous(self):
        response = self.client.get('/api/v1/heritage-items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see only published
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Public Item')

    def test_list_items_authenticated_author(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/heritage-items/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should see published + own draft
        self.assertEqual(len(response.data['results']), 2)

    def test_search_filter(self):
        response = self.client.get('/api/v1/heritage-items/?search=Public')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['title'], 'Public Item')

    def test_nearby_filter(self):
        # Item at 0,0. Query near 0,0
        response = self.client.get('/api/v1/heritage-items/nearby/?latitude=0&longitude=0&radius=10')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

        # Query far away
        response = self.client.get('/api/v1/heritage-items/nearby/?latitude=50&longitude=50&radius=10')
        self.assertEqual(len(response.data['results']), 0)


class HeritageItemMassAssignmentTest(TestCase):
    """Regression guard for the HeritageItem write serializer field-pinning
    (Vuln 3, defense-in-depth).

    The /heritage-items/ write endpoint is already curator/staff-gated
    (IsModeratorOrReadOnly) — a plain tourist is 403 and uses /contributions/
    instead. But even the privileged actor who *can* reach it must not be able to
    spoof server-controlled fields: create forces status='pending' and
    contributor=<request.user>, and status transitions require staff."""

    def setUp(self):

        self.city = make_city()
        from apps.users.models import UserProfile, UserRole
        self.client = APIClient()
        # A curator can reach the write endpoint (role slug 'curator').
        self.curator_role, _ = UserRole.objects.get_or_create(
            slug='curator', defaults={'name': 'Curator'}
        )
        self.curator = User.objects.create_user(email='curator@example.com', password='pw')
        UserProfile.objects.create(user=self.curator, role=self.curator_role)
        from apps.cities.testing import make_city_curator
        make_city_curator(self.curator, self.city)
        self.victim = User.objects.create_user(email='victim@example.com', password='pw')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(city=self.city, name='Test Parish', canton='Riobamba')

    def _payload(self, **extra):
        body = {
            'title': 'Injected',
            'description': 'x',
            'heritage_type': self.type.id,
            'heritage_category': self.category.id,
            'parish': self.parish.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
        }
        body.update(extra)
        return body

    def test_tourist_cannot_write_to_heritage_items_endpoint(self):
        """The direct write endpoint is curator/staff-only; tourists use /contributions/."""
        tourist = User.objects.create_user(email='tourist@example.com', password='pw')
        self.client.force_authenticate(user=tourist)
        resp = self.client.post('/api/v1/heritage-items/', self._payload(), format='json')
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)

    def test_privileged_create_pins_status_and_contributor(self):
        self.client.force_authenticate(user=self.curator)
        resp = self.client.post(
            '/api/v1/heritage-items/',
            self._payload(status='published', contributor=str(self.victim.id)),
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        item = HeritageItem.objects.get(id=resp.data['id'])
        # Server-controlled fields ignore the injected values, even for a curator.
        self.assertEqual(item.status, 'pending')
        self.assertEqual(item.contributor_id, self.curator.id)

    def test_non_staff_cannot_change_status_on_update(self):
        # A curator owns/reaches the item but is not staff — status stays locked.
        self.client.force_authenticate(user=self.curator)
        item = HeritageItem.objects.create(city=self.city,
            title='Mine', description='x', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish,
            location=Point(-78.6, -1.6), contributor=self.curator, status='pending',
        )
        resp = self.client.patch(
            f'/api/v1/heritage-items/{item.id}/', {'status': 'published'}, format='json'
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN, resp.content)
        item.refresh_from_db()
        self.assertEqual(item.status, 'pending')


class HeritageTagsTest(TestCase):
    """B1 — free-form tags: normalized write path, filters, and the chips
    catalog endpoint."""

    def setUp(self):
        self.city = make_city()
        self.client = APIClient()
        self.user = User.objects.create_user(email='tagger@example.com', password='pw')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(city=self.city, name='Centro')

    def _make_item(self, title, status='published', city=None, tags=()):
        item = HeritageItem.objects.create(
            city=city or self.city, title=title, description='d',
            heritage_type=self.type, heritage_category=self.category,
            parish=self.parish if (city or self.city) == self.city else None,
            location=Point(-78.6, -1.6), status=status,
        )
        for name in tags:
            item.tags.add(Tag.get_or_create_normalized(name))
        return item

    def test_contribution_accepts_and_normalizes_tags(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/v1/contributions/', {
            'title': 'Casa de la Independencia',
            'description': 'x',
            'heritage_type': self.type.id,
            'heritage_category': self.category.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
            # "  Barroco " normalizes to "Barroco"; "barroco" is the same slug → deduped
            'tags': ['Independencia', '  Barroco ', 'barroco'],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        item = HeritageItem.objects.get(title='Casa de la Independencia')
        self.assertEqual(
            sorted(t.slug for t in item.tags.all()), ['barroco', 'independencia']
        )
        # The list of names round-trips on the read serializers.
        self.assertIn('Independencia', resp.data['tags'])

    def test_contribution_rejects_more_than_ten_tags(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/v1/contributions/', {
            'title': 'Demasiadas etiquetas',
            'description': 'x',
            'heritage_type': self.type.id,
            'heritage_category': self.category.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
            'tags': [f'tag-{i}' for i in range(11)],
        }, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('tags', resp.data)

    def test_tag_filter_by_slug_and_name(self):
        self._make_item('Tagged', tags=['Gastronomía Andina'])
        self._make_item('Untagged')
        for value in ('gastronomia-andina', 'gastronomía andina'):
            resp = self.client.get('/api/v1/heritage-items/', {'tag': value})
            titles = [r['title'] for r in resp.data['results']]
            self.assertEqual(titles, ['Tagged'], value)

    def test_search_matches_tag_names(self):
        self._make_item('Sitio X', tags=['independencia'])
        self._make_item('Sitio Y')
        resp = self.client.get('/api/v1/heritage-items/', {'search': 'independencia'})
        titles = [r['title'] for r in resp.data['results']]
        self.assertEqual(titles, ['Sitio X'])

    def test_tags_catalog_counts_published_and_scopes_by_city(self):
        other_city = make_city(slug='other-city', name='Other City')
        self._make_item('Pub 1', tags=['barroco', 'colonial'])
        self._make_item('Pub 2', tags=['barroco'])
        self._make_item('Hidden draft', status='draft', tags=['barroco'])
        self._make_item('Elsewhere', city=other_city, tags=['barroco'])

        resp = self.client.get('/api/v1/heritage-items/tags/', HTTP_X_CITY=self.city.slug)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        by_slug = {t['slug']: t['count'] for t in resp.data}
        # Draft and other-city items don't count.
        self.assertEqual(by_slug['barroco'], 2)
        self.assertEqual(by_slug['colonial'], 1)

        # Unscoped (no city header) counts across cities — backwards-compatible.
        resp = self.client.get('/api/v1/heritage-items/tags/')
        by_slug = {t['slug']: t['count'] for t in resp.data}
        self.assertEqual(by_slug['barroco'], 3)


class ContributionDraftTest(TestCase):
    """B2 — save-as-draft keeps items out of the queue until submit."""

    def setUp(self):
        self.city = make_city()
        self.client = APIClient()
        self.user = User.objects.create_user(email='drafter@example.com', password='pw')
        self.other = User.objects.create_user(email='other@example.com', password='pw')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')

    def _post_contribution(self, **extra):
        payload = {
            'title': 'Borrador',
            'description': 'x',
            'heritage_type': self.type.id,
            'heritage_category': self.category.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
        }
        payload.update(extra)
        return self.client.post('/api/v1/contributions/', payload, format='json')

    def test_save_as_draft_creates_draft_without_points(self):
        from apps.gamification.models import PointTransaction

        self.client.force_authenticate(user=self.user)
        resp = self._post_contribution(save_as_draft=True)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        item = HeritageItem.objects.get(title='Borrador')
        self.assertEqual(item.status, 'draft')
        # Points are deferred to the real submission.
        self.assertFalse(PointTransaction.objects.filter(user=self.user).exists())

    def test_draft_invisible_to_public(self):
        self.client.force_authenticate(user=self.user)
        self._post_contribution(save_as_draft=True)
        self.client.force_authenticate(user=None)
        resp = self.client.get('/api/v1/heritage-items/')
        self.assertEqual(len(resp.data['results']), 0)

    def test_submit_moves_draft_to_pending_and_awards_points(self):
        from apps.gamification.models import PointTransaction

        self.client.force_authenticate(user=self.user)
        resp = self._post_contribution(save_as_draft=True)
        item_id = resp.data['id']
        resp = self.client.post(f'/api/v1/my-contributions/{item_id}/submit/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        item = HeritageItem.objects.get(id=item_id)
        self.assertEqual(item.status, 'pending')
        self.assertIsNotNone(item.submission_date)
        self.assertTrue(PointTransaction.objects.filter(user=self.user).exists())

    def test_submit_rejects_non_drafts(self):
        self.client.force_authenticate(user=self.user)
        resp = self._post_contribution()  # regular pending submission
        item_id = resp.data['id']
        resp = self.client.post(f'/api/v1/my-contributions/{item_id}/submit/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_cannot_submit_someone_elses_draft(self):
        self.client.force_authenticate(user=self.user)
        resp = self._post_contribution(save_as_draft=True)
        item_id = resp.data['id']
        self.client.force_authenticate(user=self.other)
        resp = self.client.post(f'/api/v1/my-contributions/{item_id}/submit/')
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class CategorySuggestionTest(TestCase):
    """B7 — a free-text category suggestion notifies the item's city curators."""

    def setUp(self):
        self.city = make_city()
        self.other_city = make_city(slug='other-city', name='Other City')
        self.client = APIClient()
        self.user = User.objects.create_user(email='suggester@example.com', password='pw')
        self.curator = User.objects.create_user(email='curator@example.com', password='pw')
        self.far_curator = User.objects.create_user(email='far@example.com', password='pw')
        make_city_curator(self.curator, self.city)
        make_city_curator(self.far_curator, self.other_city)
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')

    def test_suggestion_notifies_only_city_curators(self):
        from apps.notifications.models import UserNotification

        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/v1/contributions/', {
            'title': 'Molino antiguo',
            'description': 'x',
            'heritage_type': self.type.id,
            'heritage_category': self.category.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
            'suggested_category': 'Patrimonio industrial',
        }, format='json', HTTP_X_CITY=self.city.slug)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        notes = UserNotification.objects.filter(notification_type='category_suggestion')
        self.assertEqual(notes.count(), 1)
        note = notes.get()
        self.assertEqual(note.recipient, self.curator)
        self.assertIn('Patrimonio industrial', note.message)
        self.assertIn('Molino antiguo', note.message)

    def test_blank_suggestion_notifies_nobody(self):
        from apps.notifications.models import UserNotification

        self.client.force_authenticate(user=self.user)
        resp = self.client.post('/api/v1/contributions/', {
            'title': 'Sin sugerencia',
            'description': 'x',
            'heritage_type': self.type.id,
            'heritage_category': self.category.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
            'suggested_category': '   ',
        }, format='json', HTTP_X_CITY=self.city.slug)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertFalse(
            UserNotification.objects.filter(notification_type='category_suggestion').exists()
        )


class ImportItemsCommandTest(TestCase):
    """B6 — CSV/GeoJSON bulk import: all-or-nothing validation, idempotent
    re-runs, tags + LOM layer on created items."""

    def setUp(self):
        self.city = make_city()
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Arquitectura', slug='architecture')
        self.parish = Parish.objects.create(city=self.city, name='Centro')

    def _write(self, name, content):
        path = Path(tempfile.mkdtemp()) / name
        path.write_text(content, encoding='utf-8')
        return str(path)

    def _csv(self, rows_text):
        header = 'title,description,latitude,longitude,type,category,parish,period,tags\n'
        return self._write('items.csv', header + rows_text)

    def test_csv_import_creates_items_with_tags_and_lom(self):
        path = self._csv(
            'Iglesia Mayor,Templo colonial,-1.67,-78.65,tangible,architecture,Centro,colonial,"barroco;religión"\n'
            'Casa Vieja,Casona,-1.68,-78.64,tangible,Arquitectura,,,\n'
        )
        call_command('import_items', path, '--city', self.city.slug)
        self.assertEqual(HeritageItem.objects.count(), 2)
        item = HeritageItem.objects.get(title='Iglesia Mayor')
        self.assertEqual(item.status, 'pending')
        self.assertEqual(item.city, self.city)
        self.assertEqual(item.parish, self.parish)
        self.assertEqual(item.historical_period, 'colonial')
        self.assertEqual(sorted(t.slug for t in item.tags.all()), ['barroco', 'religion'])
        self.assertTrue(hasattr(item, 'lom_general'))
        # Category resolved by exact name (not slug) on the second row.
        self.assertEqual(HeritageItem.objects.get(title='Casa Vieja').heritage_category, self.category)

    def test_invalid_row_aborts_whole_import(self):
        path = self._csv(
            'Buena,Desc,-1.67,-78.65,tangible,architecture,,,\n'
            'Mala,Desc,not-a-number,-78.65,tangible,architecture,,,\n'
        )
        with self.assertRaises(CommandError):
            call_command('import_items', path, '--city', self.city.slug)
        self.assertEqual(HeritageItem.objects.count(), 0)

    def test_dry_run_writes_nothing(self):
        path = self._csv('Iglesia,Desc,-1.67,-78.65,tangible,architecture,,,\n')
        call_command('import_items', path, '--city', self.city.slug, '--dry-run')
        self.assertEqual(HeritageItem.objects.count(), 0)

    def test_existing_titles_skipped_unless_update(self):
        HeritageItem.objects.create(
            city=self.city, title='Iglesia Mayor', description='old',
            heritage_type=self.type, heritage_category=self.category,
            location=Point(-78.65, -1.67), status='published',
        )
        path = self._csv('Iglesia Mayor,Nueva descripción,-1.67,-78.65,tangible,architecture,,,\n')

        call_command('import_items', path, '--city', self.city.slug)
        item = HeritageItem.objects.get(title='Iglesia Mayor')
        self.assertEqual(item.description, 'old')  # skipped
        self.assertEqual(item.status, 'published')

        call_command('import_items', path, '--city', self.city.slug, '--update')
        item.refresh_from_db()
        self.assertEqual(item.description, 'Nueva descripción')
        self.assertEqual(item.status, 'published')  # update never touches status

    def test_geojson_import_with_status_and_defaults(self):
        payload = {
            'type': 'FeatureCollection',
            'features': [{
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [-78.65, -1.67]},
                'properties': {'title': 'Parque Central', 'description': 'Plaza principal'},
            }],
        }
        path = self._write('items.geojson', json.dumps(payload))
        call_command(
            'import_items', path, '--city', self.city.slug,
            '--status', 'published', '--default-type', 'tangible',
            '--default-category', 'architecture',
        )
        item = HeritageItem.objects.get(title='Parque Central')
        self.assertEqual(item.status, 'published')
        self.assertAlmostEqual(item.location.x, -78.65)
        self.assertEqual(item.heritage_type, self.type)
