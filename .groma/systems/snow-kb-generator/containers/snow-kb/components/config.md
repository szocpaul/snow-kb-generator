---
type: C4 Component
title: Configuration loader
status: stable
groma:
  id: config
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/config.py
  technology: pydantic-settings + PyYAML
description: Single validated Settings object merging .env secrets and config.yaml structure, with load-time checks.
---

load_settings() reads .env (secrets as SecretStr) and config.yaml (ServiceNow, pipeline, models, GEPA sections), applies the SNOW_KB_DEV_MODE override, and validates at load: ServiceNow credentials, knowledge_base_id, model prefixes, and LM key requirements unless dry-run.
