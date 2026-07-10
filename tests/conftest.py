"""conftest.py — közös fixture-k a tesztekhez.

Ide kerülnek azok a helper-ek, amiket több tesztfájl is használ:
  - tmp YAML fájl generálása
  - környezeti változók beállítása/takarítása
  - sys.path módosítása, hogy a src/snow_kb importálható legyen
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import yaml

# A src/ mappa a Python import útvonalon (hogy `import snow_kb` működjön)
SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


# ---------------------------------------------------------------------------
# Fixture-k
# ---------------------------------------------------------------------------

@pytest.fixture
def clean_env(monkeypatch, tmp_path):
    """Tiszta környezet: törli a ServiceNow / OpenAI változókat ÉS egy
    olyan mappába lép, ahol nincs .env fájl.
    Erre azért van szükség, mert a pydantic-settings automatikusan beolvassa
    a cwd .env fájlját, ami a projektben már tartalmazza a valós adatokat.
    """
    for key in (
        "SNOW_INSTANCE", "SNOW_USERNAME", "SNOW_PASSWORD",
        "OPENAI_API_KEY", "OPENAI_API_KEY_REFLECTION",
        "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.chdir(tmp_path)
    yield


@pytest.fixture
def set_env(monkeypatch, tmp_path):
    """Beállítja a minimálisan szükséges környezeti változókat (nem dry_run).
    tmp_path-be lépünk, hogy a projekt .env fájlja ne szóljon közbe.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SNOW_INSTANCE", "demo.service-now.com")
    monkeypatch.setenv("SNOW_USERNAME", "api-user")
    monkeypatch.setenv("SNOW_PASSWORD", "secret-pw")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    yield


@pytest.fixture
def make_yaml(tmp_path):
    """Factory: ír egy YAML fájlt az adott tartalommal, visszaadja az útvonalat.

    Használat:
        path = make_yaml({"servicenow": {"knowledge_base_id": "kb1"}, ...})
    """
    def _make(data: dict, name: str = "config.yaml") -> Path:
        p = tmp_path / name
        p.write_text(yaml.safe_dump(data), encoding="utf-8")
        return p
    return _make


@pytest.fixture
def valid_yaml(make_yaml):
    """Egy teljes, érvényes config.yaml — minden kötelező mező kitöltve."""
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
