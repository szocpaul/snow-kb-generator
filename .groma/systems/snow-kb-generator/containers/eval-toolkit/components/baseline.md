---
type: C4 Component
title: Baseline measurement runner
status: stable
groma:
  id: baseline
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/baseline.py
  group: Runners
description: 'python -m eval.baseline: measures the current program on the valset and writes runs/baseline.json.'
---

Runs dspy.Evaluate with the rich metric, extracts per-example scores, feedback and axes into a serializable JSON (including axis averages for the compare gate), and supports a --model kimi|local switch with a module-safe configure_lm override. Also re-used by the GEPA runner to score the optimized program.
