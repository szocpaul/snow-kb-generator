---
type: C4 System
title: ServiceNow instance
status: stable
groma:
  id: servicenow-instance
  technology: ServiceNow Table API (REST, Basic Auth)
---

The ServiceNow instance that holds the Stories, the Knowledge Base, the Update Sets, and the team template articles. The pipeline reads Story fields, team templates, Update Set XML payloads, and related KB articles from it, and creates or updates KB articles in it. Also hosts the UI Action script that triggers generation. Current production instance: dev432044 (2026-09-20, the predecessor dev437812 was retired).
