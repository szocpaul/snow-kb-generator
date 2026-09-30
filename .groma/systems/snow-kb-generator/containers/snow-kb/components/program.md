---
type: C4 Component
title: StoryToKBArticle DSPy program
status: stable
groma:
  id: program
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/program.py
    - scanner: python
      file: src/snow_kb/signatures.py
  technology: DSPy 3.3 (Signatures, ChainOfThought, Predict)
description: 'The generative core: named DSPy predictors that turn story text plus a team template into a KB article.'
---

Owns src/snow_kb/program.py and src/snow_kb/signatures.py, which are one responsibility: the LLM program that GEPA optimizes. Three named predictors — AnalyzeChanges (Update Set XML to technical summary), ExtractChange (story text to change summary, key steps, audience), and GenerateKbFromTemplate (evidence-first fill of the team HTML template). The signature docstrings carry the instructions, including the writing-style and anti-hallucination rules; the module requires a template (spec 009).
