# config.py — loading the configuration (DESIGN, not implemented)
# ===========================================================================
#
# Responsibility: gather all settings in a single place (secrets + structure),
# that the other modules import and use.
#
# Data sources:
#   1. .env                — titkok (SNOW_* , OPENAI_API_KEY, stb.)   python-dotenv
#   2. config.yaml         — structured settings (KB id, models, GEPA)   PyYAML
#
# Planned output: a Settings object (Pydantic BaseSettings or dataclass),
#   pl. `settings.snow.instance`, `settings.models.main`, `settings.gepa.auto`.
#
# Planned public functions:
#   load_settings(path="config.yaml") -> Settings
#       Loads the .env (if there is one), then the yaml, validates it, and returns it.
#
# Planned validations:
#   - SNOW_INSTANCE must not be "FILL_ME"
#   - the main model prefix must exist (openai/ | anthropic/ | azure/ | ollama/ ...)
#   - with --dry-run, the ServiceNow fields may be empty
#
# Security principle: secrets NEVER end up in the Settings __repr__.
#
# Note: during implementation, Pydantic BaseSettings + field_validator comes in handy.
