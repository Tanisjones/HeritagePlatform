from importlib import import_module

from django.apps import apps as global_apps
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.users.models import UserProfile, UserRole

from .models import CityRole
from .testing import make_city, make_city_curator

User = get_user_model()


class CityEndpointTests(APITestCase):
    """Public /api/v1/cities/ catalog."""

    def setUp(self):
        # 'riobamba' already exists in every test DB (seeded by cities.0002).
        self.active = make_city(slug='cuenca-test', name='Cuenca Test')
        self.inactive = make_city(slug='ghost-town', name='Ghost Town', is_active=False)

    def test_list_returns_only_active_cities(self):
        response = self.client.get('/api/v1/cities/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slugs = {city['slug'] for city in response.data}
        self.assertIn('riobamba', slugs)
        self.assertIn('cuenca-test', slugs)
        self.assertNotIn('ghost-town', slugs)

    def test_retrieve_by_slug_exposes_map_framing(self):
        response = self.client.get('/api/v1/cities/riobamba/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Riobamba')
        self.assertEqual(response.data['country'], 'EC')
        self.assertEqual(response.data['center']['type'], 'Point')
        # GeoJSON order: [lng, lat]
        lng, lat = response.data['center']['coordinates']
        self.assertAlmostEqual(lng, -78.6479, places=4)
        self.assertAlmostEqual(lat, -1.6735, places=4)
        self.assertEqual(response.data['default_zoom'], 13)

    def test_inactive_city_is_not_retrievable(self):
        response = self.client.get('/api/v1/cities/ghost-town/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class CityRoleBackfillTests(APITestCase):
    """The 0003 data migration body, called directly against the live registry."""

    def _run_backfill(self):
        module = import_module('apps.cities.migrations.0003_backfill_riobamba_city_roles')
        module.backfill_city_roles(global_apps, None)

    def _user_with_role(self, email, slug, name):
        role, _ = UserRole.objects.get_or_create(slug=slug, defaults={'name': name})
        user = User.objects.create_user(email=email, password='password123')
        UserProfile.objects.create(user=user, role=role)
        return user

    def test_backfill_grants_riobamba_role_to_governance_profiles(self):
        curator = self._user_with_role('cur@example.com', 'curator', 'Curator')
        moderator = self._user_with_role('mod@example.com', 'moderator', 'Moderator')
        self._run_backfill()
        self.assertTrue(
            CityRole.objects.filter(user=curator, city__slug='riobamba', role='curator').exists()
        )
        self.assertTrue(
            CityRole.objects.filter(user=moderator, city__slug='riobamba', role='moderator').exists()
        )

    def test_backfill_ignores_non_governance_roles_and_is_idempotent(self):
        teacher = self._user_with_role('tea@example.com', 'teacher', 'Teacher')
        curator = self._user_with_role('cur2@example.com', 'curator', 'Curator')
        self._run_backfill()
        self._run_backfill()
        self.assertFalse(CityRole.objects.filter(user=teacher).exists())
        self.assertEqual(CityRole.objects.filter(user=curator).count(), 1)


class CityHelperTests(APITestCase):
    def test_make_city_curator_is_idempotent(self):
        city = make_city(slug='helper-city')
        user = User.objects.create_user(email='helper@example.com', password='password123')
        make_city_curator(user, city)
        make_city_curator(user, city)
        self.assertEqual(CityRole.objects.filter(user=user, city=city).count(), 1)


class CityScopingTests(APITestCase):
    """?city= / X-City scoping across the content endpoints."""

    def setUp(self):
        from django.contrib.gis.geos import Point
        from apps.heritage.models import HeritageCategory, HeritageItem, HeritageType, Parish
        from apps.routes.models import HeritageRoute

        self.city_a = make_city(slug='city-a', name='City A')
        self.city_b = make_city(slug='city-b', name='City B')
        self.h_type = HeritageType.objects.create(name='Scope T', slug='scope-t')
        self.h_cat = HeritageCategory.objects.create(name='Scope C', slug='scope-c')
        self.parish_a = Parish.objects.create(name='Parish A', city=self.city_a)
        self.parish_b = Parish.objects.create(name='Parish B', city=self.city_b)

        def item(city, parish, title, status='published'):
            return HeritageItem.objects.create(
                city=city, title=title, description='d',
                location=Point(-78.6, -1.6, srid=4326),
                heritage_type=self.h_type, heritage_category=self.h_cat,
                parish=parish, status=status,
            )

        self.item_a = item(self.city_a, self.parish_a, 'Item In A')
        self.item_b = item(self.city_b, self.parish_b, 'Item In B')
        self.pending_a = item(self.city_a, self.parish_a, 'Pending A', status='pending')
        self.pending_b = item(self.city_b, self.parish_b, 'Pending B', status='pending')

        self.route_a = HeritageRoute.objects.create(
            city=self.city_a, title='Route A', description='d', status='published')
        self.route_b = HeritageRoute.objects.create(
            city=self.city_b, title='Route B', description='d', status='published')

        self.contributor = User.objects.create_user(email='scope-user@example.com', password='pw12345!')
        self.staff = User.objects.create_user(email='scope-staff@example.com', password='pw12345!', is_staff=True)

    def _titles(self, response):
        data = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        return {row['title'] for row in data}

    def test_item_list_unfiltered_without_city_context(self):
        titles = self._titles(self.client.get('/api/v1/heritage-items/'))
        self.assertIn('Item In A', titles)
        self.assertIn('Item In B', titles)

    def test_item_list_scoped_by_header_and_param_wins(self):
        titles = self._titles(self.client.get('/api/v1/heritage-items/', HTTP_X_CITY='city-b'))
        self.assertEqual(titles, {'Item In B'})
        # ?city= wins over a conflicting header
        titles = self._titles(
            self.client.get('/api/v1/heritage-items/?city=city-a', HTTP_X_CITY='city-b'))
        self.assertEqual(titles, {'Item In A'})

    def test_unknown_city_slug_is_unfiltered(self):
        titles = self._titles(self.client.get('/api/v1/heritage-items/?city=nowhere'))
        self.assertIn('Item In A', titles)
        self.assertIn('Item In B', titles)

    def test_geojson_scoped(self):
        response = self.client.get('/api/v1/heritage-items/geojson/?city=city-a')
        titles = {f['properties']['title'] for f in response.data['features']}
        self.assertEqual(titles, {'Item In A'})
        self.assertEqual(
            {f['properties']['city'] for f in response.data['features']}, {'city-a'})

    def test_detail_deep_link_ignores_mismatched_city(self):
        response = self.client.get(
            f'/api/v1/heritage-items/{self.item_b.id}/', HTTP_X_CITY='city-a')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['city']['slug'], 'city-b')

    def test_parish_list_scoped(self):
        response = self.client.get('/api/v1/parishes/', HTTP_X_CITY='city-a')
        data = response.data['results'] if isinstance(response.data, dict) and 'results' in response.data else response.data
        names = {p['name'] for p in data}
        self.assertIn('Parish A', names)
        self.assertNotIn('Parish B', names)

    def test_route_list_scoped_detail_unscoped(self):
        titles = self._titles(self.client.get('/api/v1/routes/', HTTP_X_CITY='city-a'))
        self.assertEqual(titles, {'Route A'})
        response = self.client.get(
            f'/api/v1/routes/{self.route_b.id}/', HTTP_X_CITY='city-a')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_contribution_created_in_request_city(self):
        self.client.force_authenticate(user=self.contributor)
        payload = {
            'title': 'Contributed In B', 'description': 'd',
            'heritage_type': self.h_type.id, 'heritage_category': self.h_cat.id,
            'parish': self.parish_b.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
        }
        response = self.client.post(
            '/api/v1/contributions/', payload, format='json', HTTP_X_CITY='city-b')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['city']['slug'], 'city-b')

    def test_contribution_parish_must_match_request_city(self):
        self.client.force_authenticate(user=self.contributor)
        payload = {
            'title': 'Cross-city parish', 'description': 'd',
            'heritage_type': self.h_type.id, 'heritage_category': self.h_cat.id,
            'parish': self.parish_b.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
        }
        response = self.client.post(
            '/api/v1/contributions/', payload, format='json', HTTP_X_CITY='city-a')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('parish', response.data)

    def test_contribution_without_city_context_adopts_parish_city(self):
        self.client.force_authenticate(user=self.contributor)
        payload = {
            'title': 'Legacy client contribution', 'description': 'd',
            'heritage_type': self.h_type.id, 'heritage_category': self.h_cat.id,
            'parish': self.parish_b.id,
            'location': {'type': 'Point', 'coordinates': [-78.6, -1.6]},
        }
        response = self.client.post('/api/v1/contributions/', payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['city']['slug'], 'city-b')

    def test_moderation_queue_and_stats_scoped(self):
        self.client.force_authenticate(user=self.staff)
        titles = self._titles(self.client.get('/api/v1/moderation/queue/', HTTP_X_CITY='city-a'))
        self.assertEqual(titles, {'Pending A'})
        response = self.client.get('/api/v1/moderation/queue/stats/', HTTP_X_CITY='city-a')
        self.assertEqual(response.data['pending'], 1)


