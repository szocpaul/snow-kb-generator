---
type: C4 Component
title: Calibrated audience decision (spec 013)
status: stable
groma:
  id: audience
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/audience.py
  technology: Python, typesafe-sdk (System One Choice), pinnelt jev modell
description: Typed, calibrated Choice call that decides the article audience instead of the generative ExtractChange field.
---

Produces the pipeline ExtractChange.audience value with a dedicated TypeSafe System One Choice call: it returns the selected option, per-option probabilities, and a confidence score. Fail-open by contract (FR-001): any timeout, 5xx, auth, or schema error returns None and the pipeline keeps the generative audience path. The decision model is pinned from config.yaml, every successful decision is logged as replay-compatible JSONL (jev-dspy-lab format), and confidence below the threshold falls back to the "developer" default with a work_notes flag.
