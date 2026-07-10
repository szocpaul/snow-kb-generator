"""test_cli.py — a cli.py parancssori felület tesztek.

Le fedett területek:
  - Argumentumok parse-olása (help, hiányzó story_id, opciók)
  - Dry-run flow: mock Story, generálás, kimenet stdout-ra / fájlba
  - Hibakezelés: ConfigError, ServiceNowError, általános hibák
  - --json kimenet formátum
  - --output fájlba írás
  - --model override
  - Exit code-ok (0 = sikeres, 1 = hiba)
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from snow_kb.cli import build_parser, main
from snow_kb.config import ConfigError
from snow_kb.schemas import KBArticle
from snow_kb.servicenow_client import StoryNotFound


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_article() -> KBArticle:
    return KBArticle(
        title="Resolving SSO Login Failures After Upgrade",
        html="<h2>Solution</h2><ol><li>Patch auth middleware.</li></ol>",
        category="IT",
        knowledge_base_id="kb_test",
    )


@pytest.fixture
def mock_settings():
    """Mock Settings, ami átment a load_settings validáción."""
    mock = MagicMock()
    mock.dry_run = False
    mock.models.main = "openai/gpt-4o"
    mock.snow.knowledge_base_id = "kb_test"
    mock.snow.default_category = "IT"
    return mock


# ---------------------------------------------------------------------------
# Argumentum parse-olás
# ---------------------------------------------------------------------------

class TestParser:
    """Az argparse konfiguráció tesztjei."""

    def test_help_exits_clean(self):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--help"])
        assert exc_info.value.code == 0

    def test_story_id_required(self, capsys):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args([])
        assert exc_info.value.code == 2

    def test_dry_run_flag(self):
        parser = build_parser()
        args = parser.parse_args(["STRY0012345", "--dry-run"])
        assert args.dry_run is True
        assert args.story_id == "STRY0012345"

    def test_no_push_flag(self):
        parser = build_parser()
        args = parser.parse_args(["STRY0012345", "--no-push"])
        assert args.no_push is True

    def test_generate_only_alias(self):
        parser = build_parser()
        args = parser.parse_args(["STRY0012345", "--generate-only"])
        assert args.no_push is True

    def test_config_path(self):
        parser = build_parser()
        args = parser.parse_args(["STRY0012345", "--config", "/custom/config.yaml"])
        assert args.config == "/custom/config.yaml"

    def test_model_override(self):
        parser = build_parser()
        args = parser.parse_args(["STRY0012345", "--model", "openai/gpt-4o-mini"])
        assert args.model == "openai/gpt-4o-mini"

    def test_output_path(self):
        parser = build_parser()
        args = parser.parse_args(["STRY0012345", "--output", "article.html"])
        assert args.output == "article.html"

    def test_json_flag(self):
        parser = build_parser()
        args = parser.parse_args(["STRY0012345", "--json"])
        assert args.json is True


# ---------------------------------------------------------------------------
# Main flow (mockolt pipeline)
# ---------------------------------------------------------------------------

class TestMainFlow:
    """A main() függvény flow tesztjei mockolt komponensekkel."""

    def test_successful_generation_stdout(self, mock_article, mock_settings, capsys):
        """Sikeres generálás — cikk HTML stdout-ra."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article):
                    code = main(["STRY0012345", "--dry-run"])
        assert code == 0
        captured = capsys.readouterr()
        assert mock_article.html in captured.out

    def test_json_output_format(self, mock_article, mock_settings, capsys):
        """--json formátum: title, html, category mezők."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article):
                    code = main(["STRY0012345", "--dry-run", "--json"])
        assert code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["title"] == "Resolving SSO Login Failures After Upgrade"
        assert data["html"] == mock_article.html
        assert data["category"] == "IT"

    def test_output_to_file(self, mock_article, mock_settings, tmp_path, capsys):
        """--output fájlba írja a cikket."""
        output_path = tmp_path / "article.html"
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article):
                    code = main([
                        "STRY0012345", "--dry-run",
                        "--output", str(output_path),
                    ])
        assert code == 0
        assert output_path.exists()
        content = output_path.read_text(encoding="utf-8")
        assert mock_article.html in content
        # stdout nem tartalmazza a cikket
        captured = capsys.readouterr()
        assert "elmentve" in captured.err

    def test_dry_run_passed_to_load_settings(self, mock_article, mock_settings):
        """A --dry-run flag beállítja a load_settings dry_run paraméterét."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings) as mock_load:
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article):
                    main(["STRY0012345", "--dry-run"])
        # Ellenőrizzük, hogy a load_settings dry_run=True-t kapott
        _, kwargs = mock_load.call_args
        assert kwargs.get("dry_run") is True

    def test_no_push_passed_to_generate(self, mock_article, mock_settings):
        """A --no-push flag push=False-t állít be."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article) as mock_gen:
                    main(["STRY0012345", "--no-push"])
        _, kwargs = mock_gen.call_args
        assert kwargs["push"] is False

    def test_model_override_applied(self, mock_article, mock_settings):
        """A --model override felülírja a settings.models.main-t."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article):
                    main(["STRY0012345", "--dry-run", "--model", "openai/gpt-4o-mini"])
        assert mock_settings.models.main == "openai/gpt-4o-mini"


# ---------------------------------------------------------------------------
# Hibakezelés
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """A CLI hibakezelésének tesztjei."""

    def test_config_error_returns_1(self, capsys):
        """ConfigError -> exit code 1, hibaüzenet stderr-re."""
        with patch("snow_kb.cli.load_settings", side_effect=ConfigError("Rossz config")):
            code = main(["STRY0012345"])
        assert code == 1
        captured = capsys.readouterr()
        assert "Konfigurációs hiba" in captured.err

    def test_servicenow_error_returns_1(self, mock_settings, capsys):
        """ServiceNowError -> exit code 1."""
        from snow_kb.servicenow_client import ServiceNowError
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", side_effect=ServiceNowError("API hiba")):
                    code = main(["STRY0012345"])
        assert code == 1
        captured = capsys.readouterr()
        assert "ServiceNow hiba" in captured.err

    def test_story_not_found_returns_1(self, mock_settings, capsys):
        """StoryNotFound (ServiceNowError alosztály) -> exit code 1."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", side_effect=StoryNotFound("Nincs")):
                    code = main(["STRY9999"])
        assert code == 1
        captured = capsys.readouterr()
        assert "ServiceNow hiba" in captured.err

    def test_unexpected_error_returns_1(self, mock_settings, capsys):
        """Általános kivétel -> exit code 1."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", side_effect=RuntimeError("Bumm")):
                    code = main(["STRY0012345"])
        assert code == 1
        captured = capsys.readouterr()
        assert "Váratlan hiba" in captured.err

    def test_sys_id_in_json_when_pushed(self, mock_settings, capsys):
        """Ha a cikknek van sys_id-ja (push történt), a JSON tartalmazza."""
        article_with_sysid = MagicMock()
        article_with_sysid.title = "Test Title Here"
        article_with_sysid.html = "<p>ok</p>"
        article_with_sysid.category = "IT"
        article_with_sysid.knowledge_base_id = "kb1"
        article_with_sysid.sys_id = "new_sys_123"
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=article_with_sysid):
                    main(["STRY0012345", "--json"])
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["sys_id"] == "new_sys_123"
