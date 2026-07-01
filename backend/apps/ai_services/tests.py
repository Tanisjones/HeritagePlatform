import os
import tempfile
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.heritage.models import HeritageItem, HeritageType, HeritageCategory, Parish
from apps.ai_services.models import AISuggestion, AIUsageRecord
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


class AISuggestionApproveTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="mod", email="mod@example.com", password="pw", is_staff=True
        )
        self.type = HeritageType.objects.create(name='Tangible', slug='tangible')
        self.category = HeritageCategory.objects.create(name='Architecture', slug='architecture')
        self.parish = Parish.objects.create(name='Parish')
        self.item = HeritageItem.objects.create(
            title='Item', description='Desc',
            heritage_type=self.type, heritage_category=self.category,
            parish=self.parish, location='POINT(0 0)',
        )

    def test_approve_keyword_suggestion_writes_to_lom(self):
        """Regression: approving a keyword suggestion used to crash with
        AttributeError because HeritageItem has no `keywords`. It must now write
        to LOMGeneral.keywords instead."""
        from apps.education.models import LOMGeneral

        suggestion = AISuggestion.objects.create(
            heritage_item=self.item,
            suggester='gemini',
            suggestion_type='keyword',
            content=['colonial', 'iglesia'],
            confidence=None,
        )
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(f"/api/v1/ai-suggestions/{suggestion.id}/approve/")
        self.assertEqual(resp.status_code, 200)

        lom = LOMGeneral.objects.get(heritage_item=self.item)
        self.assertIn('colonial', lom.keywords)
        self.assertIn('iglesia', lom.keywords)
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, 'approved')

    def test_approve_historical_period_suggestion(self):
        suggestion = AISuggestion.objects.create(
            heritage_item=self.item,
            suggester='gemini',
            suggestion_type='historical_period',
            content='colonial',
            confidence=None,
        )
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(f"/api/v1/ai-suggestions/{suggestion.id}/approve/")
        self.assertEqual(resp.status_code, 200)
        self.item.refresh_from_db()
        self.assertEqual(self.item.historical_period, 'colonial')

    def test_approve_invalid_historical_period_is_rejected(self):
        """An out-of-choices / over-length AI value must 400, not 500 or corrupt."""
        suggestion = AISuggestion.objects.create(
            heritage_item=self.item,
            suggester='gemini',
            suggestion_type='historical_period',
            content='a very long made-up period that is not in the choices list',
            confidence=None,
        )
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post(f"/api/v1/ai-suggestions/{suggestion.id}/approve/")
        self.assertEqual(resp.status_code, 400)
        self.item.refresh_from_db()
        self.assertEqual(self.item.historical_period, '')  # unchanged
        suggestion.refresh_from_db()
        self.assertEqual(suggestion.status, 'pending')  # not approved (atomic)

    def test_non_staff_curator_can_list_and_approve(self):
        """A role='curator' user without is_staff must be able to use the feature
        (the route guard allows curators; the API must match)."""
        from apps.users.models import UserRole, UserProfile

        role, _ = UserRole.objects.get_or_create(name='Curator', slug='curator')
        curator = User.objects.create_user(
            username='cur', email='cur@example.com', password='pw'
        )
        UserProfile.objects.create(user=curator, role=role)
        suggestion = AISuggestion.objects.create(
            heritage_item=self.item, suggester='gemini',
            suggestion_type='historical_period', content='colonial', confidence=None,
        )
        self.client.force_authenticate(user=curator)
        self.assertEqual(self.client.get("/api/v1/ai-suggestions/").status_code, 200)
        resp = self.client.post(f"/api/v1/ai-suggestions/{suggestion.id}/approve/")
        self.assertEqual(resp.status_code, 200)

    def test_viewset_is_read_only_no_direct_create(self):
        """The viewset must not allow direct POST creation (only approve/reject)."""
        self.client.force_authenticate(user=self.staff)
        resp = self.client.post("/api/v1/ai-suggestions/", {
            "heritage_item": str(self.item.id),
            "suggester": "x", "suggestion_type": "keyword",
            "content": ["x"], "status": "approved",
        }, format="json")
        self.assertEqual(resp.status_code, 405)  # method not allowed


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

    @patch("httpx.Client.post")
    def test_educational_metadata_success(self, post_mock):
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={
                "message": {
                    "content": (
                        '{"learning_resource_type":"narrative_text","difficulty":"medium",'
                        '"typical_age_range":"12-14","typical_learning_time":"PT30M",'
                        '"context":"school","learning_objectives":["Entender la historia"],'
                        '"keywords":["colonial","iglesia"]}'
                    )
                }
            },
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/educational-metadata/",
            {"language": "es", "title": "Iglesia", "resource_type": "text"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["difficulty"], "medium")
        self.assertEqual(resp.data["learning_objectives"], ["Entender la historia"])

    @patch("httpx.Client.post")
    def test_route_metadata_success(self, post_mock):
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={
                "message": {
                    "content": (
                        '{"description":"Un recorrido por el centro histórico.",'
                        '"theme":"arquitectura colonial","difficulty":"easy",'
                        '"estimated_duration":"PT2H"}'
                    )
                }
            },
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/route-metadata/",
            {
                "language": "es",
                "title": "Centro Histórico",
                "stops": [
                    {"title": "Catedral", "description": "Catedral de Riobamba"},
                    {"title": "Parque Maldonado", "description": "Plaza central"},
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["theme"], "arquitectura colonial")
        self.assertEqual(resp.data["difficulty"], "easy")
        self.assertEqual(resp.data["estimated_duration"], "PT2H")

    @patch("httpx.Client.post")
    def test_route_metadata_rejects_extra_keys(self, post_mock):
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={
                "message": {
                    "content": '{"description":"x","theme":"y","difficulty":"easy","bogus":1}'
                }
            },
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/route-metadata/",
            {"language": "es", "title": "R"},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)

    @patch("httpx.Client.post")
    def test_translate_success(self, post_mock):
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={
                "message": {
                    "content": '{"title":"Church","description":"A colonial church","keywords":["colonial"]}'
                }
            },
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/translate/",
            {
                "source_lang": "es",
                "target_lang": "en",
                "fields": {"title": "Iglesia", "description": "Una iglesia colonial"},
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "Church")

    @patch("httpx.Client.post")
    def test_translate_requires_auth(self, post_mock):
        resp = self.client.post(
            "/api/v1/ai/assist/translate/",
            {"source_lang": "es", "target_lang": "en", "fields": {"title": "x"}},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)
        post_mock.assert_not_called()


