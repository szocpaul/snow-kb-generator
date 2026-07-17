"""config.py — the central configuration layer.

A single place from where every other module queries all of its configuration.
It merges two sources into one typed, validated Settings object:

  1. .env              — titkok (SNOW_*, OPENAI_API_KEY*)     pydantic-settings
  2. config.yaml       — structured settings                   PyYAML

Usage:
    from snow_kb.config import load_settings
    settings = load_settings()                 # default ./config.yaml
    settings = load_settings("path/to/c.yaml") # custom path

Elvek:
  - The secrets are stored as SecretStr -> they show up as ******** in __repr__.
  - load_settings() validates at startup: missing/empty values -> ConfigError.
  - The YAML and the .env are independent: a missing YAML starts with default values.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(Exception):
    """Configuration error (missing/invalid value)."""


# ---------------------------------------------------------------------------
# 1. Secrets coming from the .env (BaseSettings)
# ---------------------------------------------------------------------------

class Secrets(BaseSettings):
    """The secrets loaded from the .env file (or from environment variables).

    `model_config` is in a single place: for the automatic loading of the .env.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",        # unknown variables do not cause an error
    )

    # --- ServiceNow ---
    snow_instance: str = ""
    snow_username: str = ""
    snow_password: SecretStr = SecretStr("")

    # --- DSPy / LM ---
    openai_api_key: SecretStr = SecretStr("")
    openai_api_key_reflection: SecretStr = SecretStr("")


# ---------------------------------------------------------------------------
# 2. Structured settings coming from config.yaml (BaseModel)
# ---------------------------------------------------------------------------

class ServiceNowConfig(BaseModel):
    knowledge_base_id: str = "FILL_ME"
    default_category: str = "General"
    story_table: str = "story"   # "story" or "rm_story" depending on the instance


class PipelineConfig(BaseModel):
    default_temperature: float = 0.0
    max_tokens: int = 2000
    use_pi_auth: bool = False  # If True, uses the Pi Agent auth.json (GLM/Kimi)
    api_base: str = ""         # Optional API endpoint (e.g. a GLM proxy)


class ModelsConfig(BaseModel):
    main: str = "openai/gpt-4o"
    reflection: str = "openai/gpt-5"
    reflection_temperature: float = 1.0
    reflection_max_tokens: int = 32000


class GepaConfig(BaseModel):
    auto: Literal["light", "medium", "heavy"] = "medium"
    candidate_selection: Literal["pareto", "random", "best"] = "pareto"
    num_threads: int = 8
    seed: int = 0


# ---------------------------------------------------------------------------
# 3. Merged Settings
# ---------------------------------------------------------------------------

class Settings(BaseModel):
    """The full configuration that the pipeline modules use.

    The content of the `secrets` part does not show up in __repr__ (because of
    SecretStr). The structures (snow, models, gepa) are visible.
    """

    dry_run: bool = False          # CLI/test override
    story_fields: list[str] = Field(
        default_factory=lambda: [
            "short_description",
            "description",
            "acceptance_criteria",
            "u_technical_specification",
            "work_notes",
            "comments",
            "state",
            "assigned_to", "assignment_group"
        ]
    )

    snow: ServiceNowConfig = Field(default_factory=ServiceNowConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    gepa: GepaConfig = Field(default_factory=GepaConfig)

    # secrets on a separate branch
    snow_instance: str = ""
    snow_username: str = ""
    snow_password: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    openai_api_key_reflection: SecretStr = SecretStr("")

    # --- model prefix validation ---
    @field_validator("models")
    @classmethod
    def _validate_model_prefix(cls, v: ModelsConfig) -> ModelsConfig:
        valid_prefixes = (
            "openai/", "anthropic/", "azure/", "vertex_ai/",
            "bedrock/", "ollama/", "ollama_chat/",
        )
        for field_name in ("main", "reflection"):
            model = getattr(v, field_name)
            if not model.startswith(valid_prefixes):
                raise ValueError(
                    f"models.{field_name}='{model}' is invalid. "
                    f"Allowed prefixes: {', '.join(valid_prefixes)}"
                )
        return v


# ---------------------------------------------------------------------------
# 4. Loader function
# ---------------------------------------------------------------------------

def load_settings(
    config_path: str | Path = "config.yaml",
    *,
    dry_run: bool = False,
) -> Settings:
    """Loads the .env and the config.yaml, then validates them.

    Args:
        config_path: the path of config.yaml (default: ./config.yaml).
        dry_run: if True, the ServiceNow/LM secrets may be empty
            (for development/testing with mock data).

    Returns:
        A validated Settings object.

    Raises:
        ConfigError: if the config.yaml is unreadable, or the validation
            stops at a placeholder (e.g. FILL_ME).
    """
    config_path = Path(config_path)

    # --- Load the YAML (if it exists) ---
    yaml_data: dict = {}
    if config_path.exists():
        try:
            yaml_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Cannot read {config_path}: {exc}") from exc

    # --- Load the .env ---
    secrets = Secrets()  # automatically from the .env

    # --- Merge (Pydantic ValidationError -> ConfigError) ---
    try:
        settings = Settings(
            dry_run=dry_run,
            story_fields=yaml_data.get("story_fields", Settings().story_fields),
            snow=ServiceNowConfig(**(yaml_data.get("servicenow") or {})),
            pipeline=PipelineConfig(**(yaml_data.get("pipeline") or {})),
            models=ModelsConfig(**(yaml_data.get("models") or {})),
            gepa=GepaConfig(**(yaml_data.get("gepa") or {})),
            snow_instance=secrets.snow_instance,
            snow_username=secrets.snow_username,
            snow_password=secrets.snow_password,
            openai_api_key=secrets.openai_api_key,
            openai_api_key_reflection=secrets.openai_api_key_reflection,
        )
    except Exception as exc:  # ValidationError
        raise ConfigError(f"Configuration validation error: {exc}") from exc

    # --- Startup consistency checks ---
    _validate_at_load(settings)

    return settings


def _validate_at_load(settings: Settings) -> None:
    """Checks that only work with the complete Settings known.

    dry_run=True allows the ServiceNow fields to be empty/"FILL_ME"
    (so that development with mock data is possible without an LM key).
    """
    if not settings.dry_run:
        # The ServiceNow connection is mandatory
        if not settings.snow_instance or settings.snow_instance == "FILL_ME":
            raise ConfigError(
                "snow_instance is missing or 'FILL_ME'. "
                "Set it in the .env, or use --dry-run."
            )
        if not settings.snow_username:
            raise ConfigError(
                "snow_username is missing from the .env (or --dry-run)."
            )
        if not settings.snow_password.get_secret_value():
            raise ConfigError(
                "snow_password is missing from the .env (or --dry-run)."
            )

    # The knowledge base id is mandatory (also in dry_run, unless we only generate)
    if settings.snow.knowledge_base_id == "FILL_ME":
        raise ConfigError(
            "config.yaml: servicenow.knowledge_base_id is still 'FILL_ME'. "
            "Set the target KB sys_id."
        )

    # The LM key is mandatory if it is not dry_run AND not Pi Auth AND there is
    # no local api_base (local llama.cpp/Ollama endpoints need no API key)
    if (
        not settings.dry_run
        and not settings.pipeline.use_pi_auth
        and not settings.pipeline.api_base
        and not settings.openai_api_key.get_secret_value()
    ):
        raise ConfigError(
            "openai_api_key is missing from the .env (or --dry-run, or pipeline.use_pi_auth=true, or pipeline.api_base is given as a local endpoint)."
        )
