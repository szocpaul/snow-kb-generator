# T012 MANUAL GATE — spec 016 calibration report review

**Date**: 2026-10-02 (runner)
**Status**: WAITING for a human decision — the runner STOPPED.

## Gate subject (tasks.md T012)

Review of the calibration report; approval of the threshold change + justification
into Agent.md. The threshold may enter the config ONLY after human approval.
According to the T009 gate decision, on the basis of the CEILING NUMBER: target
revision, rubric redesign (the restart condition of the spec) or a stop.

## 1. The sweep of the labeled sample (56 parts, EXPLORATORY)

- Current threshold (hide_below=0.25): asymmetric cost **16.5** (5:1).
- Best candidate: **0.05**, cost **16.0** — the improvement is the verdict
  fluctuation of a SINGLE borderline part, not a real separation gain.
- Recall error (relevant hidden): **0** at both thresholds; the entire cost is a
  borderline verdict mismatch.
- Ratio sensitivity: 3:1 / 5:1 / 10:1 — **identical** (16.5 / 16.5 / 16.5 →
  16.0 / 16.0 / 16.0): there is no relevant-hiding in the cost, the ratio does
  not move it.
- ReAnchor (eval-only wrapper): train score **−0.2946 → −0.2946** — the
  calibration found no improvement.

**Runner position**: the threshold **SHALL STAY 0.25** — the 0.05 "improvement"
is at noise level, the config change is not justified (the "threshold stays"
branch is written to a file in the report).

## 2. The ceiling numbers (the table required by the T009 gate)

| View | Max savings | On the full prompt | SC-001 (1878 t / 5%) |
|---|---|---|---|
| Raw ceiling (hide_below sweep, production probes) | 4161 t | **11.1%** | reached (but a forbidden zone per the labeled cost) |
| **Cost-capped ceiling** (labeled cost ≤ current) | **0 t** | **0.0%** | NOT reached |
| Context-free estimate (after the state fix, see §3) | 428–450 t | **~1.1–1.2%** | NOT reached |

## 3. Root cause finding (the most important part)

The production `_score_piece` also sends the `story_context` (core text,
2000 chars) in the state. **This field INFLATES the Score**: the same noise
parts (number/state/assigned_to/assignment_group) get 0.86–0.99 relevance WITH
story_context (→ never hide), 0.00–0.03 WITHOUT story_context, with 0.93–1.00
confidence (→ clean separation). The relevant update set records are around
0.95 under both conditions. (56/56 parts compared, from the T007 vs T011
capture — the `probe_condition_finding` section of the report.)

**BUT**: even with the state fix (excluding story_context — the rubric/question
unchanged) only **~1.1–1.2%** is reachable on the full prompt, because the
model AND the labels consider the work_notes/comments parts (the bulk of the
noise inventory) essential/borderline — hiding them carries recall/quality risk.

## 4. The honest conclusion

**The SC-001 ≥5% target is NOT reachable with the current rubric on the gold
contexts without quality risk.** The actually safe noise (admin meta:
number/state/assigned_to/assignment_group) is ~0.9–1.2% of the full prompt. The
primacy of the SC-002 quality gate (T003 decision) draws this line.

## Decision options

- **(a) THRESHOLD STAYS (0.25) + production state fix (excluding story_context
  from the `_score_piece` state) + SC-001 target revision 5% → ~1%** → the
  runner implements the fix (the module's own code, the rubric/question
  unchanged), re-measures T007 with the new state, and runs the T013 gates
  with the target revised by the HUMAN.
- **(b) Rubric/question redesign** — the restart condition of the spec: the
  "How much of this piece matters" Score rubric does not separate in the
  production condition; a new baseline + re-measurement is needed.
- **(c) STOP** — the feature stays inactive with `enabled=false`; the runner
  report closes the spec; T013 runs only the measurable gates (SC-002/003/004/005
  GREEN, SC-001 RED = documented, SC-006 GREEN with the "stays" decision).

The threshold change (if there is one) goes into Agent.md with the
justification — the runner does NOT modify the config before the approval.

## Evidence files

- `artifacts/context_calibration_report_016.json` (sweep + ceiling + finding,
  byte-identical from replay)
- `artifacts/context_reanchor_report_016.json` (ReAnchor, EXPLORATORY)
- `artifacts/context_calibration_capture_016.json` (56 raw probes)
- `data/examples/context_labeled_016.json` (56 labeled parts)
