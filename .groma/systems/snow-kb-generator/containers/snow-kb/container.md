---
type: C4 Container
title: snow_kb application
status: stable
groma:
  id: snow-kb
  parent: snow-kb-generator
  technology: Python 3.12, FastAPI + Uvicorn, DSPy 3.3
description: 'The deployable application: FastAPI webhook server (systemd on a VPS) and the snow-kb CLI, sharing one generation pipeline.'
---

Installed from src/snow_kb. In production it runs as a FastAPI server (uvicorn, systemd, port 8000) serving POST /generate-kb to the ServiceNow UI Action. The same package also runs as the snow-kb CLI for manual or dry-run generation. The pipeline component orchestrates fetch, generate, guardrail, and push; it is the only part that touches both ServiceNow and DSPy.
