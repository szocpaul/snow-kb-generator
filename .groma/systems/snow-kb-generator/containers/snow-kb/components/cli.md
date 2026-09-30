---
type: C4 Component
title: snow-kb CLI
status: stable
groma:
  id: cli
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/cli.py
    - scanner: python
      file: src/snow_kb/__main__.py
  technology: Python argparse
  group: Entry points
description: 'Command-line entry point: snow-kb STRY... with dry-run, no-push, model override, and dev-mode flags.'
---

Thin wrapper over pipeline.generate_kb_article; it parses arguments, loads settings, applies --dev / --model overrides, and prints the article as HTML or JSON. `src/snow_kb/__main__.py` only forwards to this `main()`, enabling `python -m snow_kb`.
