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

    def test_lom_catalog_scoped_by_city(self):
        # /learn lists LOM records; they scope via their parent heritage item.
        from apps.education.models import LOMGeneral

        LOMGeneral.objects.create(heritage_item=self.item_a, title='LOM A', language='es')
        LOMGeneral.objects.create(heritage_item=self.item_b, title='LOM B', language='es')
        response = self.client.get('/api/v1/lom/', HTTP_X_CITY='city-a')
        data = response.data['results'] if 'results' in response.data else response.data
        titles = {row['title'] for row in data}
        self.assertIn('LOM A', titles)
        self.assertNotIn('LOM B', titles)

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

    def test_city_curator_can_publish_lesson_plan(self):
        # Regression: publish/edit actions were IsTeacher-gated at the view
        # level, so a non-staff city curator could never reach the curator-only
        # publish transition. View gate now admits curators; the object checks
        # keep it per-city.
        from apps.education.models import LessonActivity, LessonPlan

        teacher_role, _ = UserRole.objects.get_or_create(slug='teacher', defaults={'name': 'Teacher'})
        teacher = User.objects.create_user(email='gov-teacher@example.com', password='pw12345!')
        UserProfile.objects.create(user=teacher, role=teacher_role)
        plan = LessonPlan.objects.create(
            title='Plan Gov A', city=self.city_a, author=teacher,
            status=LessonPlan.STATUS_REVIEW,
        )
        LessonActivity.objects.create(lesson=plan, order=1, title='Act', activity_type='explore')

        # Curator of ANOTHER city: not the author, not this city's curator.
        curator_b = User.objects.create_user(email='gov-cur-b@example.com', password='pw12345!')
        make_city_curator(curator_b, self.city_b)
        self.client.force_authenticate(user=curator_b)
        denied = self.client.post(f'/api/v1/lesson-plans/{plan.id}/publish/')
        self.assertIn(denied.status_code, (status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND))

        # THIS city's (non-staff) curator publishes.
        self.client.force_authenticate(user=self.curator_a)
        allowed = self.client.post(f'/api/v1/lesson-plans/{plan.id}/publish/')
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)
        plan.refresh_from_db()
        self.assertEqual(plan.status, LessonPlan.STATUS_PUBLISHED)

    def test_me_exposes_city_roles(self):
        self.client.force_authenticate(user=self.curator_a)
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        grants = {(g['city']['slug'], g['role']) for g in response.data['city_roles']}
        self.assertIn(('gov-a', 'curator'), grants)
        self.client.force_authenticate(user=self.label_only)
        response = self.client.get('/api/v1/users/me/')
        self.assertEqual(response.data['city_roles'], [])


class AIPromptCityTests(APITestCase):
    """AI prompt templates render the request city (no provider call)."""

    def _view_with_request(self, **extra):
        from rest_framework.test import APIRequestFactory
        from apps.ai_services.assist_views import RouteMetadataAssistView

        view = RouteMetadataAssistView()
        view.request = APIRequestFactory().post('/api/v1/ai/assist/route-metadata/', **extra)
        return view

    def test_prompt_variables_render_request_city(self):
        from apps.ai_services.assist_views import _render_prompt

        make_city(slug='prompt-city', name='Cuenca')
        view = self._view_with_request(HTTP_X_CITY='prompt-city')
        variables = view.prompt_variables({'language': 'es'})
        self.assertEqual(variables['city'], 'Cuenca')
        self.assertEqual(variables['country'], 'Ecuador')
        rendered = _render_prompt(
            'Walking route in {{city}}, {{country}}. Language: {{language}}.',
            variables=variables,
        )
        self.assertEqual(rendered, 'Walking route in Cuenca, Ecuador. Language: es.')

    def test_prompt_variables_fall_back_to_founding_city(self):
        view = self._view_with_request()
        variables = view.prompt_variables({'language': 'es'})
        self.assertEqual(variables['city'], 'Riobamba')
        self.assertEqual(variables['country'], 'Ecuador')


