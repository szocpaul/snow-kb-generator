---
type: C4 Component
title: Verification SC gates (spec 014 T013)
status: stable
groma:
  id: verification-sc-gates
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_sc_gates.py
  group: Component verification calibration
  technology: Python, pytest
description: Runs the spec 014 SC-001..SC-004 acceptance gates for component-name verification and exits non-zero on any red gate.
---

SC-001: zero false "does not exist" flags on the gold articles. SC-002: at the confirmatory 0.7 threshold on the labeled sample (at least 20 cases), selective_risk <= 0.15 and coverage >= 0.7. SC-003: fail-open pytest tests pass. SC-004: the report run twice is byte-identical (deterministic replay). Prerequisite: verification_measure capture + report have run.
