# config.py — konfiguráció betöltése (TERV, nincs implementálva)
# ===========================================================================
#
# Felelősség: egyetlen helyen összefogni minden beállítást (titkok + struktúra),
# amit a többi modul importál és használ.
#
# Adatforrások:
#   1. .env                — titkok (SNOW_* , OPENAI_API_KEY, stb.)   python-dotenv
#   2. config.yaml         — strukturált beállítások (KB id, modellek, GEPA)   PyYAML
#
# Tervezett kimenet: egy Settings objektum (Pydantic BaseSettings vagy dataclass),
#   pl. `settings.snow.instance`, `settings.models.main`, `settings.gepa.auto`.
#
# Tervezett publikus függvények:
#   load_settings(path="config.yaml") -> Settings
#       Betölti a .env-t (ha van), majd a yaml-t, validálja, és visszaadja.
#
# Tervezett validációk:
#   - SNOW_INSTANCE nem lehet "FILL_ME"
#   - main model prefix létezzen (openai/ | anthropic/ | azure/ | ollama/ ...)
#   - ha --dry-run, akkor a ServiceNow mezők lehetnek üresek
#
# Biztonsági elv: titkok SOHA nem kerülnek bele a Settings __repr__-jébe.
#
# Megjegyzés: implementációkor Pydantic BaseSettings + field_validator jól jön.
