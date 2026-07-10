"""test_cli.py — the tests of the cli.py command line interface.

The covered areas:
  - Parsing the arguments (help, missing story_id, options)
  - Dry-run flow: mock Story, generation, the output to stdout / a file
  - Error handling: ConfigError, ServiceNowError, general errors
  - The --json output format
  - Writing to a file with --output
  - --model override
  - Exit codes (0 = success, 1 = error)
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
    """Mock Settings that pass the validation of load_settings."""
    mock = MagicMock()
    mock.dry_run = False
    mock.models.main = "openai/gpt-4o"
    mock.snow.knowledge_base_id = "kb_test"
    mock.snow.default_category = "IT"
    return mock


# ---------------------------------------------------------------------------
# The argument parsing
# ---------------------------------------------------------------------------

class TestParser:
    """The tests of the argparse configuration."""

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
    """The flow tests of the main() function with mocked components."""

    def test_successful_generation_stdout(self, mock_article, mock_settings, capsys):
        """A successful generation — the article HTML to stdout."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article):
                    code = main(["STRY0012345", "--dry-run"])
        assert code == 0
        captured = capsys.readouterr()
        assert mock_article.html in captured.out

    def test_json_output_format(self, mock_article, mock_settings, capsys):
        """The --json format: the title, html, category fields."""
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
        """--output writes the article to a file."""
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
        # stdout does not contain the article
        captured = capsys.readouterr()
        assert "saved" in captured.err

    def test_dry_run_passed_to_load_settings(self, mock_article, mock_settings):
        """The --dry-run flag sets the dry_run parameter of load_settings."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings) as mock_load:
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article):
                    main(["STRY0012345", "--dry-run"])
        # We check that load_settings got dry_run=True
        _, kwargs = mock_load.call_args
        assert kwargs.get("dry_run") is True

    def test_no_push_passed_to_generate(self, mock_article, mock_settings):
        """The --no-push flag sets push=False."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article) as mock_gen:
                    main(["STRY0012345", "--no-push"])
        _, kwargs = mock_gen.call_args
        assert kwargs["push"] is False

    def test_model_override_applied(self, mock_article, mock_settings):
        """The --model override overwrites settings.models.main."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", return_value=mock_article):
                    main(["STRY0012345", "--dry-run", "--model", "openai/gpt-4o-mini"])
        assert mock_settings.models.main == "openai/gpt-4o-mini"


# ---------------------------------------------------------------------------
# The error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """The tests of the error handling of the CLI."""

    def test_config_error_returns_1(self, capsys):
        """ConfigError -> exit code 1, the error message to stderr."""
        with patch("snow_kb.cli.load_settings", side_effect=ConfigError("Rossz config")):
            code = main(["STRY0012345"])
        assert code == 1
        captured = capsys.readouterr()
        assert "Configuration error" in captured.err

    def test_servicenow_error_returns_1(self, mock_settings, capsys):
        """ServiceNowError -> exit code 1."""
        from snow_kb.servicenow_client import ServiceNowError
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", side_effect=ServiceNowError("API error")):
                    code = main(["STRY0012345"])
        assert code == 1
        captured = capsys.readouterr()
        assert "ServiceNow error" in captured.err

    def test_story_not_found_returns_1(self, mock_settings, capsys):
        """StoryNotFound (a subclass of ServiceNowError) -> exit code 1."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", side_effect=StoryNotFound("Not found")):
                    code = main(["STRY9999"])
        assert code == 1
        captured = capsys.readouterr()
        assert "ServiceNow error" in captured.err

    def test_unexpected_error_returns_1(self, mock_settings, capsys):
        """A general exception -> exit code 1."""
        with patch("snow_kb.cli.load_settings", return_value=mock_settings):
            with patch("snow_kb.cli.ServiceNowClient"):
                with patch("snow_kb.cli.generate_kb_article", side_effect=RuntimeError("Bumm")):
                    code = main(["STRY0012345"])
        assert code == 1
        captured = capsys.readouterr()
        assert "Unexpected error" in captured.err

    def test_sys_id_in_json_when_pushed(self, mock_settings, capsys):
        """If the article has a sys_id (a push happened), the JSON contains it."""
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
