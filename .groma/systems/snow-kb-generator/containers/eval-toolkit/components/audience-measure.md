---
type: C4 Component
title: Audience calibration measurement (spec 013 T012)
status: stable
groma:
  id: audience-measure
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/audience_measure.py
  group: Audience calibration
  technology: Python, typesafe-sdk, JSONL replay
description: Captures live audience decisions with a pinned model and reports calibration metrics from deterministic replay only.
---

Two commands: capture makes live TypeSafe System One calls with the pinned jev-1.13.0 model over the 9 gold + 3 mock cases into artifacts/audience_measurement.jsonl (needs TYPESAFE_API_KEY); report computes metrics exclusively from a deterministic replay of the recording, so two report runs are byte-identical (SC-002/SC-004). The confirmatory gate is the pre-declared 0.7 threshold; the sweep is exploratory. Needs a completed audience baseline for SC-001.