class PartEAdminOpsTests(APITestCase):
    """E1 admin inlines, E2 bootstrap_city, E3 changelist stats."""

    def setUp(self):
        from django.contrib.auth import get_user_model

        self.User = get_user_model()
        self.staff = self.User.objects.create_superuser(
            email='root@example.com', username='root', password='pw'
        )
        self.city = make_city()

    # ---- E2 ----------------------------------------------------------------

    def test_bootstrap_creates_taxonomies_parishes_and_grants(self):
        from io import StringIO

        from django.core.management import call_command

        from apps.heritage.models import HeritageCategory, HeritageType, Parish

        curator = self.User.objects.create_user(email='ana@example.com', password='pw')
        out = StringIO()
        call_command(
            'bootstrap_city', self.city.slug,
            '--parishes', 'El Sagrario, San Blas',
            '--curator', 'ana@example.com',
            stdout=out,
        )
        self.assertEqual(HeritageType.objects.filter(slug__in=['tangible', 'intangible']).count(), 2)
        self.assertEqual(HeritageCategory.objects.count(), 6)
        self.assertEqual(
            sorted(Parish.objects.filter(city=self.city).values_list('name', flat=True)),
            ['El Sagrario', 'San Blas'],
        )
        self.assertTrue(
            CityRole.objects.filter(user=curator, city=self.city, role=CityRole.ROLE_CURATOR).exists()
        )
        self.assertIn('Readiness', out.getvalue())

        # Idempotent: run again, nothing duplicates.
        call_command(
            'bootstrap_city', self.city.slug,
            '--parishes', 'El Sagrario, San Blas',
            '--curator', 'ana@example.com',
            stdout=StringIO(),
        )
        self.assertEqual(Parish.objects.filter(city=self.city).count(), 2)
        self.assertEqual(CityRole.objects.filter(city=self.city).count(), 1)

    def test_bootstrap_rejects_unknown_curator_before_writing(self):
        from io import StringIO

        from django.core.management import call_command
        from django.core.management.base import CommandError

        from apps.heritage.models import Parish

        with self.assertRaises(CommandError):
            call_command(
                'bootstrap_city', self.city.slug,
                '--parishes', 'Centro',
                '--curator', 'ghost@example.com',
                stdout=StringIO(),
            )
        # All-or-nothing: the parish list was not created either.
        self.assertEqual(Parish.objects.filter(city=self.city).count(), 0)

    def test_bootstrap_check_writes_nothing(self):
        from io import StringIO

        from django.core.management import call_command

        from apps.heritage.models import Parish

        out = StringIO()
        call_command('bootstrap_city', self.city.slug, '--check', stdout=out)
        self.assertIn('Readiness', out.getvalue())
        self.assertEqual(Parish.objects.filter(city=self.city).count(), 0)

    # ---- E3 ----------------------------------------------------------------

    def test_city_changelist_stats_count_distinct(self):
        from django.contrib.admin.sites import AdminSite
        from django.contrib.gis.geos import Point as GeoPoint

        from apps.cities.admin import CityAdmin
        from apps.cities.models import City
        from apps.heritage.models import HeritageCategory, HeritageItem, HeritageType

        h_type = HeritageType.objects.create(name='T', slug='t')
        h_cat = HeritageCategory.objects.create(name='C', slug='c')
        for index, item_status in enumerate(['published', 'pending', 'pending']):
            HeritageItem.objects.create(
                city=self.city, title=f'I{index}', description='d',
                heritage_type=h_type, heritage_category=h_cat,
                location=GeoPoint(0, 0), status=item_status,
            )
        CityRole.objects.create(user=self.staff, city=self.city, role=CityRole.ROLE_CURATOR)

        admin_instance = CityAdmin(City, AdminSite())
        row = admin_instance.get_queryset(request=None).get(pk=self.city.pk)
        self.assertEqual(admin_instance.items_total(row), 3)
        self.assertEqual(admin_instance.items_pending(row), 2)
        self.assertEqual(admin_instance.curators_total(row), 1)
        self.assertEqual(admin_instance.routes_total(row), 0)

    # ---- E1 ----------------------------------------------------------------

    def test_user_admin_page_renders_cityrole_inline_and_grant_sticks(self):
        from django.test import Client

        client = Client()
        client.force_login(self.staff)
        target = self.User.objects.create_user(email='inline@example.com', password='pw')

        page = client.get(f'/admin/users/user/{target.id}/change/')
        self.assertEqual(page.status_code, 200)
        # extra=0 → no -0- row for a user without grants; the formset's
        # management form is the reliable marker that the inline is mounted.
        self.assertContains(page, 'city_roles-TOTAL_FORMS', msg_prefix='CityRole inline missing')

        # City admin renders too (roster inline + E3 columns on the list).
        page = client.get('/admin/cities/city/')
        self.assertEqual(page.status_code, 200)
        page = client.get(f'/admin/cities/city/{self.city.id}/change/')
        self.assertEqual(page.status_code, 200)
