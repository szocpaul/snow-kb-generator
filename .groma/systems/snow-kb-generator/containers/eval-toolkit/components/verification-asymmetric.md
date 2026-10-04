---
type: C4 Component
title: Asymmetric verification cost metric (spec 015)
status: stable
groma:
  id: verification-asymmetric
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/verification_asymmetric.py
  group: Component verification calibration
description: The spec 014 calibration metric was symmetric (both error kinds cost the same); in reality a false 'exists' (the gate letting a hallucinated name through) is much more expensive than a false alarm. This module implements the asymmetric cost used by the spec 015 calibration and gates (starting ratio 5:1, sensitivity analysis in the reports).
---
