---
type: C4 Component
title: Regression gate
status: stable
groma:
  id: compare
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/compare.py
  group: Runners
description: 'python -m eval.compare: exits non-zero unless the optimized run improves style by >= +0.05 with <= 0.02 regression on other axes.'
---

Reads two `runs/*.json` files (T010c format with axis averages), compares them axis by axis, and prints an OK/FAIL table. This is the SC-004 acceptance gate for GEPA runs.
