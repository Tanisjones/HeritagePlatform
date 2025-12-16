import os
import tempfile
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish
from apps.ai_services.models import AISuggestion
from rest_framework.test import APIClient

User = get_user_model()

class AISuggestionModelTest(TestCase):
    def setUp(self):
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Parish')
        self.item = HeritageItem.objects.create(
            title='Item', description='Desc', 
            heritage_type=self.type, heritage_category=self.category, 
            parish=self.parish, location='POINT(0 0)'
        )

    def test_create_suggestion(self):
        suggestion = AISuggestion.objects.create(
            heritage_item=self.item,
            suggester='Gemini',
            suggestion_type='description_enhancement',
            content={'text': 'Better description'},
            confidence=0.95
        )
        self.assertEqual(suggestion.heritage_item, self.item)
        self.assertEqual(suggestion.status, 'pending')
        self.assertEqual(suggestion.confidence, 0.95)


class _MockHTTPXResponse:
    def __init__(self, *, status_code: int, json_data):
        self.status_code = status_code
        self._json_data = json_data

    def json(self):
        return self._json_data


class AIAssistEndpointsTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u1", email="u1@example.com", password="pw")
        self.staff = User.objects.create_user(
            username="s1", email="s1@example.com", password="pw", is_staff=True
        )

    @patch("httpx.Client.post")
    def test_contribution_draft_requires_auth(self, post_mock):
        resp = self.client.post("/api/v1/ai/assist/contribution-draft/", {"language": "es"}, format="json")
        self.assertEqual(resp.status_code, 401)
        post_mock.assert_not_called()

    @patch("httpx.Client.post")
    def test_contribution_draft_success(self, post_mock):
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={"message": {"content": '{"title":"Titulo","description":"Descripcion"}'}},
        )

        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/contribution-draft/",
            {"language": "es", "notes": "algo"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "Titulo")
        self.assertEqual(resp.data["description"], "Descripcion")

    @patch("httpx.Client.post")
    def test_curator_review_requires_staff(self, post_mock):
        self.client.force_authenticate(user=self.user)
        resp = self.client.post("/api/v1/ai/assist/curator-review/", {"language": "es"}, format="json")
        self.assertEqual(resp.status_code, 403)
        post_mock.assert_not_called()

    @patch("httpx.Client.post")
    def test_retry_on_invalid_json_then_success(self, post_mock):
        post_mock.side_effect = [
            _MockHTTPXResponse(status_code=200, json_data={"message": {"content": "not json"}}),
            _MockHTTPXResponse(
                status_code=200,
                json_data={"message": {"content": '{"title":"T","description":"D"}'}},
            ),
        ]

        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/contribution-draft/",
            {"language": "es"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "T")
        self.assertEqual(post_mock.call_count, 2)

    @patch("httpx.Client.post")
    def test_ai_disabled_returns_503(self, post_mock):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                """
ai:
  enabled: false
  provider: ollama
  base_url: http://ollama:11434
  model: llama3.2:1b
  request_timeout_seconds: 30
  temperature: 0.2
  max_output_tokens: 10
  allowed_operations: [contribution_draft]
  prompts: {contribution_draft: "x {{language}}"}
"""
            )
            path = f.name

        try:
            os.environ["AI_CONFIG_PATH"] = path
            self.client.force_authenticate(user=self.user)
            resp = self.client.post(
                "/api/v1/ai/assist/contribution-draft/",
                {"language": "es"},
                format="json",
            )
            self.assertEqual(resp.status_code, 503)
            post_mock.assert_not_called()
        finally:
            os.environ.pop("AI_CONFIG_PATH", None)
            try:
                os.unlink(path)
            except OSError:
                pass

    @patch("httpx.Client.post")
    def test_response_with_extra_keys_is_rejected(self, post_mock):
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={"message": {"content": '{"title":"T","description":"D","extra":123}'}},
        )

        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/contribution-draft/",
            {"language": "es"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("httpx.Client.post")
    def test_curator_suggested_edits_is_strict_object(self, post_mock):
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={
                "message": {
                    "content": (
                        '{"missing_fields":[],"risk_flags":[],"curator_feedback_draft":"x",'
                        '"suggested_edits":{"unknown_key":"y"}}'
                    )
                }
            },
        )

        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(
            "/api/v1/ai/assist/curator-review/",
            {"language": "es", "text": "hi"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
