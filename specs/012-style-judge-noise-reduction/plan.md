# Implementation Plan: Style Judge Noise Reduction (multi-sample scoring)

**Branch**: `012-style-judge-noise-reduction` | **Date**: 2026-08-11 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.3.0; **interpreter: `../.venv`**
- The style judge: local Qwen3.6-35B-A3B (llama.cpp, `-np 4`), the same model as the task (a deliberate compromise — unchanged)
- Affected file: primarily `eval/metric.py` (`_style_score`, the `StyleJudge` area) + `tests/test_style_axis.py` / `tests/test_eval_metric.py`
- Measurement side: `eval/baseline.py` runs (cache=False), NO code change in the pipeline
- Measured starting point (2026-08-11): style spread 0.188 (3 identical runs, Agent.md 32)

## Architecture

```
BEFORE:                          AFTER (US1):
_style_score(html)               _style_score(html)
      │                                ├── judge(html, ref) → s1
      ▼                                ├── judge(html, ref) → s2   (N=3)
 judge ×1 → score                       ├── judge(html, ref) → s3
 (±0.19 noise)                            │
                                         ▼
                                    score = mean(successful samples)
                                    critique = the sample closest to the average
                                    partial error: mean(remaining) + warning
                                    all errors: (0.5, "") — FR-002 untouched
                                         │
                                         ▼
                                    (goal: ±0.10 noise — US2 calibration)
```

## Key Decisions

1. **Average (mean), not median**: the score is continuous on a 0-1 scale; the mean preserves the expected value. (If significant outliers appear during the calibration, the median is the fallback option — to be recorded in tasks.md.)
2. **N=3 as the default**: σ/√3 ≈ 0.58× → ~0.11 expected from 0.188, which is already close to the target; N=5 (→0.08) only if the calibration justifies it (time cost!).
3. **The judge temperature stays unchanged (0.6)**: the samples should be genuinely independent; a rigid temp=0 judge is a fallback option, not the base.
4. **The critique comes from the sample closest to the mean**: the GEPA reflection needs one concrete, representative text — not all of them, and not the prettiest.
5. **Partial fault tolerance**: in case of 1-2 failed calls the average of the remaining samples (NOT 0.5) — otherwise fault tolerance would itself be a noise source; in the all-error case the spec 010 FR-002 behaviour stays untouched.
6. **The time cost is deliberate**: baseline 10 min → ~15-25 min with N=3; in GEPA estimates the cost of a metric call grows from 2 local calls to 4 (1 gen + 3 judge) — future run planning accounts for this.
7. **The metric change obsoletes the baseline again** (spec 010/011 pattern): the US2 calibration provides the new reference.

## Phases

1. **Phase 1 (US1)**: `STYLE_JUDGE_SAMPLES` constant + multi-sample `_style_score` + partial fault tolerance + critique selection + mock tests.
2. **Phase 2 (US2)**: re-validation of the judge discrimination + baseline 3× + spread analysis + (if needed: evaluation of N=5/temp=0) + new reference.
3. **Phase 3 (US3)**: numeric re-evaluation of mini-GEPA + human decision + docs.
