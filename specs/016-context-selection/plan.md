# Implementation Plan: Context Selection for Article Generation

**Branch**: `016-context-selection` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/016-context-selection/spec.md`

## Summary

The context pieces of GenerateKb (story sections, update set records, related
KB articles) get a calibrated, typed Score rating before the generation
(hide/summarize/show); the execution is plain Python policy, fail-open to the „show"
direction. The effect (token delta, quality delta) is baseline-first, replay-compatible
is proven by measurement; the hide/show threshold with asymmetric ReAnchor calibration —
the 013–015 infrastructure is reused unchanged.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `typesafe-sdk` + `dspy[typesafe]` (in the project since 013;
the new decision is of type `dspy.experimental.Score` — eval wrapper for the 014/015 sample),
vendored `jev_replay.py` + `eval/jev_metrics.py`; the „summarize" on the local Qwen-
from the endpoint (see KD3)

**Storage**: JSONL recording (013 format) + the baseline/measurement artifacts
(`artifacts/context_selection_*.json`)

**Testing**: pytest (the 387-test suite stays green + new tests)

**Target Platform**: Linux VPS, systemd-managed FastAPI service

**Performance Goals**: the extra latency of the selection ≤ the token saving
time saving (the System One decision ~70–500 ms/piece; the number of pieces is small — the
story sections + update set records + related articles typically total
< 30 pieces)

**Constraints**: fail-open = „show" (FR-002); the story main body is never „hide"
(FR-004); the quality must not degrade (SC-002); recall protection (SC-003);
pinned model version; safety floor not movable by calibration

**Scale/Scope**: a new module (`context_selection.py`) + pipeline integration +
eval addition + tests; program.py/program.json untouched

## Constitution Check

*GATE: there is still no formal constitution — the check is based on the implicit
principles of Agent.md.*

| Principle (implicit) | Check |
|---|---|
| "Measured, not claimed" | ✅ — the SC-001 target is fixed AFTER the Phase 0 baseline |
| Fail-open | ✅ — FR-002: error/low confidence → show |
| The GEPA program stays untouched | ✅ — the selection happens BEFORE the program, in the pipeline layer |
| Baseline first | ✅ — Phase 0: token + quality + noise inventory recorded |
| Recall protection | ✅ — SC-003 exit-code test (the pattern of the extractor refinement) |

## Architecture

```text
Story fetch + Update Set fetch + related-article search (unchanged)
        │
        ▼
┌─ pipeline.py ───────────────────────────────────────────────────────┐
│  NEW: select_context(pieces)  ← the 016 module                       │
│    per piece: Score decision (Jev, pinned) + confidence              │
│    → Python policy: hide (< threshold) / summarize / show            │
│    → story body: always show (FR-004)                                │
│    → summarize: local Qwen summary (KD3)                             │
│    → JSONL recording + fail-open (error → show)                      │
│                                                                      │
│  GenerateKbFromTemplate with the SELECTED context (program untouched)│
└──────────────────────────────────────────────────────────────────────┘
        │
        ▼
servicenow_client.create_kb_article → the 014/015 gate stays unchanged
```

## Key Decisions

1. **Score-type decision per piece** (not a separate Noul per piece) — the hide/summarize/show
   an ordered scale, the `Score` cuts are for this (the cmpnd-ai v3 sample);
   the question: „How much of this piece matters for writing the KB article?"
   (Alternative: two Noul steps — rejected, instead of two thresholds one scale on the
   a natural model.)
2. **The execution is plain Python policy** — the probabilities from Jev, the thresholds
   from config/manually; the model never „decides" it, it only scores (the patterns repo
   basic rule: „Jev returns the probability, plain Python owns the policy").
3. **The „summarize" on the local Qwen endpoint** (the dev-mode api_base), NOT the
   with the task model — in production too the cheap layer summarizes; if the endpoint is not
   is reachable, fail-open: the piece enters as show. (Alternative: the task model
   (Kimi K3) summary — rejected, token cost and Kimi-token involvement;
   according to the 015 dev-mode experience the local 27B is enough for summarizing.)
4. **Asymmetric calibration for the hide threshold**: hiding a relevant piece
   (recall error) is many times more expensive than showing the noise — the ratio is
   calibration report with sensitivity analysis (the 015 KD1 sample; the starting
   ratio 5:1, because fail-open protects in the show direction anyway).
5. **The selection in the pipeline layer, BEFORE the program** — the GEPA program and the
   program.json untouched (Constitution Check). (Alternative: the signature-
   built — rejected, that would be a modification of the program.)
6. **The SC-001 target value is fixed after the baseline** — the Phase 0 noise inventory gives the
   real goal (if there is no measurable noise, the spec stops — the 014 sample).

## Phases

1. **Phase 0 – Baseline**: splitting the context of the gold examples + token inventory
   (per piece), noise estimation; the rich_metric baseline re-measured with `cache=False`;
   the SC-001 target value is fixed AFTER THIS by updating the plan.
2. **Phase 1 (US1)**: `context_selection.py` (Score decision + policy + recording +
   fail-open) + pipeline integration + tests.
3. **Phase 2 (US2)**: measurement on the gold examples — token delta + rich_metric delta
   report, in replay mode.
4. **Phase 3 (US3)**: labeled context sample (min. 20 pieces: relevant/noise/
   boundary case — for the fixture sample with machine + manual labeling) + ReAnchor calibration +
   riport.
5. **Phase 4 – Closing**: SC-001..SC-006 gates with exit code, Agent.md, backlog.

## Complexity Tracking

There is no constitution violation — the table stays empty.
