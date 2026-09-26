---
type: C4 System
title: snow-kb-generator
status: stable
groma:
  id: snow-kb-generator
description: 'Automates Knowledge Base article writing: a completed ServiceNow Story becomes a structured, reviewed-quality KB article without manual work.'
---

The system is triggered from a ServiceNow UI Action (or run from the CLI), fetches the Story, its Update Set XML payloads, the team template, and related KB articles, generates an article with a DSPy program, applies deterministic guardrails (hallucinated references, N/A-only and direction-violating sections, code tags), and creates or updates the KB article via the Table API. An offline toolkit measures quality on a gold dataset and optimizes the program instructions with GEPA.
