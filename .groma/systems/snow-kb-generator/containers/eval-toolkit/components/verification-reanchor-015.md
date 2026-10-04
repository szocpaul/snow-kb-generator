---
type: C4 Component
title: Asymmetric ReAnchor calibration (spec 015 T007)
status: stable
groma:
  id: verification-reanchor-015
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_reanchor_015.py
  group: Component verification calibration
description: Eval-only wrapper mirroring the production verification.py calibrated-layer SDK call (same three options, same question and criteria, pinned jev-1.13.0); ReAnchor calibrates from cached probabilities with the asymmetric metric, without further LLM calls. Production stays a direct SDK call.
---
