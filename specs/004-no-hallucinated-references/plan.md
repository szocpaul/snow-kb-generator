# Implementation Plan: Hallucination-Free KB Article Generation

**Branch**: `004-no-hallucinated-references` | **Date**: 2026-07-26 | **Spec**: [spec.md](spec.md)

## Technical Context

- **Language**: Python 3.12, DSPy 3.2.x, pytest
- **Affected modules**: `data/examples/gold_dataset.md`, `eval/metric.py`, `src/snow_kb/pipeline.py` (guardrail), `tests/`
- **No new dependencies** — regex-based detection using the stdlib.

## Architecture

```
Story text (source of truth)
      │
      ▼
StoryToKBArticle (GEPA-optimized) ──► generated HTML
      │                                   │
      │                          guardrail: strip_hallucinated_references()
      │                                   │  (KB\d{6,} patterns compared against story_text)
      │                                   ▼
      │                           clean HTML ──► ServiceNow push
      ▼
rich_metric: + hallucination axis (GEPA feedback)
```

## Key Decisions

1. **Placeholder format**: `KBXXXXXXX` — unmistakably not a real number, so the regex detector handles it separately.
2. **Detection pattern**: `\bKB\d{6,}\b` — ServiceNow KB numbers have 7 digits; ≥6 digits is the accepted threshold.
3. **Guardrail strategy**: strip (removal) + warning log, NOT an error — the article can still be pushed, without the hallucination.
4. **Metric weights**: the new hallucination axis joins the existing axes (0.3 structure + 0.3 content + 0.2 template + 0.2 hallucination).

## Phases

1. **Phase 1 (Data)**: gold_dataset.md sanitization + dataset test expansion.
2. **Phase 2 (Metric)**: hallucination axis in the rich_metric + tests.
3. **Phase 3 (Guardrail)**: `strip_hallucinated_references()` in the pipeline + tests.
4. **Phase 4 (Re-optimization)**: baseline + GEPA re-run, export, production validation (STRY0010010).
