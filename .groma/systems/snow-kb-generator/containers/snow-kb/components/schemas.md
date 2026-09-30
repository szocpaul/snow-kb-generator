---
type: C4 Component
title: Data contracts
status: stable
groma:
  id: schemas
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/schemas.py
    - scanner: python
      file: src/snow_kb/errors.py
      symbol: MissingAssignmentGroupError
  technology: Pydantic v2
description: 'Shared typed contracts: StoryData, ArticleSections, KBArticle, plus the domain exceptions.'
---

Owns src/snow_kb/schemas.py and src/snow_kb/errors.py. StoryData tolerates partial ServiceNow payloads, KBArticle validates title length and block-level HTML, and ArticleSections is the typed intermediate between extraction and generation. The MissingAssignmentGroupError exception lives here because both the pipeline and the server map it.
