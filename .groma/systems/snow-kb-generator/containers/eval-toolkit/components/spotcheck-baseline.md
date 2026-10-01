---
type: C4 Component
title: Instance spot-check baseline (spec 014 T004)
status: stable
groma:
  id: spotcheck-baseline
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/spotcheck_baseline.py
  group: Component verification calibration
  technology: Python, ServiceNow Table API
description: Checks the inventory candidates against Update Set content and live instance metadata to quantify the hallucinated-name problem.
---

Reads artifacts/component_inventory.json and verifies each candidate: first against the Update Set payloads of its gold example (primary whitelist), then via per-name spot-checks in the live instance metadata tables (sys_db_object, sys_script, sys_script_include, sys_dictionary) over the ServiceNowClient session. Output: artifacts/component_baseline_report.json + .md with the count of names that do not exist today.
