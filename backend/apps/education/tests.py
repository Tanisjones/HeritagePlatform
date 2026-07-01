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
from apps.education.models import (
    LOMGeneral, LOMLifeCycle, LOMEducational, LOMRights, LOMClassification,
    LOMRelation, AssessmentQuestion, EducationalResource,
)
from apps.education.scorm import (
    build_ieee_lom_xml, build_scorm_2004_pif_zip, build_cmi5_zip,
    build_collection_scorm_zip,
)
from apps.education.qti import build_qti_21_zip
from apps.routes.models import HeritageRoute, RouteStop

User = get_user_model()

_LOM_NS = 'http://ltsc.ieee.org/xsd/LOM'

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

            # SCORM download now requires authentication.
            self.client.force_authenticate(user=self.user)
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


class EducationIEEELOMXMLTest(TestCase):
    """Unit tests for the valid IEEE 1484.12.3 LOM XML builder (no DB needed)."""

    def _sample_lom(self):
        return {
            'id': 'abc-123',
            'title': 'Iglesia de la Concepción',
            'language': 'es',
            'description': 'Templo colonial de Riobamba',
            'keywords': 'iglesia, colonial, barroco',
            'coverage': 'Riobamba, Ecuador',
            'structure': 'atomic',
            'aggregation_level': 1,
            'lifecycle': {
                'version': '1.0',
                'status': 'final',
                'contributors': [{'role': 'author', 'entity': 'Juan Pérez', 'date': '2026-01-01'}],
            },
            'educational': {
                'interactivity_type': 'expositive',
                'learning_resource_type': 'narrative_text',
                'difficulty': 'medium',
                'context': 'school',
                'typical_learning_time': 'PT30M',
                'typical_age_range': '12-16',
                'description': 'Uso sugerido en aula',
                'learning_objectives': ['Identificar el estilo', 'Ubicar en el tiempo'],
                'prerequisites': 'Historia básica',
                'competencies': 'Análisis histórico',
                'pedagogical_approach': 'inquiry',
                'curriculum_alignment': 'EGB',
                'suggested_activities': 'Visita guiada',
            },
            'rights': {'cost': False, 'copyright_and_other_restrictions': True, 'description': 'CC BY'},
            'classifications': [{
                'purpose': 'discipline',
                'taxon_source': 'UNESCO',
                'taxon_id': '52',
                'taxon_entry': 'Arquitectura',
                'description': 'Clasificación',
                'keywords': 'arte',
            }],
        }

    def test_ieee_lom_xml_is_wellformed_and_namespaced(self):
        xml = build_ieee_lom_xml(self._sample_lom())
        root = ET.fromstring(xml.encode('utf-8'))
        # Root must be the namespaced <lom>.
        self.assertEqual(root.tag, f'{{{_LOM_NS}}}lom')
        # schemaLocation points at the loose schema.
        schema_loc = root.attrib.get('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation', '')
        self.assertIn('lomLoose.xsd', schema_loc)
        # A title <string> element exists with the expected text.
        strings = [e for e in root.iter(f'{{{_LOM_NS}}}string')]
        self.assertTrue(any(e.text == 'Iglesia de la Concepción' for e in strings))

    def test_ieee_lom_vocab_uses_source_value_pairs(self):
        xml = build_ieee_lom_xml(self._sample_lom())
        root = ET.fromstring(xml.encode('utf-8'))
        # structure must be a <source>LOMv1.0</source><value>atomic</value> pair.
        structure = root.find(f'{{{_LOM_NS}}}general/{{{_LOM_NS}}}structure')
        self.assertIsNotNone(structure)
        source = structure.find(f'{{{_LOM_NS}}}source')
        value = structure.find(f'{{{_LOM_NS}}}value')
        self.assertEqual(source.text, 'LOMv1.0')
        self.assertEqual(value.text, 'atomic')

    def test_ieee_lom_learning_objectives_become_classification(self):
        xml = build_ieee_lom_xml(self._sample_lom())
        root = ET.fromstring(xml.encode('utf-8'))
        # There should be at least one classification whose purpose value is the
        # LOM-spelled "educational objective".
        purposes = [
            v.text
            for c in root.iter(f'{{{_LOM_NS}}}classification')
            for v in c.iter(f'{{{_LOM_NS}}}value')
        ]
        self.assertIn('educational objective', purposes)

    def test_ieee_lom_extension_block_present_and_namespaced(self):
        xml = build_ieee_lom_xml(self._sample_lom())
        root = ET.fromstring(xml.encode('utf-8'))
        # The non-standard pedagogical fields go in a namespaced extension block.
        ext_tags = [e.tag for e in root.iter() if 'lom-ext' in e.tag]
        self.assertTrue(ext_tags, 'Expected a namespaced Riobamba extension block')

    def test_ieee_lom_handles_empty_input(self):
        xml = build_ieee_lom_xml({})
        root = ET.fromstring(xml.encode('utf-8'))
        self.assertEqual(root.tag, f'{{{_LOM_NS}}}lom')


