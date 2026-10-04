---
type: C4 Component
title: Labeled context sample builder (spec 016 T010)
status: stable
groma:
  id: context-labeled
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/context_labeled.py
  group: Context selection calibration (spec 016)
description: Builds the 56-piece labeled sample (relevant / noise / borderline context pieces) at data/examples/context_labeled_016.json from the selection captures; machine-assisted with manual labels, committed for the hide-threshold calibration.
---
