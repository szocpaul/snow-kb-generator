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
   summarize_below=0.60, min_confidence=0.6): all 92 parts show. The SC-001
   target (≥5% on the full prompt) is therefore **RED** with the current config
   — the measured 0.45% is in the range of prompt-level noise fluctuation
   (temp 0.6).
2. **The quality did NOT degrade** (SC-002 GREEN): the delta's CI95 covers zero;
   the +0.009 is inside the noise band. The recall gate is 0/9 (SC-003 GREEN).
   The report run twice is byte-identical (SC-005 mechanics GREEN).
3. **The Score model scores highly** (compromised selection capability with the
   current rubric): the admin-meta parts (number/state) got 0.93–0.97 relevance.
   On the assigned_to/assignment_group parts the relevance is LOW (0.22–0.49),
   but the confidence is low as well (0.0–0.33) → the fail-open safety floor
   (min_confidence=0.6) forces them to show.
4. **The context tokens GREW by 1.4%**: rebuilding the JSON story (from the
   fragments) adds minimal formatting overhead; without hide this is a net
   increase. (The difference between tokenizing the chunked text and tokenizing
   the rebuilt text — the report measures the rebuilt one.)
5. **What this measurement still gives**: the rich_metric fluctuation of two
   generations with identical context (0.8417 vs 0.8511, per-example CI95 ±0.03)
   — this is the local Qwen rerun noise band, the basis for the SC-002
   calibration.

## The question of the next step

According to tasks.md the next phase is T010 (labeled sample — **already done,
56 parts**) + T011 ReAnchor calibration for the hide threshold + T012 gate.

**Foreseeable difficulty (flagged by the runner, not a decision):** the
calibration sweep can ONLY move hide_below (the min_confidence safety floor is
not calibratable). According to the selection capture data, for most of the
low-relevance parts the confidence is at the floor as well → it is possible that
the hide_below sweep ALONE cannot reach 5% (the fail-open shows remain
unchanged). The calibration report shows this numerically; if that is the case,
it becomes the subject of the T012 gate (e.g. target revision or redesigning the
rubric/question — the restart condition).

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