class AIConfigLoadTest(TestCase):
    def _load(self, yaml_text: str):
        import tempfile
        from apps.ai_services.ai_config import _load_ai_config_cached, reload_ai_config

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_text)
            path = f.name
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        # Clear the lru_cache afterwards so a temp-path entry can't leak.
        self.addCleanup(reload_ai_config)
        # Bypass the path/env resolution; call the cached loader directly per path.
        return _load_ai_config_cached(path)

    def test_gemini_config_without_base_url_loads(self):
        """base_url is Ollama-only; a Gemini config may omit it."""
        cfg = self._load(
            """
ai:
  enabled: true
  provider: gemini
  model: gemini-2.0-flash
  api_key_env: SOME_KEY
  request_timeout_seconds: 30
  temperature: 0.2
  max_output_tokens: 50
  allowed_operations: [contribution_draft]
  prompts: {contribution_draft: "x {{language}}"}
"""
        )
        self.assertEqual(cfg.provider, "gemini")
        self.assertEqual(cfg.base_url, "")

    def test_ollama_config_without_base_url_raises(self):
        from apps.ai_services.ai_config import AIConfigError

        with self.assertRaises(AIConfigError):
            self._load(
                """
ai:
  enabled: true
  provider: ollama
  model: llama3.2:1b
  request_timeout_seconds: 30
  temperature: 0.2
  max_output_tokens: 50
  allowed_operations: [contribution_draft]
  prompts: {contribution_draft: "x {{language}}"}
"""
            )

    def test_auto_suggest_defaults_off(self):
        cfg = self._load(
            """
ai:
  enabled: true
  provider: gemini
  model: gemini-2.0-flash
  request_timeout_seconds: 30
  temperature: 0.2
  max_output_tokens: 50
  allowed_operations: [contribution_draft]
  prompts: {contribution_draft: "x {{language}}"}
"""
        )
        self.assertFalse(cfg.auto_suggest_on_create)


