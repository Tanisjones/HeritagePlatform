from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from unittest.mock import patch
from apps.users.models import UserRole
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory
from apps.moderation.models import ContributionVersion, QualityScore, ContributionFlag, ReviewChecklist, ReviewChecklistItem
from apps.cities.testing import make_city

User = get_user_model()

class ModerationTests(APITestCase):
    def setUp(self):
        self.city = make_city()
        # Create Roles
        self.curator_role, _ = UserRole.objects.get_or_create(name='Curator', slug='curator')
        self.contributor_role, _ = UserRole.objects.get_or_create(name='Contributor', slug='contributor')

        # Create Users
        self.curator = User.objects.create_user(email='curator@example.com', password='password123')
        from apps.users.models import UserProfile
        UserProfile.objects.create(user=self.curator, role=self.curator_role)
        from apps.cities.testing import make_city_curator
        make_city_curator(self.curator, self.city)

        self.contributor = User.objects.create_user(email='contributor@example.com', password='password123')
        UserProfile.objects.create(user=self.contributor, role=self.contributor_role)

        # Create Heritage Data
        self.h_type = HeritageType.objects.create(name='Type 1', slug='type-1')
        self.h_cat = HeritageCategory.objects.create(name='Cat 1', slug='cat-1')
        
        self.item = HeritageItem.objects.create(city=self.city, 
            title='Test Item',
            description='Test Description',
            location=Point(0, 0),
            heritage_type=self.h_type,
            heritage_category=self.h_cat,
            contributor=self.contributor,
            status='pending',
            parish=None # Optional
        )

        # Basic checklist
        self.checklist = ReviewChecklist.objects.create(name='General')
        self.cl_item = ReviewChecklistItem.objects.create(checklist=self.checklist, text='Check 1')

        # Mock notifications to avoid template rendering issues
        self.p1 = patch('apps.notifications.utils.send_notification_email')
        self.p2 = patch('apps.heritage.signals.send_notification_email')
        self.mock_email1 = self.p1.start()
        self.mock_email2 = self.p2.start()
        self.addCleanup(self.p1.stop)
        self.addCleanup(self.p2.stop)

    def test_permission_classes(self):
        # Authenticate as curator
        self.client.force_authenticate(user=self.curator)
        # Assuming registered as 'moderation-queue' in router. 
        # Ideally verify URL name via router or use explicit path.
        # Let's guess standard DRF router names based on ViewSet name 'ModerationViewSet'
        # If router.register('moderation/queue', ModerationViewSet, basename='moderation-queue')
        
        url_list = '/api/v1/moderation/queue/'
        
        response = self.client.get(url_list)
        if response.status_code == 404:
             # Fallback if path is different
             print(f"URL {url_list} not found, check router config")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Authenticate as contributor (should fail)
        self.client.force_authenticate(user=self.contributor)
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_queue_list_filters(self):
        self.client.force_authenticate(user=self.curator)
        url = '/api/v1/moderation/queue/'
        
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should contain the pending item
        ids = [str(i['id']) for i in response.data['results']]
        self.assertIn(str(self.item.id), ids)

        # Create approved item
        approved_item = HeritageItem.objects.create(city=self.city, 
            title='Approved Item',
            heritage_type=self.h_type,
            heritage_category=self.h_cat,
            status='published',
            contributor=self.contributor,
            location=Point(0, 0)
        )
        
        # Test default filter (status=pending, changes_requested)
        response = self.client.get(url)
        ids = [str(i['id']) for i in response.data['results']]
        self.assertNotIn(str(approved_item.id), ids)

    def test_approve_action(self):
        self.client.force_authenticate(user=self.curator)
        url = f'/api/v1/moderation/queue/{self.item.id}/approve/'
        data = {
            'quality_score': {
                'completeness_score': 30,
                'accuracy_score': 25,
                'media_quality_score': 20
            }
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'published')
        
        # Check Quality Score created
        self.assertTrue(QualityScore.objects.filter(heritage_item=self.item).exists())
        qs = QualityScore.objects.get(heritage_item=self.item)
        self.assertEqual(qs.total_score, 75)
        
        # Check Version created
        self.assertTrue(ContributionVersion.objects.filter(heritage_item=self.item, changes_summary='Approved').exists())

    def test_reject_action(self):
        self.client.force_authenticate(user=self.curator)
        url = f'/api/v1/moderation/queue/{self.item.id}/reject/'
        data = {
            'feedback': 'Not good enough'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'rejected')
        self.assertEqual(self.item.curator_feedback, 'Not good enough')

    def test_request_changes(self):
        self.client.force_authenticate(user=self.curator)
        url = f'/api/v1/moderation/queue/{self.item.id}/request-changes/'
        data = {'feedback': 'Please fix title'}
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.item.refresh_from_db()
        self.assertEqual(self.item.status, 'changes_requested')

    def test_quality_scoring_independent(self):
        self.client.force_authenticate(user=self.curator)
        url = f'/api/v1/moderation/queue/{self.item.id}/score/'
        data = {
             'completeness_score': 10,
             'accuracy_score': 10,
             'media_quality_score': 10
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        qs = QualityScore.objects.get(heritage_item=self.item)
        self.assertEqual(qs.total_score, 30)

    def test_flagging(self):
        self.client.force_authenticate(user=self.curator)
        url = f'/api/v1/moderation/queue/{self.item.id}/flag/'
        data = {
            'flag_type': 'spam',
            'reason': 'Spam detected'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        self.assertTrue(ContributionFlag.objects.filter(heritage_item=self.item).exists())

    def test_checklist_response(self):
        self.client.force_authenticate(user=self.curator)
        url = f'/api/v1/moderation/queue/{self.item.id}/checklist-response/'
        data = {
            'responses': [
                {
                    'checklist_item': self.cl_item.id,
                    'is_checked': True,
                    'notes': 'Looks good'
                }
            ]
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.assertTrue(self.item.checklist_responses.filter(is_checked=True).exists())


class PartDModerationTests(APITestCase):
    """D1 stats breakdown, D2 assign + bulk decisions, D3 arrival broadcasts."""

    def setUp(self):
        self.city = make_city()
        self.other_city = make_city(slug='other-city', name='Other City')
        from apps.cities.testing import make_city_curator
        from apps.users.models import UserProfile

        self.curator_role, _ = UserRole.objects.get_or_create(name='Curator', slug='curator')
        self.curator = User.objects.create_user(email='curator@example.com', password='pw')
        UserProfile.objects.create(user=self.curator, role=self.curator_role)
        make_city_curator(self.curator, self.city)

        self.far_curator = User.objects.create_user(email='far@example.com', password='pw')
        make_city_curator(self.far_curator, self.other_city)

        self.contributor = User.objects.create_user(email='contrib@example.com', password='pw')

        self.h_type = HeritageType.objects.create(name='Type 1', slug='type-1')
        self.h_cat = HeritageCategory.objects.create(name='Cat 1', slug='cat-1')

    def _item(self, title, city=None, status='pending', **extra):
        return HeritageItem.objects.create(
            city=city or self.city, title=title, description='d',
            location=Point(0, 0), heritage_type=self.h_type,
            heritage_category=self.h_cat, contributor=self.contributor,
            status=status, **extra,
        )

    # ---- D3 ---------------------------------------------------------------

    def test_new_submission_notifies_city_curators_only(self):
        from apps.notifications.models import UserNotification

        self.client.force_authenticate(user=self.contributor)
        resp = self.client.post('/api/v1/contributions/', {
            'title': 'Recién llegada', 'description': 'x',
            'heritage_type': self.h_type.id, 'heritage_category': self.h_cat.id,
            'location': {'type': 'Point', 'coordinates': [0, 0]},
        }, format='json', HTTP_X_CITY=self.city.slug)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)

        arrivals = UserNotification.objects.filter(notification_type='moderation_needed')
        self.assertEqual(
            sorted(arrivals.values_list('recipient__email', flat=True)),
            ['curator@example.com'],
        )
        self.assertIn('Recién llegada', arrivals.get().message)

    def test_draft_notifies_curators_only_on_submit(self):
        from apps.notifications.models import UserNotification

        self.client.force_authenticate(user=self.contributor)
        resp = self.client.post('/api/v1/contributions/', {
            'title': 'Borrador silencioso', 'description': 'x',
            'heritage_type': self.h_type.id, 'heritage_category': self.h_cat.id,
            'location': {'type': 'Point', 'coordinates': [0, 0]},
            'save_as_draft': True,
        }, format='json', HTTP_X_CITY=self.city.slug)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertFalse(UserNotification.objects.filter(notification_type='moderation_needed').exists())

        self.client.post(f"/api/v1/my-contributions/{resp.data['id']}/submit/")
        self.assertEqual(
            UserNotification.objects.filter(
                notification_type='moderation_needed', recipient=self.curator
            ).count(),
            1,
        )

    def test_contributor_who_curates_is_not_self_notified(self):
        from apps.cities.testing import make_city_curator
        from apps.notifications.models import UserNotification

        make_city_curator(self.contributor, self.city)
        self.client.force_authenticate(user=self.contributor)
        self.client.post('/api/v1/contributions/', {
            'title': 'Propia', 'description': 'x',
            'heritage_type': self.h_type.id, 'heritage_category': self.h_cat.id,
            'location': {'type': 'Point', 'coordinates': [0, 0]},
        }, format='json', HTTP_X_CITY=self.city.slug)
        self.assertFalse(
            UserNotification.objects.filter(
                notification_type='moderation_needed', recipient=self.contributor
            ).exists()
        )

    # ---- D2 ---------------------------------------------------------------

    def test_assign_records_curator(self):
        item = self._item('Para asignar')
        self.client.force_authenticate(user=self.curator)
        resp = self.client.post(f'/api/v1/moderation/queue/{item.id}/assign/', HTTP_X_CITY=self.city.slug)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        item.refresh_from_db()
        self.assertEqual(item.curator, self.curator)

        # And the queue rows expose the assignee.
        resp = self.client.get('/api/v1/moderation/queue/', HTTP_X_CITY=self.city.slug)
        row = next(r for r in resp.data['results'] if r['id'] == str(item.id))
        self.assertEqual(row['curator_email'], 'curator@example.com')

    def test_bulk_approve_publishes_and_notifies_contributors(self):
        from apps.notifications.models import UserNotification

        a = self._item('Bulk A')
        b = self._item('Bulk B')
        self.client.force_authenticate(user=self.curator)
        resp = self.client.post(
            '/api/v1/moderation/queue/bulk/',
            {'ids': [str(a.id), str(b.id)], 'decision': 'approve'},
            format='json', HTTP_X_CITY=self.city.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(sorted(resp.data['processed']), sorted([str(a.id), str(b.id)]))
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual((a.status, b.status), ('published', 'published'))
        self.assertEqual(
            UserNotification.objects.filter(
                notification_type='contribution_approved', recipient=self.contributor
            ).count(),
            2,
        )
        self.assertEqual(ContributionVersion.objects.filter(heritage_item__in=[a, b]).count(), 2)

    def test_bulk_reject_applies_shared_feedback(self):
        a = self._item('Rechazo 1')
        self.client.force_authenticate(user=self.curator)
        resp = self.client.post(
            '/api/v1/moderation/queue/bulk/',
            {'ids': [str(a.id)], 'decision': 'reject', 'feedback': 'Faltan fuentes.'},
            format='json', HTTP_X_CITY=self.city.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        a.refresh_from_db()
        self.assertEqual(a.status, 'rejected')
        self.assertEqual(a.curator_feedback, 'Faltan fuentes.')

    def test_bulk_skips_items_outside_curator_cities(self):
        mine = self._item('Mía')
        foreign = self._item('Ajena', city=self.other_city)
        self.client.force_authenticate(user=self.curator)
        resp = self.client.post(
            '/api/v1/moderation/queue/bulk/',
            {'ids': [str(mine.id), str(foreign.id)], 'decision': 'approve'},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data['processed'], [str(mine.id)])
        self.assertEqual(resp.data['skipped'], [str(foreign.id)])
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, 'pending')

    def test_bulk_validates_payload(self):
        self.client.force_authenticate(user=self.curator)
        self.assertEqual(
            self.client.post('/api/v1/moderation/queue/bulk/', {'ids': [], 'decision': 'approve'}, format='json').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.post('/api/v1/moderation/queue/bulk/', {'ids': ['x'], 'decision': 'archive'}, format='json').status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    # ---- D1 ---------------------------------------------------------------

    def test_stats_breakdown_covers_only_curated_cities(self):
        self._item('P1')
        self._item('P2', status='changes_requested')
        self._item('Foreign pending', city=self.other_city)

        self.client.force_authenticate(user=self.curator)
        resp = self.client.get('/api/v1/moderation/queue/stats/', HTTP_X_CITY=self.city.slug)
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        cities = {c['slug']: c for c in resp.data['cities']}
        self.assertEqual(list(cities.keys()), [self.city.slug])
        self.assertEqual(cities[self.city.slug]['pending'], 1)
        self.assertEqual(cities[self.city.slug]['changes_requested'], 1)

    def test_stats_breakdown_spans_all_cities_for_staff(self):
        self._item('P1')
        self._item('Foreign pending', city=self.other_city)
        staff = User.objects.create_user(email='staff@example.com', password='pw', is_staff=True)
        self.client.force_authenticate(user=staff)
        resp = self.client.get('/api/v1/moderation/queue/stats/')
        slugs = sorted(c['slug'] for c in resp.data['cities'])
        self.assertEqual(slugs, sorted([self.city.slug, self.other_city.slug]))
