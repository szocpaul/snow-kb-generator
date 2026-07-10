"""test_config.py — the tests of the config.py module.

The covered areas:
  - the default / valid case of load_settings()
  - FILL_ME guard (knowledge_base_id)
  - missing secrets outside dry_run -> ConfigError
  - dry_run=True allows the empty secrets
  - the SecretStr does not leak into the __repr__
  - an invalid model prefix -> ConfigError
  - loading the story_fields (it contains u_technical_specification)
  - a YAML read error -> ConfigError
"""

from __future__ import annotations

import pytest

from snow_kb.config import (
    ConfigError,
    GepaConfig,
    Settings,
    ServiceNowConfig,
    load_settings,
)


class TestLoadSettingsValid:
    """The happy-path tests of load_settings()."""

    def test_valid_full_config(self, valid_yaml, set_env):
        s = load_settings(valid_yaml)
        assert s.snow.knowledge_base_id == "kb_test_123"
        assert s.snow.default_category == "Self-Service"
        assert s.snow.story_table == "story"
        assert s.models.main == "openai/gpt-4o"
        assert s.models.reflection == "openai/gpt-5"
        assert s.gepa.auto == "light"
        assert s.gepa.num_threads == 4

    def test_story_fields_include_technical_spec(self, valid_yaml, set_env):
        s = load_settings(valid_yaml)
        assert "u_technical_specification" in s.story_fields

    def test_secrets_loaded_from_env(self, valid_yaml, set_env):
        s = load_settings(valid_yaml)
        assert s.snow_instance == "demo.service-now.com"
        assert s.snow_username == "api-user"
        assert s.snow_password.get_secret_value() == "secret-pw"
        assert s.openai_api_key.get_secret_value() == "sk-test-key"

    def test_dry_run_flag_propagated(self, valid_yaml, clean_env):
        s = load_settings(valid_yaml, dry_run=True)
        assert s.dry_run is True


class TestFillMeGuard:
    """A knowledge_base_id == 'FILL_ME' always raises an error."""

    def test_fill_me_rejected_in_normal_mode(self, make_yaml, set_env):
        path = make_yaml({"servicenow": {"knowledge_base_id": "FILL_ME"}})
        with pytest.raises(ConfigError, match="FILL_ME"):
            load_settings(path)

    def test_fill_me_rejected_in_dry_run_too(self, make_yaml, clean_env):
        path = make_yaml({"servicenow": {"knowledge_base_id": "FILL_ME"}})
        with pytest.raises(ConfigError, match="FILL_ME"):
            load_settings(path, dry_run=True)


