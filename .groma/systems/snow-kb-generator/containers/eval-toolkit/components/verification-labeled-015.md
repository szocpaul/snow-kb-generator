---
type: C4 Component
title: Merged labeled sample builder (spec 015 T005)
status: stable
groma:
  id: verification-labeled-015
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_labeled_015.py
  group: Component verification calibration
description: Derives labeled calibration examples mechanically from the dumped (and T003 human-gate-approved) name set of the PDI-native fixture, merged with the spec 014 sample into data/examples/verification_labeled_015.json.
---
