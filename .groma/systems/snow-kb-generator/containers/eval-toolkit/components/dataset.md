---
type: C4 Component
title: Gold dataset loader
status: stable
groma:
  id: dataset
  parent: eval-toolkit
  code:
    - scanner: python
      file: eval/dataset.py
description: Parses data/examples/gold_dataset.md into train/val dspy.Example splits with the team template attached.
---

Each gold example provides story_text, template_context (the Integration Team HTML template), optional Update Set payloads, and the expected article HTML. Enforces a minimum of 5 examples and keeps at least 2 in the validation split.