class EducationSCORM2004Test(TestCase):
    """Unit tests for the SCORM 2004 package builder (no DB needed)."""

    def test_scorm_2004_zip_has_2004_manifest_and_runtime(self):
        lom_data = {
            'id': 'x', 'title': 'LO', 'language': 'es', 'description': 'D',
            'educational': {'learning_resource_type': 'narrative_text'},
        }
        zip_file, filename = build_scorm_2004_pif_zip(
            title='SCORM 2004 Item', description='desc', lom_data=lom_data, media_files=[],
        )
        self.assertTrue(filename.endswith('-scorm2004.zip'))

        with zipfile.ZipFile(zip_file, 'r') as zf:
            names = set(zf.namelist())
            self.assertIn('imsmanifest.xml', names)
            self.assertIn('index.html', names)
            self.assertIn('scorm2004.js', names)
            self.assertIn('metadata/lom.xml', names)

            manifest = zf.read('imsmanifest.xml').decode('utf-8')
            self.assertIn('2004 4th Edition', manifest)
            # Manifest must be well-formed.
            ET.fromstring(manifest.encode('utf-8'))

            js = zf.read('scorm2004.js').decode('utf-8')
            self.assertIn('API_1484_11', js)

            # metadata/lom.xml must be the valid IEEE LOM.
            lom_root = ET.fromstring(zf.read('metadata/lom.xml'))
            self.assertEqual(lom_root.tag, f'{{{_LOM_NS}}}lom')


class EducationCMI5Test(TestCase):
    """Unit tests for the cmi5 (xAPI) package builder (no DB needed)."""

    def test_cmi5_zip_has_course_structure_and_runtime(self):
        lom_data = {'id': 'x', 'title': 'LO', 'language': 'es', 'description': 'D'}
        zip_file, filename = build_cmi5_zip(
            title='cmi5 Item', description='desc', lom_data=lom_data, media_files=[],
        )
        self.assertTrue(filename.endswith('-cmi5.zip'))

        with zipfile.ZipFile(zip_file, 'r') as zf:
            names = set(zf.namelist())
            self.assertIn('cmi5.xml', names)
            self.assertIn('cmi5.js', names)
            self.assertIn('index.html', names)

            course = zf.read('cmi5.xml').decode('utf-8')
            root = ET.fromstring(course.encode('utf-8'))
            self.assertTrue(root.tag.endswith('}courseStructure'))
            # There must be exactly one AU with moveOn="Completed".
            aus = [e for e in root.iter() if e.tag.endswith('}au')]
            self.assertEqual(len(aus), 1)
            self.assertEqual(aus[0].attrib.get('moveOn'), 'Completed')