def _gemini_text_response(text: str) -> "_MockHTTPXResponse":
    """Build a mock Gemini generateContent response wrapping `text`."""
    return _MockHTTPXResponse(
        status_code=200,
        json_data={"candidates": [{"content": {"parts": [{"text": text}]}}]},
    )


_GEMINI_YAML = """
ai:
  enabled: true
  provider: gemini
  base_url: http://unused
  model: gemini-2.0-flash
  api_key_env: TEST_GEMINI_KEY
  request_timeout_seconds: 30
  temperature: 0.2
  max_output_tokens: 50
  allowed_operations: [contribution_draft]
  prompts: {contribution_draft: "draft {{language}}"}
"""


class GeminiProviderTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="g1", email="g1@example.com", password="pw")
        # Write a temp ai.yaml configured for the Gemini provider.
        self._tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        self._tmp.write(_GEMINI_YAML)
        self._tmp.close()
        os.environ["AI_CONFIG_PATH"] = self._tmp.name

    def tearDown(self):
        os.environ.pop("AI_CONFIG_PATH", None)
        os.environ.pop("TEST_GEMINI_KEY", None)
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass
        # Drop the cached config so other tests reload the default ai.yaml.
        from apps.ai_services.ai_config import reload_ai_config

        try:
            reload_ai_config()
        except Exception:  # noqa: BLE001
            pass

    @patch("httpx.post")
    def test_gemini_draft_success(self, post_mock):
        os.environ["TEST_GEMINI_KEY"] = "secret-key"
        from apps.ai_services.ai_config import reload_ai_config

        reload_ai_config()  # pick up provider=gemini + the key from env
        post_mock.return_value = _gemini_text_response('{"title":"T","description":"D"}')

        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/contribution-draft/",
            {"language": "es"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["title"], "T")
        # Verify we actually called the Gemini endpoint, not Ollama.
        self.assertTrue(post_mock.called)
        called_url = post_mock.call_args.args[0]
        self.assertIn("generativelanguage.googleapis.com", called_url)

    @patch("httpx.post")
    def test_gemini_without_key_is_unavailable(self, post_mock):
        # No TEST_GEMINI_KEY set → key unresolved.
        from apps.ai_services.ai_config import reload_ai_config

        reload_ai_config()
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/contribution-draft/",
            {"language": "es"},
            format="json",
        )
        self.assertEqual(resp.status_code, 503)
        post_mock.assert_not_called()

    @patch("httpx.get")
    def test_status_reports_missing_key(self, get_mock):
        from apps.ai_services.ai_config import reload_ai_config

        reload_ai_config()
        resp = self.client.get("/api/v1/ai/status/")
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.data["available"])
        self.assertEqual(resp.data["provider"], "gemini")
        self.assertIn("key", resp.data["reason"].lower())
        # Health short-circuits on missing key without a network call.
        get_mock.assert_not_called()


