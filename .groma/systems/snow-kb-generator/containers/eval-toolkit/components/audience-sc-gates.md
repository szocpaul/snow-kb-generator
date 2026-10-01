---
type: C4 Component
title: Audience SC gates (spec 013 T012)
status: stable
groma:
  id: audience-sc-gates
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/audience_sc_gates.py
  group: Audience calibration
  technology: Python, pytest
description: Runs the spec 013 SC-001..SC-004 acceptance gates for the audience calibration and exits non-zero on any red gate.
---

SC-001: the new decision matches the gold labels at least as often as the generative baseline. SC-002: at the confirmatory 0.7 threshold, selective_risk <= 0.15, coverage >= 0.7, ECE <= 0.10. SC-003: fail-open pytest tests pass. SC-004: the report run twice is byte-identical (deterministic replay). Prerequisite: python -m eval.audience_measure capture has run.