class EducationQTITest(TestCase):
    """Unit tests for the QTI 2.1 export (accepts plain dicts — no DB needed)."""

    def _questions(self):
        return [
            {
                'question_type': 'single_choice',
                'prompt': '¿Capital de Ecuador?',
                'choices': [
                    {'id': 'a', 'text': 'Quito', 'correct': True},
                    {'id': 'b', 'text': 'Lima', 'correct': False},
                ],
                'feedback': 'Quito es la respuesta correcta',
            },
            {
                'question_type': 'multiple_choice',
                'prompt': '¿Cuáles son ciudades de Ecuador?',
                'choices': [
                    {'id': 'a', 'text': 'Riobamba', 'correct': True},
                    {'id': 'b', 'text': 'Guayaquil', 'correct': True},
                    {'id': 'c', 'text': 'Bogotá', 'correct': False},
                ],
            },
            {
                'question_type': 'short_answer',
                'prompt': '¿Nombre del volcán cercano?',
                'correct_response': 'Chimborazo',
            },
        ]

    def test_qti_zip_has_one_item_per_question_and_manifest(self):
        zip_file, filename = build_qti_21_zip(
            title='Quiz Riobamba', questions=self._questions(), identifier='lom-1',
        )
        self.assertTrue(filename.endswith('-qti21.zip'))

        with zipfile.ZipFile(zip_file, 'r') as zf:
            names = set(zf.namelist())
            self.assertIn('imsmanifest.xml', names)
            item_files = sorted(n for n in names if n.startswith('items/'))
            self.assertEqual(len(item_files), 3)

            qns = '{http://www.imsglobal.org/xsd/imsqti_v2p1}'
            for name in item_files:
                root = ET.fromstring(zf.read(name))
                self.assertEqual(root.tag, f'{qns}assessmentItem')

            # Manifest is well-formed with one resource per item.
            manifest_root = ET.fromstring(zf.read('imsmanifest.xml'))
            resources = [e for e in manifest_root.iter() if e.tag.endswith('}resource')]
            self.assertEqual(len(resources), 3)

    def test_qti_multiple_choice_is_multiple_cardinality(self):
        zip_file, _ = build_qti_21_zip(
            title='Quiz', questions=self._questions(), identifier='lom-1',
        )
        with zipfile.ZipFile(zip_file, 'r') as zf:
            root = ET.fromstring(zf.read('items/item_2.xml'))
            rd = [e for e in root.iter() if e.tag.endswith('}responseDeclaration')][0]
            self.assertEqual(rd.attrib.get('cardinality'), 'multiple')

    def test_qti_short_answer_uses_text_interaction(self):
        zip_file, _ = build_qti_21_zip(
            title='Quiz', questions=self._questions(), identifier='lom-1',
        )
        with zipfile.ZipFile(zip_file, 'r') as zf:
            root = ET.fromstring(zf.read('items/item_3.xml'))
            self.assertTrue(
                any(e.tag.endswith('}extendedTextInteraction') for e in root.iter())
            )

    def test_qti_unscorable_item_omits_responseprocessing(self):
        """short_answer with no expected answer must OMIT responseProcessing
        (there is no valid 'none' template to reference)."""
        from apps.education.qti import build_assessment_item_xml
        root = ET.fromstring(build_assessment_item_xml(
            {'question_type': 'short_answer', 'prompt': 'Explain'}, 'IT'))
        rp = [c for c in root if c.tag.endswith('}responseProcessing')]
        self.assertEqual(rp, [])
        # And no fabricated 'none' template appears in the XML.
        self.assertNotIn('rptemplates/none', ET.tostring(root, encoding='unicode'))

    def test_qti_feedback_is_scorer_rubric_not_always_shown_modal(self):
        """Feedback must render as a scorer/tutor rubricBlock (not an always-shown
        modalFeedback that spoils the answer before the learner responds)."""
        from apps.education.qti import build_assessment_item_xml
        root = ET.fromstring(build_assessment_item_xml(
            {'question_type': 'single_choice', 'prompt': 'Q', 'feedback': 'The answer is X',
             'choices': [{'id': 'a', 'text': 'A', 'correct': True}]}, 'IT'))
        self.assertFalse([e for e in root.iter() if e.tag.endswith('}modalFeedback')])
        rubrics = [e for e in root.iter() if e.tag.endswith('}rubricBlock')]
        self.assertTrue(rubrics)
        self.assertEqual(rubrics[0].get('view'), 'scorer tutor')

    def test_qti_empty_choice_item_is_not_autoscored(self):
        from apps.education.qti import build_assessment_item_xml
        root = ET.fromstring(build_assessment_item_xml(
            {'question_type': 'single_choice', 'prompt': 'Q', 'choices': []}, 'IT'))
        # A placeholder simpleChoice keeps it schema-valid...
        self.assertTrue([e for e in root.iter() if e.tag.endswith('}simpleChoice')])
        # ...but with no correct option it must not be auto-scored wrong.
        self.assertEqual([c for c in root if c.tag.endswith('}responseProcessing')], [])


