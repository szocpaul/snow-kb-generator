---
type: C4 Component
title: GEPA optimization runner
status: stable
groma:
  id: gepa-optimize
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/gepa_optimize.py
  group: Runners
description: 'python -m eval.gepa_optimize: runs the GEPA compile with a Kimi K3 reflection model and saves artifacts/program.json.'
---

Builds dspy.GEPA with the rich metric, an anti-overfitting SkilledProposer seeded with evidence-first and style guidance, and a token-refreshing Kimi LM (`_RefreshingKimiLM` refreshes the OAuth token from the Pi auth.json before every call, including a direct refresh request under systemd). Also measures the baseline if missing, scores the optimized program, and saves it for the server to load at startup.
