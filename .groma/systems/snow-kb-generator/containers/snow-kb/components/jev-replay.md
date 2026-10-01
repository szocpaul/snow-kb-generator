---
type: C4 Component
title: Vendored record/replay helper (jev-dspy-lab)
status: stable
groma:
  id: jev-replay
  parent: snow-kb
  code:
    - scanner: python
      file: src/snow_kb/vendor/jev_replay.py
  technology: Python, JSONL, SHA-256
description: Record/replay JSONL helper vendored from jev-dspy-lab, adapted to the typesafe-sdk 0.7.x system_one call shape.
---

Source: github.com/jmanhype/jev-dspy-lab (MIT), src/jev_dspy_lab/replay.py. Provides the canonical, key-order-independent SHA-256 request hash and the {request_hash, source, model, response} JSONL line format used by the audience and verification decision logs. The ReplayClient serves fail-closed deterministic replays from recordings, which the SC-004 byte-identical report gates rely on.