class EducationCollectionBuilderTest(TestCase):
    """Unit test for the collection package builder (accepts plain dicts)."""

    def test_collection_zip_bundles_multiple_entries(self):
        entries = [
            {'heritage_item': None, 'lom_data': {'id': 'a', 'title': 'Alpha'}, 'media_files': []},
            {'heritage_item': None, 'lom_data': {'id': 'b', 'title': 'Beta'}, 'media_files': []},
        ]
        zip_file, filename = build_collection_scorm_zip(
            title='My Route', description='Route desc', entries=entries, package_format='scorm12',
        )
        with zipfile.ZipFile(zip_file, 'r') as zf:
            names = set(zf.namelist())
            self.assertIn('imsmanifest.xml', names)
            self.assertIn('index.html', names)
            self.assertIn('metadata/lom.xml', names)
            # Per-item metadata present for both entries.
            self.assertIn('metadata/Alpha/lom.xml', names)
            self.assertIn('metadata/Beta/lom.xml', names)

            # Manifest has one <item> per entry.
            manifest_root = ET.fromstring(zf.read('imsmanifest.xml'))
            items = [e for e in manifest_root.iter() if e.tag.endswith('}item')]
            self.assertEqual(len(items), 2)

            # Collection LOM declares structure "collection".
            lom_root = ET.fromstring(zf.read('metadata/lom.xml'))
            structure_values = [
                v.text for s in lom_root.iter(f'{{{_LOM_NS}}}structure')
                for v in s.iter(f'{{{_LOM_NS}}}value')
            ]
            self.assertIn('collection', structure_values)


