---
type: C4 Component
title: Component-name candidate inventory (spec 014 T003)
status: stable
groma:
  id: component-inventory
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/component_inventory.py
  group: Component verification calibration
  technology: Python, regex
description: Baseline inventory of component-name candidates extracted from the gold articles with the unchanged 011 pattern.
---

Replicates the eval/metric.py _find_hallucinated_components regexes without modification (spec requirement: unchanged code) to extract candidates — quoted names, CamelCase, dotted identifiers — from the gold articles and optionally a few freshly generated articles (--generate N, dev mode). Writes the raw candidate list with type hints and whitelist flags to artifacts/component_inventory.json; story-side checking is left to the 011 metric, this list feeds the instance-side spot-check (T004).
