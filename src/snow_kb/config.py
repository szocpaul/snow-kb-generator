"""config.py — központi beállítási réteg.

Egyetlen hely, ahonnan a többi modul minden konfigurációt lekérdez.
Két forrást egyesít egy típusos, validált Settings objektummá:

  1. .env              — titkok (SNOW_*, OPENAI_API_KEY*)     pydantic-settings
  2. config.yaml       — strukturált beállítások               PyYAML

Használat:
    from snow_kb.config import load_settings
    settings = load_settings()                 # alapértelmezett ./config.yaml
    settings = load_settings("path/to/c.yaml") # egyéni útvonal

Elvek:
  - A titkok SecretStr-ként vannak tárolva -> __repr__-ben ******** jelenik meg.
  - A load_settings() induláskor validál: hiányzó/üres értékek -> ConfigError.
  - A YAML és a .env függetlenek: hiányzó yaml alapértelmezett értékekkel indul.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigError(Exception):
    """Konfigurációs hiba (hiányzó/érvénytelen érték)."""


# ---------------------------------------------------------------------------
# 1. .env-ből jövő titkok (BaseSettings)
# ---------------------------------------------------------------------------

class Secrets(BaseSettings):
    """A .env fájlból (vagy környezeti változókból) töltött titkok.

    Egyetlen helyen van `model_config`: a .env automatikus betöltéséhez.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",        # ismeretlen változók nem okoznak hibát
    )

    # --- ServiceNow ---
    snow_instance: str = ""
    snow_username: str = ""
    snow_password: SecretStr = SecretStr("")

    # --- DSPy / LM ---
    openai_api_key: SecretStr = SecretStr("")
    openai_api_key_reflection: SecretStr = SecretStr("")


# ---------------------------------------------------------------------------
# 2. config.yaml-ból jövő strukturált beállítások (BaseModel)
# ---------------------------------------------------------------------------

class ServiceNowConfig(BaseModel):
    knowledge_base_id: str = "FILL_ME"
    default_category: str = "General"
    story_table: str = "story"   # instance-onként "story" vagy "rm_story"


class PipelineConfig(BaseModel):
    default_temperature: float = 0.0
    max_tokens: int = 2000


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
# 3. Egyesített Settings
# ---------------------------------------------------------------------------

class Settings(BaseModel):
    """A teljes konfiguráció, amit a pipeline moduljai használnak.

    A `secrets` rész tartalma nem jelenik meg a __repr__-ben értelemszerűen
    (SecretStr miatt). A struktúrák (snow, models, gepa) láthatóak.
    """

    dry_run: bool = False          # CLI/teszt override
    story_fields: list[str] = Field(
        default_factory=lambda: [
            "short_description",
            "description",
            "acceptance_criteria",
            "work_notes",
            "comments",
            "state",
            "assigned_to",
        ]
    )

    snow: ServiceNowConfig = Field(default_factory=ServiceNowConfig)
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    gepa: GepaConfig = Field(default_factory=GepaConfig)

    # titkok külön ágon
    snow_instance: str = ""
    snow_username: str = ""
    snow_password: SecretStr = SecretStr("")
    openai_api_key: SecretStr = SecretStr("")
    openai_api_key_reflection: SecretStr = SecretStr("")

    # --- model prefix validáció ---
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
                    f"models.{field_name}='{model}' érvénytelen. "
                    f"Engedélyezett prefixek: {', '.join(valid_prefixes)}"
                )
        return v


# ---------------------------------------------------------------------------
# 4. Betöltő függvény
# ---------------------------------------------------------------------------

def load_settings(
    config_path: str | Path = "config.yaml",
    *,
    dry_run: bool = False,
) -> Settings:
    """Betölti a .env-t és a config.yaml-t, majd validálja.

    Args:
        config_path: a config.yaml útvonala (alapértelmezett: ./config.yaml).
        dry_run: ha True, a ServiceNow/LM titkok lehetnek üresek
            (mock adatokkal való fejlesztéshez / teszteléshez).

    Returns:
        Egy validált Settings objektum.

    Raises:
        ConfigError: ha a config.yaml olvashatatlan, vagy a validáció
            megállapodási ponton (pl. FILL_ME) akad.
    """
    config_path = Path(config_path)

    # --- YAML betöltése (ha létezik) ---
    yaml_data: dict = {}
    if config_path.exists():
        try:
            yaml_data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            raise ConfigError(f"Nem olvasható a {config_path}: {exc}") from exc

    # --- .env betöltése ---
    secrets = Secrets()  # automatikusan a .env-ből

    # --- Egyesítés (Pydantic ValidationError -> ConfigError) ---
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
        raise ConfigError(f"Konfigurációs validációs hiba: {exc}") from exc

    # --- Induláskori konzisztencia-ellenőrzés ---
    _validate_at_load(settings)

    return settings


def _validate_at_load(settings: Settings) -> None:
    """Olyan ellenőrzések, amik csak a teljes Settings ismeretében működnek.

    A dry_run=True engedi, hogy a ServiceNow-mezők üresek/"FILL_ME" legyenek
    (így LM kulcs nélkül is lehet fejleszteni, mock adatokkal).
    """
    if not settings.dry_run:
        # ServiceNow kapcsolat nélkülözhetetlen
        if not settings.snow_instance or settings.snow_instance == "FILL_ME":
            raise ConfigError(
                "snow_instance hiányzik vagy 'FILL_ME'. "
                "Állítsd be a .env-ben, vagy használj --dry-run-t."
            )
        if not settings.snow_username:
            raise ConfigError(
                "snow_username hiányzik a .env-ből (vagy --dry-run)."
            )
        if not settings.snow_password.get_secret_value():
            raise ConfigError(
                "snow_password hiányzik a .env-ből (vagy --dry-run)."
            )

    # Knowledge base id kötelező (dry_run-ban is, hacsak nem csak generálunk)
    if settings.snow.knowledge_base_id == "FILL_ME":
        raise ConfigError(
            "config.yaml: servicenow.knowledge_base_id még 'FILL_ME'. "
            "Állítsd be a cél KB sys_id-ját."
        )

    # LM kulcs kötelező, ha nem dry_run
    if not settings.dry_run and not settings.openai_api_key.get_secret_value():
        raise ConfigError(
            "openai_api_key hiányzik a .env-ből (vagy --dry-run)."
        )
