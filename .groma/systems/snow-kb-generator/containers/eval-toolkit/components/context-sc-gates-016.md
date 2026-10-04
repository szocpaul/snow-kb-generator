---
type: C4 Component
title: Context selection SC gates (spec 016 T013)
status: stable
groma:
  id: context-sc-gates-016
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/context_sc_gates_016.py
  group: Context selection calibration (spec 016)
description: 'Exit-code gates for SC-001..SC-006: token target (documented RED, accepted at the T012 human gate), quality non-regression, recall, fail-open, byte-identical replay, and the threshold-stays decision with unchanged config. Prerequisite: context_measure and context_calibration_016 have run.'
---
