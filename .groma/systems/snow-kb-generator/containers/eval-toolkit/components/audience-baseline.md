---
type: C4 Component
title: Audience baseline recorder (spec 013 T003)
status: stable
groma:
  id: audience-baseline
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/audience_baseline.py
      symbol: main
  group: Audience calibration
  technology: Python, DSPy
description: Records the current generative audience decisions on the 9 gold examples with unmodified production code.
---

Runs the production StoryToKBArticle extract step (ChainOfThought(ExtractChange) with the analyze_changes preamble) on the gold dataset; the base program stands in for production behavior. Output: artifacts/audience_baseline.json with per-example number, audience, and story hash — the reference that the SC-001 gate compares the calibrated path against. Run with SNOW_KB_DEV_MODE=1 python -m eval.audience_baseline.
