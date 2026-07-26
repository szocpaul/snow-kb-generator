# Implementation Plan: Direction-Aware KB Quality

**Branch**: `007-direction-aware-quality` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.2.x, `skilled-proposer` (new pip dependency), pytest
- Affected files: `eval/metric.py`, `eval/gepa_optimize.py`, `src/snow_kb/signatures.py`, `tests/`, `pyproject.toml`

## Architecture

```
story_text ──► detect_direction() ──► inbound | outbound | both | unknown
                         │
        ┌────────────────┼─────────────────────┐
        ▼                ▼                     ▼
  rich_metric      SkilledProposer       GenerateKbFromTemplate
  (direction       (extra_guidance:      (signature: explicit
   violation        direction rule +      direction rule)
   feedback)        no invented KB refs)
        │                │
        └──── GEPA ◄─────┘
              (Kimi K3 reflection sees the sign)
```

## Key Decisions

1. **Where to detect direction**: in the metric, with simple keyword counting (story_text). Not in the program — the metric is the source of truth, the program can be freely reshaped by GEPA.
2. **Weights unchanged**: the direction violation scores within the existing `template_adherence` axis (0.5 or 0 instead of 0), it does not get a new axis — we avoid the reweighting of spec 004.
3. **SkilledProposer fallback**: if the package cannot be imported, `run_gepa_optimization()` falls back to the stock proposer with a warning (so the CI/mock tests do not require the package).
4. **Guardrail is NOT extended** (out of scope): first we check whether the metric+GEPA path is enough.

## Phases

1. **Phase 1 (Metric)**: `detect_direction()` + direction violation in template_adherence + feedback + tests.
2. **Phase 2 (Signature)**: explicit direction rule in the `GenerateKbFromTemplate` docstring.
3. **Phase 3 (Proposer)**: install `skilled-proposer`, switch `run_gepa_optimization()` + config (`extra_guidance`) + test.
4. **Phase 4 (Re-opt)**: baseline + GEPA + export + production validation + docs.
