from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish
from apps.cities.testing import make_city

User = get_user_model()


class ContributionAPITest(TestCase):
    """The real contribution flow: /contributions/ creates HeritageItems and
    /my-contributions/ serves the contributor's own submissions. (The old
    Contribution/ContributionReview model tests left with the dead models.)"""

    def setUp(self):
        self.city = make_city()
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        self.curator = User.objects.create_user(email='curator@example.com', password='password', is_staff=True)
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(city=self.city, name='Parish')

    def test_submit_contribution(self):
        self.client.force_authenticate(user=self.user)
        data = {
            'title': 'New Contribution',
            'description': 'Description',
            'heritage_type': self.type.id,
            'heritage_category': self.category.id,
            'parish': self.parish.id,
            'location': {'type': 'Point', 'coordinates': [0, 0]},
        }
        response = self.client.post('/api/v1/contributions/', data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        item = HeritageItem.objects.latest('created_at')
        self.assertEqual(item.status, 'pending')
        self.assertEqual(item.contributor, self.user)

    def test_list_my_contributions(self):
        self.client.force_authenticate(user=self.user)
        HeritageItem.objects.create(
            city=self.city,
            title='My Contr',
            description='Desc',
            heritage_type=self.type,
            heritage_category=self.category,
            parish=self.parish,
            location='POINT(0 0)',
            contributor=self.user,
            status='pending',
        )

        response = self.client.get('/api/v1/my-contributions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