class EducationAssessmentQuestionNestedWriteTest(TestCase):
    """Nested write of questions through LOMGeneralWriteSerializer (replace-all)."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='q_user@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')
        self.item = HeritageItem.objects.create(
            title='Quiz Item', description='Desc',
            heritage_type=self.type, heritage_category=self.category,
            parish=self.parish, location='POINT(0 0)', status='published',
        )
        self.lom = LOMGeneral.objects.create(
            heritage_item=self.item, title='LO', language='es', description='d',
        )

    def test_patch_replaces_question_set(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'questions': [
                {
                    'order': 1,
                    'question_type': 'single_choice',
                    'prompt': '¿Pregunta 1?',
                    'choices': [{'id': 'a', 'text': 'Sí', 'correct': True}],
                },
                {
                    'order': 2,
                    'question_type': 'short_answer',
                    'prompt': '¿Pregunta 2?',
                    'correct_response': 'respuesta',
                },
            ]
        }
        resp = self.client.patch(f'/api/v1/lom/{self.lom.id}/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(self.lom.questions.count(), 2)
        # Read shape exposes the questions.
        self.assertIn('questions', resp.data)
        self.assertEqual(len(resp.data['questions']), 2)

        # A second PATCH replaces (not appends) the set.
        resp2 = self.client.patch(
            f'/api/v1/lom/{self.lom.id}/',
            {'questions': [{'order': 1, 'question_type': 'true_false', 'prompt': '¿Única?', 'correct_response': 'true'}]},
            format='json',
        )
        self.assertEqual(resp2.status_code, status.HTTP_200_OK, resp2.content)
        self.assertEqual(self.lom.questions.count(), 1)

    def test_export_qti_endpoint_returns_zip(self):
        self.client.force_authenticate(user=self.user)
        AssessmentQuestion.objects.create(
            lom_general=self.lom, order=1, question_type='single_choice',
            prompt='¿P?', choices=[{'id': 'a', 'text': 'A', 'correct': True}],
        )
        resp = self.client.get(f'/api/v1/lom-questions/export-qti/?lom_general={self.lom.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/zip')
        content = b''.join(resp.streaming_content)
        with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
            self.assertIn('imsmanifest.xml', set(zf.namelist()))


class EducationRoutePackageAPITest(TestCase):
    """API test: route-package export returns a collection zip for an auth user."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='route_pkg@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')

        self.item_a = HeritageItem.objects.create(
            title='Stop A', description='A', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish,
            location='POINT(0 0)', status='published',
        )
        self.item_b = HeritageItem.objects.create(
            title='Stop B', description='B', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish,
            location='POINT(0 0)', status='published',
        )
        LOMGeneral.objects.create(heritage_item=self.item_a, title='LO A', language='es', description='da')
        LOMGeneral.objects.create(heritage_item=self.item_b, title='LO B', language='es', description='db')

        self.route = HeritageRoute.objects.create(
            title='Ruta Colonial', description='Recorrido por el centro', creator=self.user,
            status='published',
        )
        RouteStop.objects.create(route=self.route, heritage_item=self.item_a, order=1)
        RouteStop.objects.create(route=self.route, heritage_item=self.item_b, order=2)

    def test_route_package_download_returns_collection_zip(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(f'/api/v1/education/route-packages/{self.route.id}/download/')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/zip')

        content = b''.join(resp.streaming_content)
        with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
            names = set(zf.namelist())
            self.assertIn('imsmanifest.xml', names)
            self.assertIn('index.html', names)
            # One <item> per stop in the manifest organization.
            manifest_root = ET.fromstring(zf.read('imsmanifest.xml'))
            items = [e for e in manifest_root.iter() if e.tag.endswith('}item')]
            self.assertEqual(len(items), 2)

    def test_route_package_requires_authentication(self):
        resp = self.client.get(f'/api/v1/education/route-packages/{self.route.id}/download/')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_route_package_scorm2004_format(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(
            f'/api/v1/education/route-packages/{self.route.id}/download/?format=scorm2004'
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        content = b''.join(resp.streaming_content)
        with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
            manifest = zf.read('imsmanifest.xml').decode('utf-8')
            self.assertIn('2004 4th Edition', manifest)


class EducationCollectionPackageAPITest(TestCase):
    """API test: query-param collection export for arbitrary item ids."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='coll_pkg@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')
        self.item_a = HeritageItem.objects.create(
            title='Item A', description='A', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish,
            location='POINT(0 0)', status='published',
        )
        self.item_b = HeritageItem.objects.create(
            title='Item B', description='B', heritage_type=self.type,
            heritage_category=self.category, parish=self.parish,
            location='POINT(0 0)', status='published',
        )
        LOMGeneral.objects.create(heritage_item=self.item_a, title='LO A', language='es', description='da')

    def test_collection_download_with_ids(self):
        self.client.force_authenticate(user=self.user)
        ids = f'{self.item_a.id},{self.item_b.id}'
        resp = self.client.get(f'/api/v1/education/collection-packages/download/?ids={ids}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp['Content-Type'], 'application/zip')
        content = b''.join(resp.streaming_content)
        with zipfile.ZipFile(io.BytesIO(content), 'r') as zf:
            self.assertIn('imsmanifest.xml', set(zf.namelist()))
            manifest_root = ET.fromstring(zf.read('imsmanifest.xml'))
            items = [e for e in manifest_root.iter() if e.tag.endswith('}item')]
            self.assertEqual(len(items), 2)

    def test_collection_download_requires_ids(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get('/api/v1/education/collection-packages/download/')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_collection_download_rejects_oversized_selection(self):
        self.client.force_authenticate(user=self.user)
        too_many = ','.join(str(i) for i in range(51))
        resp = self.client.get(f'/api/v1/education/collection-packages/download/?ids={too_many}')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class EducationReviewFixesTest(TestCase):
    """Regression tests for the F2 code-review fixes."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='rev_user@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')
        self.item = HeritageItem.objects.create(
            title='Rev Item', description='Desc',
            heritage_type=self.type, heritage_category=self.category,
            parish=self.parish, location='POINT(0 0)', status='published',
        )
        self.lom = LOMGeneral.objects.create(
            heritage_item=self.item, title='LO', language='es', description='d',
        )

    def test_anonymous_question_read_hides_answer_key(self):
        AssessmentQuestion.objects.create(
            lom_general=self.lom, order=1, question_type='single_choice',
            prompt='¿Cuál?', choices=[
                {'id': 'a', 'text': 'Sí', 'correct': True},
                {'id': 'b', 'text': 'No', 'correct': False},
            ],
            correct_response='a',
        )
        # Anonymous read: answer key must be stripped.
        resp = self.client.get(f'/api/v1/lom-questions/?lom_general={self.lom.id}')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get('results', resp.data)
        q = results[0]
        self.assertNotIn('correct_response', q)
        for choice in q['choices']:
            self.assertNotIn('correct', choice)
        # Authenticated read: full serializer includes the answer key.
        self.client.force_authenticate(user=self.user)
        resp2 = self.client.get(f'/api/v1/lom-questions/?lom_general={self.lom.id}')
        results2 = resp2.data.get('results', resp2.data)
        self.assertIn('correct_response', results2[0])

    def _nested_questions(self, data):
        """Pull questions[] out of an LOMGeneral-shaped payload."""
        return (data or {}).get('questions', [])

    def test_answer_key_hidden_on_nested_lom_read_paths(self):
        """The answer key must be stripped for anonymous callers on EVERY path
        that nests LOMGeneralSerializer, not just /lom-questions/."""
        AssessmentQuestion.objects.create(
            lom_general=self.lom, order=1, question_type='single_choice',
            prompt='¿Cuál?',
            choices=[{'id': 'a', 'text': 'Sí', 'correct': True},
                     {'id': 'b', 'text': 'No', 'correct': False}],
            correct_response='a',
        )

        def assert_stripped(questions, where):
            self.assertTrue(questions, f'no questions in {where}')
            q = questions[0]
            self.assertNotIn('correct_response', q, where)
            for choice in q.get('choices', []):
                self.assertNotIn('correct', choice, where)

        # /lom/{id}/ (retrieve)
        r = self.client.get(f'/api/v1/lom/{self.lom.id}/')
        assert_stripped(self._nested_questions(r.data), '/lom/{id}/')
        # /lom/by_heritage_item/
        r = self.client.get(f'/api/v1/lom/by_heritage_item/?heritage_item_id={self.item.id}')
        assert_stripped(self._nested_questions(r.data), '/lom/by_heritage_item/')
        # /heritage-items/{id}/ (detail, lom_metadata nested)
        r = self.client.get(f'/api/v1/heritage-items/{self.item.id}/')
        assert_stripped(self._nested_questions(r.data.get('lom_metadata')), '/heritage-items/{id}/')

        # Authenticated curator sees the answer key on the nested path.
        self.client.force_authenticate(user=self.user)
        r = self.client.get(f'/api/v1/lom/{self.lom.id}/')
        q = self._nested_questions(r.data)[0]
        self.assertIn('correct_response', q)

    def test_export_qti_requires_authentication(self):
        AssessmentQuestion.objects.create(
            lom_general=self.lom, order=1, question_type='true_false',
            prompt='¿V o F?', correct_response='true',
        )
        resp = self.client.get(f'/api/v1/lom-questions/export-qti/?lom_general={self.lom.id}')
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    def test_question_update_preserves_uuid_by_id(self):
        q = AssessmentQuestion.objects.create(
            lom_general=self.lom, order=1, question_type='single_choice',
            prompt='Original', choices=[{'id': 'a', 'text': 'A', 'correct': True}],
        )
        original_id = q.id
        self.client.force_authenticate(user=self.user)
        # Sending the row's id matches it by identity → in-place update, same UUID.
        resp = self.client.patch(
            f'/api/v1/lom/{self.lom.id}/',
            {'questions': [{'id': str(original_id), 'order': 1, 'question_type': 'single_choice',
                            'prompt': 'Edited', 'choices': [{'id': 'a', 'text': 'A', 'correct': True}]}]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(self.lom.questions.count(), 1)
        survivor = self.lom.questions.first()
        self.assertEqual(survivor.id, original_id)
        self.assertEqual(survivor.prompt, 'Edited')

    def test_question_reorder_keeps_content_with_its_uuid(self):
        """Reordering questions must keep each UUID attached to ITS content
        (the positional-matching bug swapped content between rows)."""
        q1 = AssessmentQuestion.objects.create(
            lom_general=self.lom, order=1, question_type='short_answer', prompt='First',
        )
        q2 = AssessmentQuestion.objects.create(
            lom_general=self.lom, order=2, question_type='short_answer', prompt='Second',
        )
        self.client.force_authenticate(user=self.user)
        # Send them reordered (q2 first) with ids; new orders swapped.
        resp = self.client.patch(
            f'/api/v1/lom/{self.lom.id}/',
            {'questions': [
                {'id': str(q2.id), 'order': 1, 'question_type': 'short_answer', 'prompt': 'Second'},
                {'id': str(q1.id), 'order': 2, 'question_type': 'short_answer', 'prompt': 'First'},
            ]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        q1.refresh_from_db()
        q2.refresh_from_db()
        # Each UUID still holds its OWN prompt (no content swap), with updated order.
        self.assertEqual(q1.prompt, 'First')
        self.assertEqual(q1.order, 2)
        self.assertEqual(q2.prompt, 'Second')
        self.assertEqual(q2.order, 1)

    def test_question_dropped_from_payload_is_deleted(self):
        q1 = AssessmentQuestion.objects.create(
            lom_general=self.lom, order=1, question_type='short_answer', prompt='Keep',
        )
        q2 = AssessmentQuestion.objects.create(
            lom_general=self.lom, order=2, question_type='short_answer', prompt='Drop',
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.patch(
            f'/api/v1/lom/{self.lom.id}/',
            {'questions': [{'id': str(q1.id), 'order': 1, 'question_type': 'short_answer', 'prompt': 'Keep'}]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(self.lom.questions.count(), 1)
        self.assertEqual(self.lom.questions.first().id, q1.id)
        self.assertFalse(AssessmentQuestion.objects.filter(id=q2.id).exists())

    def test_classification_update_preserves_untouched_rows(self):
        c = LOMClassification.objects.create(
            lom_general=self.lom, purpose='discipline',
            taxon_source='Local', taxon_entry='Arquitectura',
        )
        original_id = c.id
        self.client.force_authenticate(user=self.user)
        resp = self.client.patch(
            f'/api/v1/lom/{self.lom.id}/',
            {'classifications': [{'id': str(original_id), 'purpose': 'discipline',
                                  'taxon_source': 'Local', 'taxon_entry': 'Arquitectura colonial'}]},
            format='json',
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(self.lom.classifications.count(), 1)
        survivor = self.lom.classifications.first()
        self.assertEqual(survivor.id, original_id)
        self.assertEqual(survivor.taxon_entry, 'Arquitectura colonial')

    def test_route_package_rejects_cmi5(self):
        route = HeritageRoute.objects.create(title='R', description='d', status='published')
        RouteStop.objects.create(route=route, heritage_item=self.item, order=1)
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(f'/api/v1/education/route-packages/{route.id}/download/?format=cmi5')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)


class EducationContributionEducationalTest(TestCase):
    """The contribution wizard's educational payload flows into LOM, and invalid
    values surface as a 400 instead of being silently dropped."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='contrib@example.com', password='password')
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Test Parish', canton='Riobamba')

    def _base_payload(self):
        return {
            'title': 'Nuevo', 'description': 'Una descripción',
            'location': {'type': 'Point', 'coordinates': [-78.65, -1.67]},
            'address': '', 'parish': self.parish.id,
            'heritage_type': self.type.id, 'heritage_category': self.category.id,
            'historical_period': 'colonial',
        }

    def test_valid_educational_payload_is_stored(self):
        self.client.force_authenticate(user=self.user)
        payload = self._base_payload()
        payload['educational'] = {
            'difficulty': 'easy', 'context': 'school',
            'typical_learning_time': 'PT30M',
            'learning_objectives': ['Objetivo 1'],
        }
        resp = self.client.post('/api/v1/contributions/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        item = HeritageItem.objects.get(title='Nuevo')
        edu = item.lom_general.educational
        self.assertEqual(edu.difficulty, 'easy')
        self.assertEqual(edu.context, 'school')
        self.assertEqual(edu.typical_learning_time, 'PT30M')

    def test_invalid_educational_payload_returns_400(self):
        self.client.force_authenticate(user=self.user)
        payload = self._base_payload()
        payload['educational'] = {'typical_learning_time': '30 minutos'}  # not ISO-8601
        resp = self.client.post('/api/v1/contributions/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST, resp.content)


class EducationalResourceContentSanitizeTest(TestCase):
    """EducationalResource.content is rendered with v-html in the SPA, so the
    serializer must strip script/handler payloads on write (stored-XSS guard).
    The write endpoint is only IsAuthenticatedOrReadOnly, so a plain tourist is
    the threat model here."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email='tourist@example.com', password='password')

    def test_sanitize_html_helper_strips_scripts_keeps_formatting(self):
        from apps.education.sanitize import sanitize_html
        dirty = (
            '<h2>Lesson</h2><p>Safe <strong>bold</strong> and '
            '<a href="https://x.test">link</a>.</p>'
            '<script>alert(1)</script>'
            '<img src="x" onerror="alert(2)">'
            '<a href="javascript:alert(3)">bad</a>'
        )
        clean = sanitize_html(dirty)
        # Legitimate rich formatting survives.
        self.assertIn('<h2>Lesson</h2>', clean)
        self.assertIn('<strong>bold</strong>', clean)
        self.assertIn('href="https://x.test"', clean)
        # Dangerous constructs are gone.
        self.assertNotIn('<script', clean)
        self.assertNotIn('alert(1)', clean)
        self.assertNotIn('onerror', clean)
        self.assertNotIn('javascript:', clean)

    def test_create_resource_sanitizes_content(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            'title': 'Evil',
            'description': 'x',
            'content': '<p>ok</p><script>document.cookie</script>',
        }
        resp = self.client.post('/api/v1/educational-resources/', payload, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        res = EducationalResource.objects.get(id=resp.data['id'])
        self.assertIn('<p>ok</p>', res.content)
        self.assertNotIn('<script', res.content)
        self.assertNotIn('document.cookie', res.content)
