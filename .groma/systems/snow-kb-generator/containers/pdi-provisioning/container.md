---
type: C4 Container
title: PDI provisioning script
status: stable
groma:
  id: pdi-provisioning
  parent: snow-kb-generator
  technology: Python, requests + ServiceNow Table API
description: One-off setup script that prepares a fresh ServiceNow developer instance (PDI) for the pipeline.
---

Run manually against a new instance: verifies credentials, writes the KB sys_id into config.yaml, creates the u_source_story and u_assignment_group fields, creates the team template KB and template article, installs the Create KB Article UI Action, and restores a test Story from a dump. Each step is idempotent and can run alone with --step N.
