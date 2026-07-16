"""test_servicenow_client.py — the tests of the servicenow_client.py.

The covered areas:
  - Dry-run mode: a mock Story from a file, a missing Story, a mock KB creation
  - Protocol compatibility (the get_story + create_kb_article methods)
  - Live mode with a mock HTTP (requests mock): GET story (number + sys_id),
    POST kb_knowledge, the error codes (401/403/404/500)
  - Building the StoryData from the response (story_fields, display values)
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from snow_kb.config import ServiceNowConfig, Settings
from snow_kb.schemas import KBArticle, StoryData
from snow_kb.servicenow_client import (
    AuthError,
    DEFAULT_SAMPLE_DIR,
    ServiceNowClient,
    ServiceNowError,
    StoryNotFound,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def dry_run_settings() -> Settings:
    return Settings(
        dry_run=True,
        snow=ServiceNowConfig(knowledge_base_id="kb_test_123"),
    )


@pytest.fixture
def live_settings() -> Settings:
    return Settings(
        dry_run=False,
        snow_instance="demo.service-now.com",
        snow_username="api-user",
        snow_password="secret",
        openai_api_key="sk-test",
        snow=ServiceNowConfig(
            knowledge_base_id="kb_test_123",
            story_table="rm_story",
        ),
    )


@pytest.fixture
def sample_story_data() -> dict:
    """A data/sample_stories/STRY0012345.json tartalma."""
    return {
        "number": "STRY0012345",
        "sys_id": "a1b2c3d4e5f67890a1b2c3d4e5f67890",
        "short_description": "Fix SSO login failure",
        "description": "Users cannot log in via SSO.",
        "u_technical_specification": "Patch auth middleware.",
        "state": "Closed Complete",
        "assigned_to": "Jane Dev",
    }


@pytest.fixture
def sample_story_file(tmp_path, sample_story_data):
    """A temporary mock Story file in the tmp_path."""
    story_dir = tmp_path / "sample_stories"
    story_dir.mkdir()
    path = story_dir / "STRY0012345.json"
    path.write_text(json.dumps(sample_story_data), encoding="utf-8")
    return story_dir


@pytest.fixture
def valid_kb_article() -> KBArticle:
    return KBArticle(
        title="Resolving SSO Login Failures After Upgrade",
        html="<h2>Solution</h2><ol><li>Patch middleware.</li></ol>",
        category="IT",
        knowledge_base_id="kb_test_123",
    )


# ---------------------------------------------------------------------------
# The Protocol compatibility
# ---------------------------------------------------------------------------

class TestProtocolCompliance:
    """The ServiceNowClient implements the Protocol of the pipeline."""

    def test_has_get_story(self, dry_run_settings):
        client = ServiceNowClient(dry_run_settings)
        assert hasattr(client, "get_story") and callable(client.get_story)

    def test_has_create_kb_article(self, dry_run_settings):
        client = ServiceNowClient(dry_run_settings)
        assert hasattr(client, "create_kb_article") and callable(client.create_kb_article)


# ---------------------------------------------------------------------------
# Dry-run: get_story (from a mock file)
# ---------------------------------------------------------------------------

class TestGetStoryDryRun:
    """In dry-run mode the Story is loaded from a local file."""

    def test_loads_existing_story(self, dry_run_settings, sample_story_file, sample_story_data):
        client = ServiceNowClient(dry_run_settings, sample_dir=sample_story_file)
        story = client.get_story("STRY0012345")
        assert story.number == "STRY0012345"
        assert story.short_description == "Fix SSO login failure"
        assert story.u_technical_specification == "Patch auth middleware."

    def test_missing_story_raises(self, dry_run_settings, sample_story_file):
        client = ServiceNowClient(dry_run_settings, sample_dir=sample_story_file)
        with pytest.raises(StoryNotFound, match="STRY9999"):
            client.get_story("STRY9999999")

    def test_returns_story_data_type(self, dry_run_settings, sample_story_file):
        client = ServiceNowClient(dry_run_settings, sample_dir=sample_story_file)
        story = client.get_story("STRY0012345")
        assert isinstance(story, StoryData)

    def test_uses_default_sample_dir_if_not_specified(self, dry_run_settings):
        """If there is no sample_dir, it uses the DEFAULT_SAMPLE_DIR."""
        client = ServiceNowClient(dry_run_settings)
        assert client.sample_dir == DEFAULT_SAMPLE_DIR

    def test_dry_run_flag_override(self, dry_run_settings):
        """The dry_run flag can be overridden in the constructor."""
        client = ServiceNowClient(dry_run_settings, dry_run=False)
        assert client.dry_run is False


# ---------------------------------------------------------------------------
# Dry-run: create_kb_article (mock)
# ---------------------------------------------------------------------------

class TestCreateKbArticleDryRun:
    """In dry-run mode the KB creation is simulated."""

    def test_returns_dummy_sys_id(self, dry_run_settings, valid_kb_article):
        client = ServiceNowClient(dry_run_settings)
        sys_id = client.create_kb_article(valid_kb_article)
        assert sys_id == "dry_run_dummy_sys_id"

    def test_does_not_call_http(self, dry_run_settings, valid_kb_article):
        client = ServiceNowClient(dry_run_settings)
        with patch.object(client, "_request") as mock_request:
            client.create_kb_article(valid_kb_article)
            mock_request.assert_not_called()


# ---------------------------------------------------------------------------
# Live: get_story (mock HTTP)
# ---------------------------------------------------------------------------

class TestGetStoryLive:
    """Live mode — the HTTP calls are mocked."""

    def _mock_response(self, json_data, status_code=200):
        resp = MagicMock(spec=requests.Response)
        resp.status_code = status_code
        resp.json.return_value = json_data
        resp.ok = status_code < 400
        resp.text = json.dumps(json_data)
        return resp

    def test_get_story_by_number(self, live_settings, sample_story_data):
        client = ServiceNowClient(live_settings)
        mock_resp = self._mock_response({"result": [sample_story_data]})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            story = client.get_story("STRY0012345")
            assert story.number == "STRY0012345"
            mock_req.assert_called_once()
            # We check that it used a number query
            args, kwargs = mock_req.call_args
            assert kwargs["params"]["sysparm_query"] == "number=STRY0012345"

    def test_get_story_by_sys_id(self, live_settings, sample_story_data):
        """A 32 character identifier -> a sys_id based GET."""
        client = ServiceNowClient(live_settings)
        sys_id = "a1b2c3d4e5f67890a1b2c3d4e5f67890"
        mock_resp = self._mock_response({"result": sample_story_data})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            story = client.get_story(sys_id)
            assert story.sys_id == sys_id
            args, kwargs = mock_req.call_args
            # The URL contains the sys_id directly
            assert sys_id in args[1]

    def test_story_not_found_empty_result(self, live_settings):
        client = ServiceNowClient(live_settings)
        mock_resp = self._mock_response({"result": []})
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(StoryNotFound):
                client.get_story("STRY0000")

    def test_uses_story_table_from_settings(self, live_settings, sample_story_data):
        """The story_table comes from the settings (rm_story, not a hardcoded story)."""
        client = ServiceNowClient(live_settings)
        mock_resp = self._mock_response({"result": [sample_story_data]})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.get_story("STRY0012345")
            args, kwargs = mock_req.call_args
            assert "rm_story" in args[1]

    def test_requests_display_value_true(self, live_settings, sample_story_data):
        """sysparm_display_value=true for resolving the journal fields."""
        client = ServiceNowClient(live_settings)
        mock_resp = self._mock_response({"result": [sample_story_data]})
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.get_story("STRY0012345")
            kwargs = mock_req.call_args.kwargs
            assert kwargs["params"]["sysparm_display_value"] == "true"


# ---------------------------------------------------------------------------
# Live: create_kb_article (mock HTTP)
# ---------------------------------------------------------------------------

class TestCreateKbArticleLive:
    """Live mode KB creation — the HTTP POST is mocked."""

    def test_returns_sys_id(self, live_settings, valid_kb_article):
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": {"sys_id": "new_kb_abc123"}}
        mock_resp.status_code = 201
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            sys_id = client.create_kb_article(valid_kb_article)
            assert sys_id == "new_kb_abc123"
            mock_req.assert_called_once()
            assert mock_req.call_args.args[0] == "POST"

    def test_payload_contains_kb_fields(self, live_settings, valid_kb_article):
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": {"sys_id": "x"}}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.create_kb_article(valid_kb_article)
            payload = mock_req.call_args.kwargs["json"]
            assert payload["short_description"] == valid_kb_article.title
            assert payload["text"] == valid_kb_article.html
            assert payload["knowledge_base"] == "kb_test_123"
            assert payload["article_type"] == "text"

    def test_uses_kb_id_from_article_over_settings(self, live_settings, valid_kb_article):
        """If the article.knowledge_base_id is given, it overwrites the settings."""
        valid_kb_article.knowledge_base_id = "article_kb_override"
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": {"sys_id": "x"}}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            client.create_kb_article(valid_kb_article)
            payload = mock_req.call_args.kwargs["json"]
            assert payload["knowledge_base"] == "article_kb_override"

    def test_malformed_response_raises(self, live_settings, valid_kb_article):
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"unexpected": "format"}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp):
            with pytest.raises(ServiceNowError, match="Unexpected"):
                client.create_kb_article(valid_kb_article)


# ---------------------------------------------------------------------------
# T003/T005: Foundation tests (find_existing_kb_article, PATCH update)
# ---------------------------------------------------------------------------

class TestKbDuplicatePrevention:
    """The tests of the client methods needed to prevent duplication."""

    def test_find_existing_kb_article_returns_sys_id(self, live_settings):
        """If an article with the source_story field already exists, it returns the sys_id."""
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": [{"sys_id": "existing_kb_123"}]}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            sys_id = client.find_existing_kb_article("STRY0010005")
            assert sys_id == "existing_kb_123"
            # We check that the query goes for the source_story
            args, kwargs = mock_req.call_args
            assert "u_source_story=STRY0010005" in kwargs["params"]["sysparm_query"]

    def test_find_existing_kb_article_returns_none_if_not_found(self, live_settings):
        """If there is no article, it returns None."""
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": []}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp):
            assert client.find_existing_kb_article("STRY9999") is None

    def test_create_kb_article_patches_when_existing_sys_id_given(self, live_settings, valid_kb_article):
        """If an existing_sys_id is given, it starts a PATCH call, not a POST."""
        client = ServiceNowClient(live_settings)
        valid_kb_article.source_story = "STRY0010005"
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": {"sys_id": "existing_kb_123"}}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            sys_id = client.create_kb_article(valid_kb_article, existing_sys_id="existing_kb_123")
            assert sys_id == "existing_kb_123"
            # We check that it was a PATCH
            assert mock_req.call_args.args[0] == "PATCH"
            assert "existing_kb_123" in mock_req.call_args.args[1]
            # The payload contains the new content, but NOT the source_story (it is already set)
            payload = mock_req.call_args.kwargs["json"]
            assert "u_source_story" not in payload

    def test_create_kb_article_post_includes_source_story(self, live_settings, valid_kb_article):
        """If a new article is created (POST), the payload contains the source_story."""
        client = ServiceNowClient(live_settings)
        valid_kb_article.source_story = "STRY0010005"
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": {"sys_id": "new_kb_456"}}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            sys_id = client.create_kb_article(valid_kb_article)
            assert sys_id == "new_kb_456"
            assert mock_req.call_args.args[0] == "POST"
            payload = mock_req.call_args.kwargs["json"]
            assert payload["u_source_story"] == "STRY0010005"


# ---------------------------------------------------------------------------
# The error handling (_request)
# ---------------------------------------------------------------------------

class TestRequestErrorHandling:
    """The error handling tests of the unified _request."""

    def test_401_raises_auth_error(self, live_settings):
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 401
        mock_resp.ok = False
        with patch.object(client.session, "request", return_value=mock_resp):
            with pytest.raises(AuthError):
                client._request("GET", "https://example-service.com/api")

    def test_403_raises_auth_error(self, live_settings):
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 403
        mock_resp.ok = False
        with patch.object(client.session, "request", return_value=mock_resp):
            with pytest.raises(AuthError):
                client._request("GET", "https://example-service.com/api")

    def test_404_raises_story_not_found(self, live_settings):
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 404
        mock_resp.ok = False
        with patch.object(client.session, "request", return_value=mock_resp):
            with pytest.raises(StoryNotFound):
                client._request("GET", "https://example-service.com/api")

    def test_500_raises_servicenow_error(self, live_settings):
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.status_code = 500
        mock_resp.ok = False
        mock_resp.text = "Internal Server Error"
        with patch.object(client.session, "request", return_value=mock_resp):
            with pytest.raises(ServiceNowError, match="500"):
                client._request("GET", "https://example-service.com/api")

    def test_connection_error_raises_servicenow_error(self, live_settings):
        client = ServiceNowClient(live_settings)
        with patch.object(client.session, "request", side_effect=requests.ConnectionError("refused")):
            with pytest.raises(ServiceNowError, match="Connection error"):
                client._request("GET", "https://example-service.com/api")

    def test_timeout_raises_servicenow_error(self, live_settings):
        client = ServiceNowClient(live_settings)
        with patch.object(client.session, "request", side_effect=requests.Timeout("30s")):
            with pytest.raises(ServiceNowError, match="Timeout"):
                client._request("GET", "https://example-service.com/api")

    def test_base_url_uses_instance(self, live_settings):
        client = ServiceNowClient(live_settings)
        assert client.base_url == "https://demo.service-now.com/api/now/table"


# ---------------------------------------------------------------------------
# T003: Team-Based KB Templates tests
# ---------------------------------------------------------------------------

class TestTeamTemplates:
    """The tests of fetching the team specific templates."""

    def test_get_team_template_returns_text(self, live_settings):
        """If there is a KB for the team, it returns the text field."""
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": [{"text": "<h1>Network Template</h1>"}]}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp) as mock_req:
            template = client.get_team_template("group_sys_id_123")
            assert template == "<h1>Network Template</h1>"
            # Check that the query goes to u_assignment_group
            args, kwargs = mock_req.call_args
            assert "u_assignment_group=group_sys_id_123" in kwargs["params"]["sysparm_query"]

    def test_get_team_template_returns_none_if_not_found(self, live_settings):
        """If there is no KB for the team, it returns None."""
        client = ServiceNowClient(live_settings)
        mock_resp = MagicMock(spec=requests.Response)
        mock_resp.json.return_value = {"result": []}
        mock_resp.ok = True
        with patch.object(client, "_request", return_value=mock_resp):
            assert client.get_team_template("unknown_group") is None