class PerCityCuratorTests(APITestCase):
    """Curator/moderator powers are per-city CityRole grants; profile.role
    curator alone grants nothing (the enforcement flip of the refactor)."""

    def setUp(self):
        from django.contrib.gis.geos import Point
        from apps.heritage.models import HeritageCategory, HeritageItem, HeritageType
        from apps.routes.models import HeritageRoute

        self.city_a = make_city(slug='gov-a', name='Gov A')
        self.city_b = make_city(slug='gov-b', name='Gov B')
        self.h_type = HeritageType.objects.create(name='Gov T', slug='gov-t')
        self.h_cat = HeritageCategory.objects.create(name='Gov C', slug='gov-c')

        def pending_item(city, title):
            return HeritageItem.objects.create(
                city=city, title=title, description='d',
                location=Point(-78.6, -1.6, srid=4326),
                heritage_type=self.h_type, heritage_category=self.h_cat,
                status='pending',
            )

        self.pending_a = pending_item(self.city_a, 'Gov Pending A')
        self.pending_b = pending_item(self.city_b, 'Gov Pending B')
        self.route_a = HeritageRoute.objects.create(
            city=self.city_a, title='Gov Route A', description='d', status='pending')
        self.route_b = HeritageRoute.objects.create(
            city=self.city_b, title='Gov Route B', description='d', status='pending')

        role, _ = UserRole.objects.get_or_create(slug='curator', defaults={'name': 'Curator'})
        self.curator_a = User.objects.create_user(email='gov-cur-a@example.com', password='pw12345!')
        UserProfile.objects.create(user=self.curator_a, role=role)
        make_city_curator(self.curator_a, self.city_a)

        # Curator label on the profile but NO CityRole grant anywhere.
        self.label_only = User.objects.create_user(email='gov-label@example.com', password='pw12345!')
        UserProfile.objects.create(user=self.label_only, role=role)

    def test_queue_limited_to_assigned_cities(self):
        self.client.force_authenticate(user=self.curator_a)
        response = self.client.get('/api/v1/moderation/queue/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['results'] if 'results' in response.data else response.data
        titles = {row['title'] for row in data}
        self.assertIn('Gov Pending A', titles)
        self.assertNotIn('Gov Pending B', titles)

    def test_cross_city_approve_denied_own_city_allowed(self):
        self.client.force_authenticate(user=self.curator_a)
        denied = self.client.post(f'/api/v1/moderation/queue/{self.pending_b.id}/approve/')
        self.assertIn(denied.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))
        allowed = self.client.post(f'/api/v1/moderation/queue/{self.pending_a.id}/approve/')
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.pending_a.refresh_from_db()
        self.assertEqual(self.pending_a.status, 'published')

    def test_route_governance_is_city_scoped_for_non_staff_curator(self):
        # Regression for the old IsAdminUser gate: a (non-staff) city curator
        # can now approve routes — but only in their own city.
        self.client.force_authenticate(user=self.curator_a)
        allowed = self.client.post(f'/api/v1/routes/{self.route_a.id}/approve/')
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        self.route_a.refresh_from_db()
        self.assertEqual(self.route_a.status, 'published')
        denied = self.client.post(f'/api/v1/routes/{self.route_b.id}/approve/')
        self.assertIn(denied.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

    def test_profile_role_label_alone_grants_nothing(self):
        self.client.force_authenticate(user=self.label_only)
        response = self.client.get('/api/v1/moderation/queue/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_me_exposes_city_roles(self):
        self.client.force_authenticate(user=self.curator_a)
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        grants = {(g['city']['slug'], g['role']) for g in response.data['city_roles']}
        self.assertIn(('gov-a', 'curator'), grants)
        self.client.force_authenticate(user=self.label_only)
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.data['city_roles'], [])
