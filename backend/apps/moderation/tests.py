from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from unittest.mock import patch
from apps.users.models import UserRole
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory
from apps.moderation.models import ContributionVersion, QualityScore, ContributionFlag, ReviewChecklist, ReviewChecklistItem

User = get_user_model()

class ModerationTests(APITestCase):
    def setUp(self):
        # Create Roles
        self.curator_role, _ = UserRole.objects.get_or_create(name='Curator', slug='curator')
        self.contributor_role, _ = UserRole.objects.get_or_create(name='Contributor', slug='contributor')

        # Create Users
        self.curator = User.objects.create_user(email='curator@example.com', password='password123')
        from apps.users.models import UserProfile
        UserProfile.objects.create(user=self.curator, role=self.curator_role)

        self.contributor = User.objects.create_user(email='contributor@example.com', password='password123')
        UserProfile.objects.create(user=self.contributor, role=self.contributor_role)

        # Create Heritage Data
        self.h_type = HeritageType.objects.create(name='Type 1', slug='type-1')
        self.h_cat = HeritageCategory.objects.create(name='Cat 1', slug='cat-1')
        
        self.item = HeritageItem.objects.create(
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
        approved_item = HeritageItem.objects.create(
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
