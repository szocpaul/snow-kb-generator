---
type: C4 Component
title: Asymmetric cost baseline (spec 015 T004)
status: stable
groma:
  id: verification-baseline-015
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_baseline_015.py
      symbol: main
  group: Component verification calibration
description: 'Computes the asymmetric cost of the THEN-CURRENT threshold (0.7) on the existing 24-example labeled sample from the spec 014 replay report rows — no new live calls (deterministic, SC-005 hygiene). Baseline-first: the spec 015 calibration compares against this number.'
---
