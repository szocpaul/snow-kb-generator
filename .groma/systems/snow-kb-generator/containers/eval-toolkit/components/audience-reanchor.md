---
type: C4 Component
title: Audience ReAnchor calibration (spec 013 T012)
status: stable
groma:
  id: audience-reanchor
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/audience_reanchor.py
  group: Audience calibration
  technology: Python, DSPy experimental (Choice, ReAnchor, TypeSafe)
description: Tunes the audience decision threshold with DSPy ReAnchor on an eval-only mirror of the production SDK call.
---

The wrapper mirrors the production TypeSafe call (same three options, same question and criteria, pinned jev-1.13.0) but is not the production decision path — production stays a direct SDK call in src/snow_kb/audience.py. ReAnchor calibrates without further LLM calls: the first run caches TypeSafe probabilities and threshold/weight candidates work from the cache. Output: artifacts/audience_reanchor_report.json. Needs TYPESAFE_API_KEY.
