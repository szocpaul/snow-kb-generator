"""conftest.py — the shared fixtures for the tests.

The helpers that several test files use go here:
  - generating a temporary YAML file
  - setting/cleaning the environment variables
  - modifying sys.path so that src/snow_kb can be imported
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import yaml

# The src/ folder is on the Python import path (so that `import snow_kb` works)
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Fixture-k
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_env(monkeypatch):
    """Deletes all ServiceNow / OpenAI environment variables.

    Useful when a test starts with a clean slate (e.g. dry_run tests).
    """
    for key in (
        "SNOW_INSTANCE", "SNOW_USERNAME", "SNOW_PASSWORD",
        "OPENAI_API_KEY", "OPENAI_API_KEY_REFLECTION",
        "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    yield


@pytest.fixture
def set_env(monkeypatch):
    """Sets the minimally required environment variables (not dry_run)."""
    monkeypatch.setenv("SNOW_INSTANCE", "demo.service-now.com")
    monkeypatch.setenv("SNOW_USERNAME", "api-user")
    monkeypatch.setenv("SNOW_PASSWORD", "secret-pw")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    yield


@pytest.fixture
def make_yaml(tmp_path):
    """Factory: writes a YAML file with the given content and returns the path.

    Usage:
        path = make_yaml({"servicenow": {"knowledge_base_id": "kb1"}, ...})
    """
    def _make(data: dict, name: str = "config.yaml") -> Path:
        p = tmp_path / name
        p.write_text(yaml.safe_dump(data), encoding="utf-8")
        return p
    return _make


@pytest.fixture
def valid_yaml(make_yaml):
    """A complete, valid config.yaml — every mandatory field is filled in."""
    return make_yaml({
        "servicenow": {
            "knowledge_base_id": "kb_test_123",
            "default_category": "Self-Service",
            "story_table": "story",
        },
        "models": {
            "main": "openai/gpt-4o",
            "reflection": "openai/gpt-5",
        },
        "gepa": {
            "auto": "light",
            "num_threads": 4,
        },
        "story_fields": [
            "short_description", "description", "acceptance_criteria",
            "u_technical_specification", "work_notes", "comments",
            "state", "assigned_to",
        ],
    })
