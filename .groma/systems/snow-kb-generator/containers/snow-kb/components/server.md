---
type: C4 Component
title: Webhook server
status: stable
groma:
  id: server
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/server.py
  technology: FastAPI + Uvicorn
  group: Entry points
description: 'HTTP layer for the ServiceNow UI Action: GET /health and POST /generate-kb, API-key checked.'
---

Stateless FastAPI wrapper around the pipeline: it verifies the X-API-Key header, loads the GEPA-optimized program from artifacts/program.json at startup (falling back to the base program), and maps pipeline errors to HTTP codes (409 duplicate, 422 missing assignment group, 502 ServiceNow error). Runs under systemd on a VPS; contains no business logic itself.
