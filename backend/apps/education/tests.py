from django.test import TestCase
from django.test import override_settings
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient
from rest_framework import status
from django.core.files.uploadedfile import SimpleUploadedFile

import io
import json
import shutil
import tempfile
import zipfile
from xml.etree import ElementTree as ET
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish
from apps.heritage.models import MediaFile
from apps.education.models import LOMGeneral, LOMLifeCycle, LOMEducational, LOMRights, LOMClassification, LOMRelation

User = get_user_model()

class EducationLOMTest(TestCase):
    def setUp(self):
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Parish')
        self.item = HeritageItem.objects.create(
            title='Education Item', 
            description='Desc', 
            heritage_type=self.type, 
            heritage_category=self.category,
            parish=self.parish,
            location='POINT(0 0)'
        )

    def test_lom_general_creation(self):
        lom = LOMGeneral.objects.create(
            heritage_item=self.item,
            title='Learning Object',
            language='es',
            description='A learning object',
            keywords='test, education',
            aggregation_level=1
        )
        self.assertEqual(lom.title, 'Learning Object')
        self.assertEqual(lom.heritage_item, self.item)

    def test_lom_lifecycle_creation(self):
        lom = LOMGeneral.objects.create(heritage_item=self.item, title='LO')
        lifecycle = LOMLifeCycle.objects.create(
            lom_general=lom,
            version='1.0',
            status='final'
        )
        self.assertEqual(lifecycle.lom_general, lom)
        self.assertEqual(lifecycle.version, '1.0')

    def test_lom_educational_creation(self):
        lom = LOMGeneral.objects.create(heritage_item=self.item, title='LO')
        edu = LOMEducational.objects.create(
            lom_general=lom,
            learning_resource_type='narrative_text',
            difficulty='medium',
            context='school'
        )
        self.assertEqual(edu.learning_resource_type, 'narrative_text')

    def test_lom_rights_creation(self):
        lom = LOMGeneral.objects.create(heritage_item=self.item, title='LO')
        rights = LOMRights.objects.create(
            lom_general=lom,
            cost=False,
            copyright_and_other_restrictions=True
        )
        self.assertFalse(rights.cost)
        self.assertTrue(rights.copyright_and_other_restrictions)

    def test_lom_classification_creation(self):
        lom = LOMGeneral.objects.create(heritage_item=self.item, title='LO')
        classification = LOMClassification.objects.create(
            lom_general=lom,
            purpose='discipline',
            taxon_entry='History'
        )
        self.assertEqual(classification.purpose, 'discipline')

    def test_lom_relation_creation_target_item(self):
        lom = LOMGeneral.objects.create(heritage_item=self.item, title='LO')
        other = HeritageItem.objects.create(
            title='Other Item',
            description='Other Desc',
            heritage_type=self.type,
            heritage_category=self.category,
            parish=self.parish,
            location='POINT(0 0)'
        )
        rel = LOMRelation.objects.create(
            lom_general=lom,
            kind='references',
            target_heritage_item=other,
        )
        self.assertEqual(rel.lom_general, lom)
        self.assertEqual(rel.target_heritage_item, other)


class EducationLOMAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='lom_api_user@example.com', password='password')

        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')

        self.item = HeritageItem.objects.create(
            title='Item With LOM',
            description='Desc',
            heritage_type=self.type,
            heritage_category=self.category,
            parish=self.parish,
            location='POINT(0 0)',
            status='published',
        )

        self.media_a = MediaFile.objects.create(
            file='a.jpg',
            file_type='image',
            uploaded_by=self.user,
        )
        self.media_b = MediaFile.objects.create(
            file='b.jpg',
            file_type='image',
            uploaded_by=self.user,
        )
        self.item.images.add(self.media_a)
        self.item.images.add(self.media_b)

        self.lom = LOMGeneral.objects.create(
            heritage_item=self.item,
            title='Learning Object',
            language='es',
            description='A learning object',
            keywords='test, education',
            aggregation_level=1,
        )

    def test_create_lom_relation_and_appears_in_heritage_detail(self):
        self.client.force_authenticate(user=self.user)

        payload = {
            'lom_general': str(self.lom.id),
            'kind': 'is_similar_to',
            'target_media_file': str(self.media_b.id),
            'description': 'Two images of the same element',
        }

        create_resp = self.client.post('/api/v1/lom-relations/', payload, format='json')
        self.assertEqual(create_resp.status_code, status.HTTP_201_CREATED)

        detail_resp = self.client.get(f'/api/v1/heritage-items/{self.item.id}/')
        self.assertEqual(detail_resp.status_code, status.HTTP_200_OK)

        lom_metadata = detail_resp.data.get('lom_metadata')
        self.assertIsNotNone(lom_metadata)

        relations = lom_metadata.get('relations')
        self.assertIsInstance(relations, list)
        self.assertEqual(len(relations), 1)

        rel = relations[0]
        self.assertEqual(rel['kind'], 'is_similar_to')
        self.assertEqual(str(rel.get('target_media_file')), str(self.media_b.id))
        self.assertEqual(rel.get('target_heritage_item'), None)


class EducationSCORMExportAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='scorm_user@example.com', password='password')

        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')

        self.item = HeritageItem.objects.create(
            title='SCORM Item',
            description='SCORM export test',
            heritage_type=self.type,
            heritage_category=self.category,
            parish=self.parish,
            location='POINT(0 0)',
            status='published',
        )

        self.lom = LOMGeneral.objects.create(
            heritage_item=self.item,
            title='Learning Object',
            language='en',
            description='LOM description',
            keywords='alpha, beta',
            aggregation_level=1,
        )
        LOMEducational.objects.create(
            lom_general=self.lom,
            learning_resource_type='narrative_text',
            difficulty='medium',
            context='school',
        )
        LOMRights.objects.create(
            lom_general=self.lom,
            cost=False,
            copyright_and_other_restrictions=True,
            description='Attribution goes here',
        )
        LOMClassification.objects.create(
            lom_general=self.lom,
            purpose='discipline',
            taxon_entry='History',
        )
        LOMRelation.objects.create(
            lom_general=self.lom,
            kind='references',
            target_url='https://example.com',
            description='External reference',
        )

        self._media_root = tempfile.mkdtemp(prefix='hp-test-media-')
        self.addCleanup(lambda: shutil.rmtree(self._media_root, ignore_errors=True))

    def test_scorm_package_download_contains_required_files(self):
        with override_settings(MEDIA_ROOT=self._media_root):
            img = MediaFile.objects.create(
                file=SimpleUploadedFile('a.jpg', b'fake-jpg', content_type='image/jpeg'),
                file_type='image',
                uploaded_by=self.user,
            )
            aud = MediaFile.objects.create(
                file=SimpleUploadedFile('a.mp3', b'fake-mp3', content_type='audio/mpeg'),
                file_type='audio',
                uploaded_by=self.user,
            )
            vid = MediaFile.objects.create(
                file=SimpleUploadedFile('a.mp4', b'fake-mp4', content_type='video/mp4'),
                file_type='video',
                uploaded_by=self.user,
            )
            pdf = MediaFile.objects.create(
                file=SimpleUploadedFile('a.pdf', b'%PDF-1.4 fake', content_type='application/pdf'),
                file_type='document',
                uploaded_by=self.user,
            )
            txt = MediaFile.objects.create(
                file=SimpleUploadedFile('a.txt', b'hello', content_type='text/plain'),
                file_type='document',
                uploaded_by=self.user,
            )

            self.item.images.add(img)
            self.item.audio.add(aud)
            self.item.video.add(vid)
            self.item.documents.add(pdf)
            self.item.documents.add(txt)

            resp = self.client.get(f'/api/v1/education/scorm-packages/{self.item.id}/download/')
            self.assertEqual(resp.status_code, status.HTTP_200_OK)
            self.assertEqual(resp['Content-Type'], 'application/zip')

            content = b''.join(resp.streaming_content)
            with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
                names = set(zf.namelist())
                self.assertIn('imsmanifest.xml', names)
                self.assertIn('index.html', names)
                self.assertIn('scorm.js', names)
                self.assertIn('metadata/lom.json', names)
                self.assertIn('metadata/lom.xml', names)

                # At least one asset per type is present.
                self.assertTrue(any(n.startswith('assets/image/') for n in names))
                self.assertTrue(any(n.startswith('assets/audio/') for n in names))
                self.assertTrue(any(n.startswith('assets/video/') for n in names))
                self.assertTrue(any(n.startswith('assets/document/') for n in names))

                # Manifest references the launch file.
                manifest_bytes = zf.read('imsmanifest.xml')
                root = ET.fromstring(manifest_bytes)
                # Namespace-agnostic search: ensure index.html exists as a file href in manifest.
                hrefs = [el.attrib.get('href') for el in root.iter() if el.tag.endswith('file')]
                self.assertIn('index.html', hrefs)

                # LOM JSON contains expected fields.
                lom_json = json.loads(zf.read('metadata/lom.json').decode('utf-8'))
                self.assertEqual(lom_json.get('title'), 'Learning Object')
                self.assertIn('educational', lom_json)
                self.assertIn('rights', lom_json)
