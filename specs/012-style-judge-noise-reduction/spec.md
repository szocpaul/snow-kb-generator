# Feature Specification: Style Judge Noise Reduction (multi-sample scoring)

**Feature Branch**: `012-style-judge-noise-reduction`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "The calibration (2026-08-11) showed: the style axis spreads 0.188 across three IDENTICAL baseline runs — the single-sample, temperature=0.6 LLM call of the style judge is the biggest measurement noise source in the pipeline. This is why the mini-GEPA was postponed (spec 011 T009): the expected gain (+0.02-0.05) is smaller than the noise. The judge is a local model (free), so multi-sample averaging is a cheap solution."

## Background (diagnosis)

- **The measurement (Agent.md 32):** axis spreads over 3 identical baseline runs: hallucination 0.000, template 0.000, structure 0.042, content 0.070, **style 0.188**. The spread of the style axis is ~3-4× larger than that of the other axes.
- **The source of the noise:** `_style_score()` (eval/metric.py) issues a SINGLE `dspy.Predict(StyleJudge)` call, with the global `temperature=0.6` LM config. The same article gets a different score from run to run.
- **The judge itself is good** (spec 010 SC-002 validation): the machine test score is 0.00, the hand-written STYLE-REF is 1.00 — the *average* is in a good place, the *standard deviation* is the problem. Not a judge swap is needed, but variance reduction.
- **Physics:** the spread of the average of n independent samples ≈ σ/√n → 3 samples: ±0.19 → ~±0.11; 5 samples: ~±0.08.
- **Cost side:** the judge is local (marginal cost zero), but the measurement time grows: metric call = 1 generation + N judge calls. The baseline measurement (~10 min) takes ~15-25 min with N=3. This modifies the estimate of a future GEPA run.
- **Why not temperature=0?** A single temp=0 call can make the judge rigid (hidden bias), and we do not know its clamping behaviour either. The primary path of the spec is averaging over samples; temp=0 is a fallback option in the calibration phase.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-sample Style Scoring (Priority: P1)

The `_style_score()` takes N samples from the judge (default `STYLE_JUDGE_SAMPLES = 3`), and returns the **average** of the scores. Partial fault tolerance: if 1-2 calls fail, it computes from the remaining samples; if all fail, the spec 010 FR-002 behaviour remains (neutral 0.5 + warning).

**Why this priority**: This is the core of the noise reduction; everything else builds on it.

**Independent Test**: mock judge with a fixed series ([0.4, 0.6, 0.8] → 0.6); partial error (2 errors + 1 success → the successful value); total error → 0.5.

**Acceptance Scenarios**:

1. **Given** 3 successful judge calls with different scores, **When** `_style_score` runs, **Then** the returned score is the average of the 3 values (±0.001).
2. **Given** 1-2 failed calls, **When** the function runs, **Then** the average of the successful samples is returned, with a warning, NOT 0.5.
3. **Given** all calls fail, **When** the function runs, **Then** (0.5, "") — the existing fault tolerance stays untouched.
4. **Given** the selection of the critique, **When** multiple samples are produced, **Then** the critique of the sample closest to the average goes into the feedback (the GEPA reflection needs one concrete, representative text).

---

### User Story 2 - Calibration Proof (Priority: P2)

After the change the baseline is re-measured 3 times, and the spread of the style axis must drop from 0.188 to **≤ 0.10**. If this is not met: evaluation of N=5 or temp=0 (decision documented in tasks.md).

**Why this priority**: The noise reduction only exists if it measurably happens — with the same method that detected the problem.

**Independent Test**: 3 identical baseline runs (`cache=False`) → per-axis spread table; the style spread is below the target value.

**Acceptance Scenarios**:

1. **Given** the multi-sample judge, **When** the baseline runs 3 times, **Then** the style min–max spread ≤ 0.10.
2. **Given** the calibration, **When** the judge validation is repeated, **Then** the machine test score < 0.4 and the STYLE-REF reference > 0.7 (the discrimination has not degraded).
3. **Given** the new baseline averages, **When** the documentation happens, **Then** the new reference is recorded (the earlier ones are marked as obsolete).

---

### User Story 3 - Re-evaluation of the Mini-GEPA Decision (Priority: P3)

Re-opening the mini-GEPA question that was postponed in spec 011 T009, in light of the measured (reduced) noise level. The decision is the human's; the spec only provides the numbers.

**Why this priority**: The real goal of spec 012 — not improving the judge as such, but making the optimisation results interpretable again.

**Independent Test**: tasks.md contains the numeric re-evaluation (measured spread vs the expected mini-GEPA gain).

**Acceptance Scenarios**:

1. **Given** the measured new spread, **When** the decision preparation is done, **Then** it explicitly states the interpretability threshold in the form: "improvement > measured spread + margin".
2. **Given** the re-evaluation, **When** the human decides, **Then** the decision and its justification are recorded in tasks.md.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Partial fault tolerance stays: 1-2 failed judge calls must not yield a neutral 0.5 if there is a successful sample (otherwise fault tolerance would itself become a noise source — exactly the opposite direction).
- **FR-002**: `STYLE_JUDGE_SAMPLES` is a configurable constant in `eval/metric.py` (default 3); the tests can override it.
- **FR-003**: The other axes, the weights (0.25/0.25/0.15/0.15/0.20) and the feedback format stay unchanged. The critique comes from the sample closest to the average.
- **FR-004**: Every measurement runs with `cache=False` (spec 010 cache hygiene); the multi-sample calls must not come from the disk cache either.
- **FR-005**: The judge validation (spec 010 SC-002) must also hold after the change: robotic < 0.4, human > 0.7.

### Success Criteria

- **SC-001**: `_style_score` = the average of N successful samples; partial error handled; all-error → 0.5 (mock tests).
- **SC-002**: The style spread on 3 identical baseline runs is ≤ 0.10 (down from 0.188).
- **SC-003**: The judge discrimination is unchanged (machine < 0.4, STYLE-REF > 0.7).
- **SC-004**: The mini-GEPA re-evaluation is documented numerically; the human decision is recorded.

## Out of Scope

- Running GEPA (in any size) — spec 012 only improves the measurement.
- Extending the valset (the other way to reduce the noise) — a separate decision, a separate spec if needed.
- Replacing the judge model (the local Qwen judge stays; the self-evaluation compromise is unchanged).
- Parallelising the judge calls (async) — measurement time optimisation, only if it becomes a problem during the calibration.
- Production pipeline (server.py, pipeline.py, program.json) — untouched.
