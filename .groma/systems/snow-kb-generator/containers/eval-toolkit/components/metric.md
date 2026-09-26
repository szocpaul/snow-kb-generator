---
type: C4 Component
title: Rich 5-axis evaluation metric
status: stable
groma:
  id: metric
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/metric.py
description: GEPA-contract metric scoring structure, content, template, hallucination, and style, with natural-language feedback.
---

rich_metric compares a generated article with its gold counterpart: heading coverage, fact-identifier overlap (style-neutral), evidence-first template checks (direction violations, unsupported and N/A-only sections), hallucinated KB numbers and fabricated component names, plus an LLM-as-judge style score against a hand-written reference article. The weighted score and the feedback text drive GEPA reflection; per-axis values are persisted for the compare gate.
