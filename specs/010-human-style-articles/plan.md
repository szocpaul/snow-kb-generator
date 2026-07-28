# Implementation Plan: Human-Written Style for Generated KB Articles

**Branch**: `010-human-style-articles` | **Date**: 2026-07-28 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.2.x, Kimi K3 (task + judge LM, `_RefreshingKimiLM`)
- Affected files: `src/snow_kb/signatures.py` (US1), `eval/metric.py` (US2), `eval/gepa_optimize.py` (US3), `tests/`

## Architecture

```
                        (US1) signature docstring + style block
                                    │
generated article ──► rich_metric ───┼── structure / content / template / hallucination
                    │               └── (US2) style_judge() [Kimi K3, LLM-as-judge]
                    │                     score 0-1 + specific critique
                    ▼
              GEPA reflection sees the feedback
                    │
                    ▼
         (US3) SkilledProposer(additional_instructions = style guidance)
                    │  generalizable style rules into the prompts
                    ▼
         (US4) small-budget GEPA (≤300 calls) → proof of style axis improvement
```

## Key Decisions

1. **The judge is a `dspy.Signature` in metric.py** (`StyleJudge`: article_html + style_reference → score + critique), with a Kimi K3 LM. Not a separate module — the metric is its home.
2. **Error tolerance:** judge exception → score=0.5 + warning log; the metric never stops.
3. **Weights:** 0.25 structure + 0.25 content + 0.15 template + 0.15 hallucination + 0.20 style. The thresholds of the existing tests must be aligned.
4. **The style reference is baked into the judge prompt**: a representative excerpt of the STYLE-REF gold article (not the full HTML — token saving).
5. **The boilerplate ban list is a shared constant** (`BANNED_PHRASES`): the signature block, the judge prompt and the SC-001 regex check use the same list.
6. **US3 only replaces the text of `additional_instructions`** on the existing SkilledProposer instance — the fallback logic and the prompt_model stay unchanged.
7. **No docstring consolidation** (separate spec, backlog).

## Phases

1. **Phase 1 (US1)**: signature style block + `BANNED_PHRASES` constant + tests.
2. **Phase 2 (US2)**: `StyleJudge` signature + `style_score()` in the metric + fault tolerance + tests (with a mock judge).
3. **Phase 3 (US3)**: SkilledProposer style guidance + test.
4. **Phase 4 (US4)**: GEPA run (≤300 calls, Kimi task+reflection) → proof of style axis improvement + live validation + docs.
