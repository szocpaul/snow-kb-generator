"""test_server.py — a FastAPI server.py tesztek.

Le fedett területek:
  - /health végpont (státusz, dry_run)
  - /generate-kb végpont (sikeres generálás, hitelesítés, hibakezelés)
  - API kulcs ellenőrzés (hiányzó/rossz/jó kulcs)
  - ServiceNow hiba kezelés (502)
  - Config hiba kezelés (500)

A pipeline mockolva van (LM hívás nélkül).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from snow_kb.config import ConfigError, Settings, ServiceNowConfig
from snow_kb.schemas import KBArticle
from snow_kb.server import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_settings():
    return Settings(
        dry_run=True,
        snow_instance="dev300344.service-now.com",
        snow=ServiceNowConfig(knowledge_base_id="kb_test"),
    )


@pytest.fixture
def mock_article():
    return KBArticle(
        title="Resolving SSO Login Failures After Upgrade",
        html="<h2>Solution</h2><ol><li>Patch middleware.</li></ol>",
        category="IT",
        knowledge_base_id="kb_test",
    )


@pytest.fixture(autouse=True)
def mock_api_key(monkeypatch):
    """Beállítja a teszt API kulcsot minden tesztre."""
    monkeypatch.setenv("SNOW_WEBHOOK_API_KEY", "test-api-key-123")


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_ok(self, client, mock_settings):
        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert data["dry_run"] is True

    def test_health_degraded_on_error(self, client):
        with patch("snow_kb.server.load_settings", side_effect=Exception("fail")):
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"


# ---------------------------------------------------------------------------
# /generate-kb — hitelesítés
# ---------------------------------------------------------------------------

class TestAuthentication:
    def test_missing_api_key_rejected(self, client, mock_settings):
        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            resp = client.post("/generate-kb", json={"story_id": "STRY001"})
        assert resp.status_code == 401

    def test_wrong_api_key_rejected(self, client, mock_settings):
        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            resp = client.post(
                "/generate-kb",
                json={"story_id": "STRY001"},
                headers={"X-API-Key": "wrong-key"},
            )
        assert resp.status_code == 401

    def test_correct_api_key_accepted(self, client, mock_settings, mock_article):
        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            with patch("snow_kb.server.ServiceNowClient"):
                with patch("snow_kb.server.generate_kb_article", return_value=mock_article):
                    resp = client.post(
                        "/generate-kb",
                        json={"story_id": "STRY001"},
                        headers={"X-API-Key": "test-api-key-123"},
                    )
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# /generate-kb — flow
# ---------------------------------------------------------------------------

class TestGenerateKb:
    def test_successful_generation(self, client, mock_settings, mock_article):
        """Sikeres generálás — válasz tartalmazza a címet."""
        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            with patch("snow_kb.server.ServiceNowClient"):
                with patch("snow_kb.server.generate_kb_article", return_value=mock_article):
                    resp = client.post(
                        "/generate-kb",
                        json={"story_id": "STRY0012345"},
                        headers={"X-API-Key": "test-api-key-123"},
                    )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["story_id"] == "STRY0012345"
        assert "SSO" in data["title"]

    def test_kb_url_in_response(self, client, mock_settings, mock_article):
        """A válasz tartalmazza a KB URL-t (ha volt push)."""
        # Mock article sys_id-val
        article_with_sysid = MagicMock()
        article_with_sysid.title = "Test Title Here"
        article_with_sysid.sys_id = "kb_sys_123"

        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            with patch("snow_kb.server.ServiceNowClient"):
                with patch("snow_kb.server.generate_kb_article", return_value=article_with_sysid):
                    resp = client.post(
                        "/generate-kb",
                        json={"story_id": "STRY001"},
                        headers={"X-API-Key": "test-api-key-123"},
                    )
        data = resp.json()
        assert data["kb_sys_id"] == "kb_sys_123"
        assert "kb_view.do" in data["kb_url"]
        assert "dev300344" in data["kb_url"]

    def test_servicenow_error_returns_502(self, client, mock_settings):
        """ServiceNowError -> 502 Bad Gateway."""
        from snow_kb.servicenow_client import ServiceNowError

        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            with patch("snow_kb.server.ServiceNowClient"):
                with patch("snow_kb.server.generate_kb_article", side_effect=ServiceNowError("API down")):
                    resp = client.post(
                        "/generate-kb",
                        json={"story_id": "STRY001"},
                        headers={"X-API-Key": "test-api-key-123"},
                    )
        assert resp.status_code == 502

    def test_config_error_returns_500(self, client):
        """ConfigError -> 500."""
        with patch("snow_kb.server.load_settings", side_effect=ConfigError("Bad config")):
            resp = client.post(
                "/generate-kb",
                json={"story_id": "STRY001"},
                headers={"X-API-Key": "test-api-key-123"},
            )
        assert resp.status_code == 500

    def test_unexpected_error_returns_500(self, client, mock_settings):
        """Általános hiba -> 500."""
        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            with patch("snow_kb.server.ServiceNowClient"):
                with patch("snow_kb.server.generate_kb_article", side_effect=RuntimeError("Bumm")):
                    resp = client.post(
                        "/generate-kb",
                        json={"story_id": "STRY001"},
                        headers={"X-API-Key": "test-api-key-123"},
                    )
        assert resp.status_code == 500

    def test_push_false_generates_without_kb_url(self, client, mock_settings, mock_article):
        """Ha push=false, nincs sys_id és nincs kb_url."""
        with patch("snow_kb.server.load_settings", return_value=mock_settings):
            with patch("snow_kb.server.ServiceNowClient"):
                with patch("snow_kb.server.generate_kb_article", return_value=mock_article):
                    resp = client.post(
                        "/generate-kb",
                        json={"story_id": "STRY001", "push": False},
                        headers={"X-API-Key": "test-api-key-123"},
                    )
        data = resp.json()
        assert data["success"] is True
        assert data["kb_sys_id"] is None
        assert data["kb_url"] is None
