from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish
from apps.contributions.models import Contribution, ContributionReview

User = get_user_model()

class ContributionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='contributor@example.com', password='password')
        self.reviewer = User.objects.create_user(email='reviewer@example.com', password='password', is_staff=True)
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Parish')
        self.item = HeritageItem.objects.create(
            title='Item', description='Desc', 
            heritage_type=self.type, heritage_category=self.category, 
            parish=self.parish, location='POINT(0 0)'
        )

    def test_create_contribution_new_item(self):
        contribution = Contribution.objects.create(
            contributor=self.user,
            contribution_type='new_item',
            content={'title': 'New Place', 'description': 'Very nice'}
        )
        self.assertEqual(contribution.status, 'pending')
        self.assertIsNone(contribution.heritage_item)

    def test_create_contribution_enrichment(self):
        contribution = Contribution.objects.create(
            contributor=self.user,
            heritage_item=self.item,
            contribution_type='enrichment',
            content={'description': 'Updated description'}
        )
        self.assertEqual(contribution.heritage_item, self.item)

    def test_contribution_review(self):
        contribution = Contribution.objects.create(
            contributor=self.user,
            contribution_type='new_item'
        )
        review = ContributionReview.objects.create(
            contribution=contribution,
            reviewer=self.reviewer,
            decision='approve',
            feedback='Good job'
        )
        self.assertEqual(review.contribution, contribution)
        self.assertEqual(review.decision, 'approve')

class ContributionAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        self.curator = User.objects.create_user(email='curator@example.com', password='password', is_staff=True)
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Parish')

    def test_submit_contribution(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'New Contribution',
            'description': 'Description',
            'heritage_type': self.type.id,
            'heritage_category': self.category.id,
            'parish': self.parish.id,
            'location': {'type': 'Point', 'coordinates': [0, 0]}
        }
        # Assuming the contribution endpoint handles direct HeritageItem creation in pending state
        # as per previous discussions/code which merged contributions into HeritageItem model workflow
        response = self.client.post('/api/v1/contributions/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
        # Check item created in pending state
        item = HeritageItem.objects.latest('created_at')
        self.assertEqual(item.status, 'pending')
        self.assertEqual(item.contributor, self.user)
        # Check AI suggestion triggered (implied by service calls in views)

    def test_list_my_contributions(self):
        self.client.force_authenticate(user=self.user)
        HeritageItem.objects.create(
            title='My Contr', 
            description='Desc', 
            heritage_type=self.type, 
            heritage_category=self.category,
            parish=self.parish,
            location='POINT(0 0)',
            contributor=self.user, 
            status='pending'
        )
        
        response = self.client.get('/api/v1/my-contributions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
