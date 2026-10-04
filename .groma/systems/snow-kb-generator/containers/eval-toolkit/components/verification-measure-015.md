---
type: C4 Component
title: Asymmetric calibration measurement (spec 015 T007/T008)
status: stable
groma:
  id: verification-measure-015
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_measure_015.py
  group: Component verification calibration
description: 'Follows the spec 014 verification_measure pattern on the merged PDI-native sample: capture makes live TypeSafe Noul calls (pinned jev-1.13.0), report works from deterministic replay only (byte-identical reruns). Measures the asymmetric cost of threshold candidates.'
---
