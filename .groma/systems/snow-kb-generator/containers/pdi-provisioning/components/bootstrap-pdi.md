---
type: C4 Component
title: PDI bootstrap
status: stable
groma:
  id: bootstrap-pdi
  parent: pdi-provisioning
  code:
    - scanner: python
      file: scripts_pdi/bootstrap_pdi.py
description: Six idempotent steps that make a fresh ServiceNow PDI ready for the pipeline (fields, template KB, UI Action, test Story).
---

Reads credentials from .env directly, talks to the Table API, updates config.yaml with the chosen knowledge base sys_id, and warns when the UI Action script API key differs from SNOW_WEBHOOK_API_KEY. Supports --step N and --dry-run for safe re-runs.
