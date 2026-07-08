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
