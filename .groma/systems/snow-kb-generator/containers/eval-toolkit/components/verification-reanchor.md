---
type: C4 Component
title: Verification ReAnchor calibration (spec 014 T013)
status: stable
groma:
  id: verification-reanchor
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_reanchor.py
  group: Component verification calibration
  technology: Python, DSPy experimental (Choice, ReAnchor, TypeSafe)
description: Tunes the verification decision threshold with DSPy ReAnchor on an eval-only mirror of the verification calibrated layer.
---

The wrapper mirrors the verification.py calibrated-layer SDK call (same three options yes/external/no, same question and criteria, pinned jev-1.13.0) but is not the production decision path — production stays a direct SDK call in src/snow_kb/verification.py. ReAnchor calibrates without further LLM calls from the cached probabilities. Output: artifacts/verification_reanchor_report.json. Needs TYPESAFE_API_KEY.
