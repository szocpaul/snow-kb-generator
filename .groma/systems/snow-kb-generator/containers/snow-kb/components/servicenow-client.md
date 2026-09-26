---
type: C4 Component
title: ServiceNow client
status: stable
groma:
  id: servicenow-client
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/servicenow_client.py
  technology: requests, ServiceNow Table API (Basic Auth)
description: 'All HTTP communication with ServiceNow: Story fetch, team template lookup, Update Set changes, KB search, KB create/update.'
---

Implements the pipeline client protocol. Reads Stories by number or sys_id, resolves the team template via the assignment group to template KB mapping, fetches Update Set payloads, finds duplicates by u_source_story, searches published KB articles with keyword re-ranking, and creates or patches articles, writing the KB link back into the Story work notes. In dry-run mode it serves mock stories from data/sample_stories and simulates creation.