class AIUsageRecordingTest(TestCase):
    """Every AI operation attempt (success, provider error, rate-limit) leaves
    exactly one AIUsageRecord, with tokens/cost when the provider reports them."""

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="ru", email="ru@example.com", password="pw")

    @patch("httpx.Client.post")
    def test_successful_call_records_usage_with_tokens(self, post_mock):
        # Ollama reports prompt_eval_count / eval_count on the /api/chat response.
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={
                "message": {"content": '{"title":"T","description":"D"}'},
                "prompt_eval_count": 120,
                "eval_count": 45,
            },
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/contribution-draft/",
            {"language": "es", "notes": "x"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

        records = AIUsageRecord.objects.all()
        self.assertEqual(records.count(), 1)
        rec = records.first()
        self.assertEqual(rec.status, AIUsageRecord.STATUS_OK)
        self.assertEqual(rec.operation, "contribution_draft")
        self.assertEqual(rec.provider, "ollama")
        self.assertEqual(rec.input_tokens, 120)
        self.assertEqual(rec.output_tokens, 45)
        self.assertEqual(rec.total_tokens, 165)
        self.assertEqual(rec.user_id, self.user.id)
        # Local Ollama model → priced at 0 via the "*" pricing fallback.
        self.assertEqual(rec.estimated_cost_usd, 0)
        self.assertIsNotNone(rec.duration_ms)

    @patch("httpx.Client.post")
    def test_provider_error_records_error_status(self, post_mock):
        post_mock.return_value = _MockHTTPXResponse(status_code=500, json_data={})
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/contribution-draft/",
            {"language": "es"},
            format="json",
        )
        self.assertEqual(resp.status_code, 503)
        rec = AIUsageRecord.objects.get()
        self.assertEqual(rec.status, AIUsageRecord.STATUS_ERROR)
        self.assertTrue(rec.error_type)
        self.assertIsNone(rec.total_tokens)

    @patch("httpx.Client.post")
    def test_missing_usage_fields_records_null_tokens(self, post_mock):
        # A model/version that omits token counts → usage stays None, still recorded.
        post_mock.return_value = _MockHTTPXResponse(
            status_code=200,
            json_data={"message": {"content": '{"title":"T","description":"D"}'}},
        )
        self.client.force_authenticate(user=self.user)
        resp = self.client.post(
            "/api/v1/ai/assist/contribution-draft/",
            {"language": "es"},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)
        rec = AIUsageRecord.objects.get()
        self.assertEqual(rec.status, AIUsageRecord.STATUS_OK)
        self.assertIsNone(rec.input_tokens)
        self.assertIsNone(rec.total_tokens)


