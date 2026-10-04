---
type: C4 Component
title: Context selection impact measurement (spec 016 T007)
status: stable
groma:
  id: context-measure
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/context_measure.py
  group: Context selection calibration (spec 016)
description: 'Runs the gold examples with context selection enabled against the recorded baseline: per-example and aggregate token delta plus rich_metric delta into artifacts/context_selection_report.json (quality must not regress beyond the noise band, SC-002). Replay mode is byte-identical (SC-005).'
---
