---
type: C4 Component
title: Verification SC gates (spec 015 T012)
status: stable
groma:
  id: verification-sc-gates-015
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_sc_gates_015.py
  group: Component verification calibration
description: 'Exit-code gates for SC-001..SC-005: fixture integrity (every update-set name exists, live PDI spot-check), asymmetric calibration result, no quality regression, fail-open tests, and byte-identical replay. The config threshold changes only after human approval (T009 gate).'
---
