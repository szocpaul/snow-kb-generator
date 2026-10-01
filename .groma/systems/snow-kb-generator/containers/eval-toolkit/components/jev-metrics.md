---
type: C4 Component
title: Vendored calibration metrics (jev-dspy-lab)
status: stable
groma:
  id: jev-metrics
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/jev_metrics.py
  technology: Python
description: 'Calibration gate metrics copied unmodified from jev-dspy-lab: selective risk, coverage, ECE, Brier.'
---

Source: github.com/jmanhype/jev-dspy-lab (MIT), src/jev_dspy_lab/metrics.py. These are the SC-002 gate metrics for the spec 013 (audience) and spec 014 (component verification) calibrations; the sc_gates runners read them from the calibration reports.