class AIUsageAggregationTest(TestCase):
    """G.4 — /ai/usage/{summary,timeseries,recent} aggregation endpoints.

    Records are created directly (not via the AI pipeline) so we control tokens,
    cost, provider, operation and timestamp precisely. `created_at` is auto_now_add,
    so we backdate rows with an explicit .update() after create.
    """

    def setUp(self):
        from decimal import Decimal
        from datetime import timedelta
        from django.utils import timezone

        self.client = APIClient()
        self.staff = User.objects.create_user(
            username="mod2", email="mod2@example.com", password="pw", is_staff=True
        )
        self.tourist = User.objects.create_user(
            username="tour", email="tour@example.com", password="pw"
        )

        today = timezone.localdate()
        now = timezone.now()

        def mk(*, operation, provider, model, inp, out, cost, status_, when, user=None):
            rec = AIUsageRecord.objects.create(
                user=user,
                operation=operation,
                provider=provider,
                model=model,
                input_tokens=inp,
                output_tokens=out,
                total_tokens=(None if inp is None else inp + out),
                estimated_cost_usd=(None if cost is None else Decimal(cost)),
                duration_ms=120,
                status=status_,
            )
            AIUsageRecord.objects.filter(pk=rec.pk).update(created_at=when)
            return rec

        # Two ops, two providers, three days, one error row, one old (out-of-window) row.
        mk(operation="translate", provider="gemini", model="gemini-2.0-flash",
           inp=100, out=50, cost="0.0000225", status_="ok", when=now, user=self.staff)
        mk(operation="translate", provider="gemini", model="gemini-2.0-flash",
           inp=200, out=100, cost="0.0000450", status_="ok", when=now - timedelta(days=1))
        mk(operation="route_metadata", provider="ollama", model="llama3",
           inp=None, out=None, cost=None, status_="ok", when=now - timedelta(days=2))
        mk(operation="translate", provider="gemini", model="gemini-2.0-flash",
           inp=None, out=None, cost=None, status_="error", when=now - timedelta(days=1))
        # Far outside the default 30-day window — must be excluded by default.
        mk(operation="translate", provider="gemini", model="gemini-2.0-flash",
           inp=999, out=999, cost="1.0", status_="ok", when=now - timedelta(days=200))

        self.today = today

    # ---- permissions -------------------------------------------------------

    def test_summary_requires_staff_or_curator(self):
        # Anonymous
        resp = self.client.get("/api/v1/ai/usage/summary/")
        self.assertIn(resp.status_code, (401, 403))
        # Authenticated tourist
        self.client.force_authenticate(user=self.tourist)
        resp = self.client.get("/api/v1/ai/usage/summary/")
        self.assertEqual(resp.status_code, 403)

    def test_curator_role_can_access(self):
        from apps.users.models import UserRole, UserProfile
        role, _ = UserRole.objects.get_or_create(name="Curator", slug="curator")
        curator = User.objects.create_user(username="cur2", email="cur2@example.com", password="pw")
        UserProfile.objects.create(user=curator, role=role)
        self.client.force_authenticate(user=curator)
        resp = self.client.get("/api/v1/ai/usage/summary/")
        self.assertEqual(resp.status_code, 200)

    # ---- summary -----------------------------------------------------------

    def test_summary_by_operation_excludes_old_and_sums(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get("/api/v1/ai/usage/summary/?group_by=operation")
        self.assertEqual(resp.status_code, 200, resp.content)
        body = resp.data
        self.assertEqual(body["group_by"], "operation")
        rows = {r["key"]: r for r in body["rows"]}
        # translate: 3 in-window rows (2 ok + 1 error); the 200-day-old row excluded.
        self.assertEqual(rows["translate"]["calls"], 3)
        self.assertEqual(rows["translate"]["total_tokens"], 450)  # 150 + 300 + 0(error)
        self.assertEqual(rows["route_metadata"]["calls"], 1)
        # Totals across all in-window rows = 4 calls (old one excluded).
        self.assertEqual(body["totals"]["calls"], 4)
        # Cost sums the priced rows. NB: estimated_cost_usd is DecimalField(…,6), so
        # each row is already quantised to 6dp on write: 0.0000225→0.000023,
        # 0.0000450→0.000045; their sum is 0.000068. (Sub-µdollar per-call rounding
        # is acceptable for a spend dashboard.)
        self.assertEqual(body["totals"]["estimated_cost_usd"], "0.000068")

    def test_summary_group_by_provider_and_model(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get("/api/v1/ai/usage/summary/?group_by=model")
        self.assertEqual(resp.status_code, 200)
        rows = {r["key"]: r for r in resp.data["rows"]}
        self.assertIn("gemini/gemini-2.0-flash", rows)
        self.assertIn("ollama/llama3", rows)

    def test_summary_rejects_bad_group_by(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get("/api/v1/ai/usage/summary/?group_by=bogus")
        self.assertEqual(resp.status_code, 400)

    def test_summary_rejects_inverted_range(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get("/api/v1/ai/usage/summary/?since=2026-02-01&until=2026-01-01")
        self.assertEqual(resp.status_code, 400)

    # ---- timeseries --------------------------------------------------------

    def test_timeseries_buckets_by_day(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get("/api/v1/ai/usage/timeseries/")
        self.assertEqual(resp.status_code, 200)
        points = resp.data["points"]
        # 3 distinct in-window days had activity (today, -1d, -2d).
        self.assertEqual(len(points), 3)
        for p in points:
            self.assertIn("date", p)
            self.assertIn("total_tokens", p)
            self.assertIn("estimated_cost_usd", p)

    # ---- recent ------------------------------------------------------------

    def test_recent_returns_rows_newest_first_with_limit(self):
        self.client.force_authenticate(user=self.staff)
        resp = self.client.get("/api/v1/ai/usage/recent/?limit=2")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["count"], 2)
        results = resp.data["results"]
        # Newest first.
        self.assertGreaterEqual(results[0]["created_at"], results[1]["created_at"])
        # Audit rows never leak prompts/responses — only metrics + who/what.
        self.assertIn("operation", results[0])
        self.assertIn("estimated_cost_usd", results[0])
        self.assertNotIn("prompt", results[0])
