# Implementation Plan: Evidence-First KB Generation

**Branch**: `007-direction-aware-quality` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.2.x, `skilled-proposer` (new pip dependency), pytest
- Affected files: `eval/metric.py`, `eval/gepa_optimize.py`, `src/snow_kb/signatures.py`, `data/examples/gold_dataset.md`, `tests/`, `pyproject.toml`

## Architecture

```
story_text ──► detect_direction() ──► inbound | outbound | both | unknown
      │
      ├──── rich_metric: direction violation + unsupported section ──► feedback ──┐
      │                                                                           ▼
      ├──── GenerateKbFromTemplate (evidence-first: menu, not mandate) ◄── GEPA (Kimi K3)
      │                                                                           ▲
      └──── SkilledProposer(extra_guidance: evidence-first + no invented refs) ───┘

Template (KBA1–KBA11): MENU — the article is built up from the supported sections.
```

## Key Decisions

1. **Omission, not N/A**: the unsupported section is left out entirely (no "N/A" placeholder). The gold dataset is adjusted accordingly (deleting the N/A-only blocks).
2. **Direction violation = special case with explicit feedback**: besides the general unsupported-section check, the direction error gets its own, clearly identifiable feedback string (the reflection model learns concrete patterns faster).
3. **The metric is the ground truth**: direction detection and the supportedness check live in the metric, the program can be freely reshaped by GEPA.
4. **Weights unchanged**: both checks score within the existing `template_adherence` axis.
5. **SkilledProposer fallback**: on import error, stock proposer + warning (the mock tests do not require the package).
6. **The guardrail is NOT extended** (out of scope).

## Phases

1. **Phase 1 (Metric)**: `detect_direction()` + direction violation + unsupported-section penalty + tests.
2. **Phase 2 (Signature + Dataset)**: evidence-first instruction; deleting the N/A-only blocks from the gold dataset; aligning the dataset tests.
3. **Phase 3 (Proposer)**: install `skilled-proposer` + switch `run_gepa_optimization()` + test.
4. **Phase 4 (Re-opt)**: baseline + GEPA + export + production validation + docs.
