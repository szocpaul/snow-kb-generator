---
type: C4 Component
title: Context baseline measurement (spec 016 T002)
status: stable
groma:
  id: context-baseline
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/context_baseline.py
  group: Context selection calibration (spec 016)
description: 'Chunks the gold examples'' generation context (story sections, update set records) and records a per-piece token inventory with the real Qwen tokenizer (llama.cpp /tokenize) plus a rich_metric baseline with cache=False in dev mode. Output: artifacts/context_baseline*.json — the reference that the spec 016 impact measurement compares against; the after-measurement must use the same model and tokenizer.'
---
