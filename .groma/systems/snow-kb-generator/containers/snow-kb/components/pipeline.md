---
type: C4 Component
title: Generation pipeline orchestrator
status: stable
groma:
  id: pipeline
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/pipeline.py
description: 'End-to-end orchestration: fetch Story, template, Update Set and related articles, run the DSPy program, apply guardrails, push to the KB.'
---

The glue between ServiceNow and DSPy. Assembles labeled story text (sanitizing HTML fields), enriches it with Update Set analysis and real related-article references, builds the LM (Kimi K3 by default, Pi-auth GLM, or local llama.cpp in dev mode) and runs the program under a thread-safe dspy.context. After generation it applies deterministic guardrails (code-tag normalization, direction-violating and N/A-only section stripping, hallucinated KB reference removal) and handles duplicate detection and force-update before pushing.
