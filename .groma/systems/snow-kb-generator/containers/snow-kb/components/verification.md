---
type: C4 Component
title: Component-name verification gate (spec 014)
status: stable
groma:
  id: verification
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/verification.py
  technology: Python, typesafe-sdk (Noul), ServiceNow Table API metadata
description: Validates the named ServiceNow components of a generated article against instance metadata before the article is pushed.
---

Runs after generation, before the ServiceNow write. Extracts component-name candidates with the 011 pattern (quoted names, CamelCase, dotted identifiers; shared general-term whitelist), then applies a deterministic core: the story Update Set whitelist first, and for remaining names a per-name spot-check against instance metadata (sys_db_object, sys_dictionary, sys_script, sys_script_include) with a JSON cache that makes replays byte-identical. Ambiguous "not_exists" names go to a calibrated TypeSafe Noul layer (pinned model) that judges whether the name refers to a real component. Fail-open (FR-002): any query or SDK error skips the layer with a warning and the pipeline continues; the gate behavior (flag/block) comes from config.verification_gate.
