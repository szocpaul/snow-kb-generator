---
type: C4 Component
title: Context recall gate (spec 016 T008 / SC-003)
status: stable
groma:
  id: context-recall-gate
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/context_recall_gate.py
      symbol: main
  group: Context selection calibration (spec 016)
description: 'Exit-code gate: the selected (filtered) prompt must still contain the real component names referenced by the gold articles — 0/9 loss required. Same pattern as the extractor-refinement recall test.'
---
