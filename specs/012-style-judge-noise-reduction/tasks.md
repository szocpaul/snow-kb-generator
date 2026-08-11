# Tasks: Style Judge Noise Reduction (multi-sample scoring)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Multi-sample Scoring (US1)

- [x] T001 [US1] `STYLE_JUDGE_SAMPLES = 3` constant into `eval/metric.py` (the tests can override it — FR-002)
- [x] T002 [US1] Rewrite of `_style_score()`: N judge calls, the score is the average of the successful samples; the critique comes from the sample closest to the mean (FR-003); clamping stays
- [x] T003 [US1] Partial fault tolerance: 1-2 failed calls → mean(remaining) + warning; all errors → (0.5, "") (FR-001)
- [x] T004 [US1] Tests (mock judge): (a) [0.4, 0.6, 0.8] → 0.6; (b) 2 errors + 1 success → the successful value + warning; (c) all errors → 0.5; (d) the critique comes from the sample closest to the mean; (e) the axes of rich_metric are still 5 axes

## Phase 2: Calibration Proof (US2)

- [x] T005 [US2] Judge discrimination revalidation (FR-005): machine test score < 0.4, STYLE-REF > 0.7
- [x] T006 [US2] Baseline 3× re-measurement (`python -m eval.baseline --model local --output runs/baseline{,_recheck,_recheck2}.json`, `cache=False` — FR-004) — preflight on llama.cpp before the runs
- [x] T007 [US2] Spread analysis: per-axis min–max table; **style spread ≤ 0.10** (SC-002) — if it is not met: evaluation of N=5 or temp=0, the decision documented; recording the new baseline reference

## Phase 3: Mini-GEPA Re-evaluation + Closing (US3)

- [x] T008 [US3] Numeric re-evaluation in tasks.md: measured spread vs the expected mini-GEPA gain ("improvement > measured spread + margin" threshold) — the decision is the human's
  - **FINAL DECISION (human, 2026-08-11): the mini-GEPA will be run LATER — it is not needed now, the current state of the pipeline is good. The earlier (noise-based) reason for the postponement is gone with spec 012: the run can be started any time when it is needed (~5-7 hours, as an overnight run, with the autonomous runner + infra-watcher setup, following the spec 010 pattern).**
- [x] T009 [US3] New Agent.md section + README if needed + commit, push


---

## T007 results (2026-08-11, N=3 multi-sample judge, cache=False, preflight OK)

Preflight: llama.cpp `/health` 200 + smoke generation 0.3 s — the server was alive before all three runs.

### Per-axis min–max table (axis averages of 3 identical baseline runs)

| axis | run1 | run2 | run3 | min | max | **spread** | old (1-sample) |
|---|---|---|---|---|---|---|---|
| structure | 0.875 | 0.917 | 0.917 | 0.875 | 0.917 | 0.042 | 0.042 |
| content | 0.667 | 0.699 | 0.660 | 0.660 | 0.699 | 0.039 | 0.070 |
| template | 0.750 | 0.750 | 0.750 | 0.750 | 0.750 | 0.000 | 0.000 |
| hallucination | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| **style** | 0.513 | 0.508 | 0.525 | 0.508 | 0.525 | **0.017** | **0.188** |
| overall | 0.751 | 0.768 | 0.762 | 0.751 | 0.768 | 0.018 | ~0.055 |

**SC-002 MET: style spread 0.188 → 0.017 (target: ≤ 0.10) — even better than the expected ~0.11** (averaging the axis per run reduces the variance further). The N=5 / temp=0 fallback options were NOT needed (not even the first option of plan Key Decision #2).

Methodological note: the per-EXAMPLE style standard deviation is still 0.20–0.27, but in this case the task-model generation variance (temp=0.6, the articles differ per run) and the judge noise are not separated — SC-002 is met with the original calibration, using the same method, for the standard deviation of the axis AVERAGES. Judge discrimination (T005/SC-003): machine test score 0.017 (< 0.4 ✅), STYLE-REF 0.950 (> 0.7 ✅) — `runs/t005_judge_revalidation.json`.

### New baseline reference (after spec 012, N=3 judge)

`runs/baseline.json` (2026-08-11T12:48): **average 0.751**; structure 0.875 / content 0.667 / template 0.750 / hallucination 1.000 / style 0.513. The numbers from the morning of 2026-08-11 (1-sample judge) are OBSOLETE; saved: `runs/baseline_pre_spec012.json`, `runs/baseline_recheck_pre_spec012.json`, `runs/baseline_recheck2_pre_spec012.json`. Spread analysis: `runs/t007_spread_analysis.json`.

## T008 — Numeric re-evaluation of the Mini-GEPA (the DECISION is the human's, GEPA was NOT run)

**Threshold (spec US3 acceptance 1):** the outcome of a mini-GEPA is interpretable only if **improvement > measured spread + margin**.

| quantity | value |
|---|---|
| Measured overall spread (3 runs, min–max) | **0.018** |
| Measured style axis spread | **0.017** |
| Margin (conservative, following the ±0.05 noise band of spec 010 T012, but adapted to the new noise level) | 0.02 |
| **Interpretability threshold (0.018 + 0.02)** | **≈ 0.04** |
| Expected mini-GEPA gain (spec 011 T009 estimate) | +0.02 – +0.05 |

**Reading:** the original reason for the postponement (noise 0.188 > gain 0.02–0.05) IS GONE — the noise is now 0.018. The upper end of the expected gain (+0.05) is already above the threshold (0.05 > 0.04), the lower end (+0.02) is still below it. At axis level the situation is stronger: a style-targeted improvement was of the order of +0.15–0.20 based on earlier GEPA experience (T012: style 0.45–0.46 → 0.60–0.65), which is a ~10× signal/noise ratio against the 0.017 style noise. **The outcome of a mini-GEPA is now interpretable if the measured improvement is ≥ ~0.04 (or is confirmed by a double measurement).**

**Open human decision:** running the mini-GEPA (estimated time: the cost of a metric call grew from 2 → 4 local calls — 1 gen + 3 judge —, the ~3.5 hours of the 200 call run of spec 010 is expected to become ~5-7 hours) OR further postponement (e.g. extending the valset first). The decision and its justification must be recorded: ⬜ DECISION: ______________ (human)
