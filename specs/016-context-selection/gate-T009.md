# T009 MANUAL GATE — spec 016 impact report review

**Date**: 2026-10-02 (runner)
**Status**: WAITING for a human decision — the runner STOPPED.

## Gate subject (tasks.md T009)

Review of the impact report — if the quality degraded or the recall dropped, the
spec does NOT go further towards production.

## Key numbers (artifacts/context_selection_report.json)

| Metric | Baseline | Selected | Delta |
|---|---|---|---|
| Context tokens (story+US) | 8540 | 8657 | **+1.4%** (it grew!) |
| Full prompt (LM usage) | 37550 | 37380 | **−0.45%** |
| rich_metric average | 0.8417 | 0.8511 | +0.009, CI95 [−0.029, +0.038] |
| Recall (real names) | — | 0/9 drops | ✅ |
| Verdict distribution | — | 0 hide / 0 summarize / 92 show | — |

## Honest findings (NOT "spun to look good")

1. **The selection is INERT at the current thresholds** (hide_below=0.25,
   summarize_below=0.60, min_confidence=0.6): all 92 pieces show. The SC-001
   target (≥5% of the whole prompt) so **RED** with the current config — the measured
   0.45% is the order of magnitude of the prompt-level fluctuation (temp 0.6).
2. **The quality did NOT degrade** (SC-002 green): the delta's CI95 covers 0; the
   +0.009 is within the noise band. The recall gate is 0/9 (SC-003 green). The report
   double run is byte-identical (SC-005 mechanics green).
3. **The Score model scores high** (compromised selection capability on the
   current rubric): the admin-meta pieces (number/state) got 0.93–0.97
   relevance. On the assigned_to/assignment_group pieces the relevance
   ALACSONY (0.22–0.49), de a confidence is alacsony (0.0–0.33) → a fail-open
   safety floor (min_confidence=0.6) forces them to be shown.
4. **The context token GREW by 1.4%**: the JSON story reconstruction
   (from fragments to object) adds minimal formatting overhead; without hide this
   net extra. (The chunk-then-tokenize and the rebuilt text
   difference between tokenization — the report measures the rebuilt one.)
5. **What this measurement still gives**: the twice-generated output with identical context
   fluctuation of the rich_metric (0.8417 vs 0.8511, per-example CI95 ±0.03) — this is the
   local Qwen rerun noise band, the basis of the SC-002 calibration.

## The question of the next step

According to tasks.md the next phase is T010 (labeled sample — **already done,
56 parts**) + T011 ReAnchor calibration for the hide threshold + T012 gate.

**Foreseeable difficulty (the runner flags it, does not decide):** the calibration sweep ONLY
can move hide_below (the min_confidence safety floor is not calibratable).
According to the selection-capture data, for most of the low-relevance pieces
the confidence is at the floor → maybe the hide_below sweep ALONE cannot
5% (the fail-open shows remain unchanged). The calibration report will
shows it numerically; if so, that is the subject of the T012 gate (e.g. target value-
revision or the redesign of the rubric/question — the restart condition).

## Decision options

- **CONTINUE with the T011 calibration** (the quality and the recall are fine,
  the spec can go on) → the runner runs ReAnchor + sweep + report, then stops
  again at the T012 gate.
- **STOP** → the feature stays inactive with `enabled=false`, the runner report
  closes the spec with the results from here.

## Evidence files

- `artifacts/context_selection_report.json` (the source of the numbers above,
  byte-identical from replay)
- `artifacts/context_selection_capture.json` (per-part verdict + relevance +
  confidence — the "high Score" claim is verifiable)
- `artifacts/context_selection_measurement.jsonl` (the recording of the
  system_one decisions, replay-compatible)
- `eval/context_recall_gate.py` output: 0/9 drops
