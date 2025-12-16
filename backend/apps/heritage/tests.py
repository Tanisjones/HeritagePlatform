from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient
from rest_framework import status
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish, MediaFile

User = get_user_model()

class HeritageModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='contributor@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parent_cat = HeritageCategory.objects.create(name='Parent', slug='parent')
        self.category.parent = self.parent_cat
        self.category.save()
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')

    def test_create_heritage_item(self):
        item = HeritageItem.objects.create(
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
        self.client = APIClient()
        self.user = User.objects.create_user(email='user@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')
        
        self.item1 = HeritageItem.objects.create(
            title='Public Item',
            description='Public Desc',
            heritage_type=self.type,
            heritage_category=self.category,
            parish=self.parish,
            location=Point(0,0),
            status='published'
        )
        self.item2 = HeritageItem.objects.create(
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
