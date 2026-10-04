---
type: C4 Component
title: Context selection for generation (spec 016, INACTIVE)
status: stable
groma:
  id: context-selection
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/context_selection.py
description: Classifies each generation context piece (story section, update set record, related article) as hide/summarize/show via a pinned typesafe Score decision with confidence; a plain-Python threshold policy executes the verdict, fail-open is always show, and the story body can never be hidden. Every decision is recorded as replay-compatible JSONL. Measured on the gold set and stopped at the T012 human gate (safe-noise ceiling ~1% of the full prompt vs the 5% target), so it ships disabled (context_selection.enabled=false) with the full measurement trail in artifacts/.
---
