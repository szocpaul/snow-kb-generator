---
type: C4 Component
title: Verification calibration measurement (spec 014 T013)
status: stable
groma:
  id: verification-measure
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_measure.py
  group: Component verification calibration
  technology: Python, typesafe-sdk, JSONL replay
description: Captures live refers-to-real-component decisions with a pinned model and reports calibration metrics from deterministic replay only.
---

Follows the spec 013 audience_measure pattern: capture makes live TypeSafe Noul calls with the pinned jev-1.13.0 model over the labeled sample (data/examples/verification_labeled.json, at least 20 examples) and caches spot-check results; report works exclusively from a fail-closed ReplayClient plus the cache-only SpotChecker, so two report runs are byte-identical (SC-004). The confirmatory gate is the pre-declared 0.7 threshold; the sweep is exploratory.
