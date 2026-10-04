---
type: C4 Component
title: Hide-threshold calibration (spec 016 T011)
status: stable
groma:
  id: context-calibration-016
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/context_calibration_016.py
  group: Context selection calibration (spec 016)
description: 'ReAnchor calibration (eval-only wrapper) plus threshold sweep with asymmetric cost (starting ratio 5:1) and sensitivity analysis on the labeled sample; includes the ceiling analysis of achievable token savings (raw / cost-constrained / with state-fix). Output: artifacts/context_calibration_report_016.json + context_reanchor_report_016.json. The sweep is exploratory; the safety floor (fail-open=show) is not calibratable.'
---
