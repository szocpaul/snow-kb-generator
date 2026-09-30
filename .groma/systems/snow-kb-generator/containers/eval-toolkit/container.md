---
type: C4 Container
title: Evaluation and GEPA optimization toolkit
status: stable
groma:
  id: eval-toolkit
  parent: snow-kb-generator
  technology: Python, DSPy 3.3 (Evaluate, GEPA)
description: Offline commands that measure article quality on a gold dataset and optimize the DSPy program with GEPA.
---

Run with python -m eval.baseline / eval.compare / eval.gepa_optimize. The dataset loader builds train/val examples from data/examples/gold_dataset.md, the rich metric scores generated articles on five axes (structure, content, template, hallucination, style) with feedback for GEPA reflection, and the runners measure baselines, gate regressions, and save optimized programs to artifacts/program.json, which the server loads at startup.