class TestMissingSecrets:
    """The secrets are mandatory outside dry_run."""

    def test_missing_snow_instance_rejected(self, make_yaml, clean_env):
        path = make_yaml({"servicenow": {"knowledge_base_id": "kb1"}})
        with pytest.raises(ConfigError, match="snow_instance"):
            load_settings(path)

    def test_missing_snow_username_rejected(self, make_yaml, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SNOW_INSTANCE", "x.service-now.com")
        # the username/password is missing
        path = make_yaml({"servicenow": {"knowledge_base_id": "kb1"}})
        with pytest.raises(ConfigError, match="snow_username"):
            load_settings(path)

    def test_missing_openai_key_rejected(self, make_yaml, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("SNOW_INSTANCE", "x.service-now.com")
        monkeypatch.setenv("SNOW_USERNAME", "u")
        monkeypatch.setenv("SNOW_PASSWORD", "p")
        path = make_yaml({"servicenow": {"knowledge_base_id": "kb1"}})
        with pytest.raises(ConfigError, match="openai_api_key"):
            load_settings(path)

    def test_dry_run_allows_empty_secrets(self, make_yaml, clean_env):
        path = make_yaml({"servicenow": {"knowledge_base_id": "kb1"}})
        s = load_settings(path, dry_run=True)
        assert s.snow_instance == ""
        assert s.openai_api_key.get_secret_value() == ""

    def test_pi_auth_allows_missing_openai_key(self, make_yaml, monkeypatch):
        """If use_pi_auth=True, it does not require an OPENAI_API_KEY."""
        monkeypatch.setenv("SNOW_INSTANCE", "x.service-now.com")
        monkeypatch.setenv("SNOW_USERNAME", "u")
        monkeypatch.setenv("SNOW_PASSWORD", "p")
        path = make_yaml({
            "servicenow": {"knowledge_base_id": "kb1"},
            "pipeline": {"use_pi_auth": True},
        })
        s = load_settings(path)  # it does not raise a ConfigError for a missing API key
        assert s.pipeline.use_pi_auth is True


class TestSecretStrProtection:
    """The secrets do not leak into the Settings __repr__."""

    def test_password_not_in_repr(self, valid_yaml, set_env):
        s = load_settings(valid_yaml)
        rep = repr(s)
        assert "secret-pw" not in rep
        assert "**********" in rep or "SecretStr" in rep

    def test_api_key_not_in_repr(self, valid_yaml, set_env):
        s = load_settings(valid_yaml)
        rep = repr(s)
        assert "sk-test-key" not in rep


class TestModelPrefixValidation:
    """An invalid model prefix -> ConfigError."""

    @pytest.mark.parametrize("bad_model", [
        "gpt-4o",              # without a prefix
        "claude-3-opus",       # without a prefix
        "foobar/baz",          # an unknown prefix
    ])
    def test_bad_prefix_rejected(self, make_yaml, set_env, bad_model):
        path = make_yaml({
            "servicenow": {"knowledge_base_id": "kb1"},
            "models": {"main": bad_model},
        })
        with pytest.raises(ConfigError, match="is invalid"):
            load_settings(path)

    @pytest.mark.parametrize("good_model", [
        "openai/gpt-4o",
        "anthropic/claude-3-opus",
        "azure/gpt-4o",
        "ollama/llama3.1:8b",
        "ollama_chat/llama3.1:8b",
    ])
    def test_good_prefix_accepted(self, make_yaml, set_env, good_model):
        path = make_yaml({
            "servicenow": {"knowledge_base_id": "kb1"},
            "models": {"main": good_model},
        })
        s = load_settings(path)
        assert s.models.main == good_model


class TestYamlErrors:
    """Handling the YAML read errors."""

    def test_malformed_yaml_rejected(self, tmp_path, set_env):
        path = tmp_path / "bad.yaml"
        path.write_text(
            "servicenow:\n"
            "  knowledge_base_id: [unterminated\n"
            "  - this is broken\n",
            encoding="utf-8",
        )
        with pytest.raises(ConfigError, match="Cannot read"):
            load_settings(path)

    def test_missing_yaml_uses_defaults(self, tmp_path, set_env):
        """If the yaml does not exist, it starts with the default values —
        but the knowledge_base_id is FILL_ME by default, which is forbidden.
        """
        path = tmp_path / "nonexistent.yaml"
        with pytest.raises(ConfigError):
            load_settings(path)


class TestDefaultsAndSubmodels:
    """The default values of the Pydantic sub-models."""

    def test_settings_defaults(self):
        s = Settings(dry_run=True, snow=ServiceNowConfig(knowledge_base_id="kb1"))
        assert s.gepa.auto == "medium"
        assert s.gepa.candidate_selection == "pareto"
        assert s.gepa.seed == 0
        assert "short_description" in s.story_fields
        assert "u_technical_specification" in s.story_fields

    def test_gepa_auto_literal_validation(self, make_yaml, set_env):
        """An invalid gepa.auto value is also a ConfigError."""
        path = make_yaml({
            "servicenow": {"knowledge_base_id": "kb1"},
            "gepa": {"auto": "turbo"},   # it does not exist
        })
        with pytest.raises(ConfigError):
            load_settings(path)
