# Implementation Plan: Audience Decision with Calibrated Confidence

**Branch**: `013-audience-typed-decision` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/013-audience-typed-decision/spec.md`

## Summary

The `ExtractChange.audience` field (`Literal["helpdesk","end-user","developer"]`) is produced by a
dedicated, typed decision call alongside the generative `change_summary`/`key_steps`, with
calibrated confidence and replay-compatible logging. On low confidence the default is
`developer` + a work_notes note; if the decision service fails, fail-open to the existing path.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: DSPy 3.3.x (the signatures are untouched, the program is untouched), FastAPI + Uvicorn
(server), `typesafe-sdk` from the public PyPI (`pip install typesafe-sdk`), and for the measurement
the `jev-dspy-lab` metric code (MIT, vendored or as a dependency — see Key Decisions)

**Storage**: N/A (logging goes into the existing log infrastructure + JSONL recording files)

**Testing**: pytest (the existing 286-test suite stays green + new tests)

**Target Platform**: Linux VPS, systemd-managed FastAPI service

**Project Type**: web-service (webhook-driven pipeline)

**Performance Goals**: the decision call ≤ ~500 ms p95 (the 70–500 ms band according to TypeSafe),
must not perceptibly slow down the Story → KB pipeline

**Constraints**: fail-open is mandatory; the generative path remains as a switchable fallback;
pinned model version for the calibration measurements

**Scale/Scope**: one signature field, one pipeline insertion, ~3 affected files + tests

## Constitution Check

*GATE: the repository currently has no formal constitution file — adding one is recommended as a
separate initiative (`/speckit-constitution`), it is not blocking. The check below is based on the
principles implicitly recorded in the project Agent.md and README.*

| Principle (implicit) | Check |
|---|---|
| "Measured, not claimed" | ✅ — the SCs are numeric, replay-based measurement |
| Fail-open / error tolerance (the spec 010 FR-002 pattern) | ✅ — FR-001 is mandatory |
| The pipeline's GEPA program stays untouched | ✅ — the insertion is outside the program, in the pipeline layer |
| Baseline first | ✅ — Phase 0 records the current model's audience decisions on the gold examples |

## Architecture

```text
Story fetch + Update Set fetch (unchanged)
        │
        ▼
┌─ pipeline.py ─────────────────────────────────────────────┐
│  ExtractChange (DSPy + Kimi K3)                            │
│    → change_summary, key_steps          (unchanged)        │
│                                                            │
│  NEW: decide_audience(story_text)                          │
│    → TypeSafe Choice: helpdesk / end-user / developer      │
│    → confidence + per-option probabilities                 │
│    → JSONL recording (hash + response + latency + model)   │
│    → error/timeout → fail-open: LLM-fallback (config-flag) │
│    → confidence < threshold → developer + work_notes note  │
└────────────────────────────────────────────────────────────┘
        │
        ▼
GenerateKbFromTemplate (unchanged, receives the audience as context)
```

## Key Decisions

1. **Direct SDK call, NOT the `dspy-typesafeify` fork** — the fork is a PoC, not a production
   distribution; the DSPy signature and the GEPA program stay untouched. (Alternative: the fork's
   decorator — rejected, because we do not take an upstream fork into production.)
2. **Jev as the decision model** — it returns calibrated, per-option probability (RLCD).
   (Alternative: asking the LLM for its own confidence estimate — rejected, RLHF models are
   overconfident; see the spec Background.)
3. **Measurement with the jev-dspy-lab metric code** (selective risk, coverage, ECE, Brier),
   adapted at the SDK level to record/replay. (Alternative: our own mini metric — rejected, the
   calibration statistics are not trivial and the lab is MIT-licensed and battle-tested.)
4. **Fail-open, not fail-closed** — on a TypeSafe outage the pipeline keeps running on the
   existing path, with a warning. (Alternative: blocking — rejected, availability comes first;
   this is the tradeoff recorded in the spec's Edge Cases, a MANUAL GATE in tasks.md.)
5. **Pinned model version** for the calibration (`jev-1.13.0` or the pinned version current at
   measurement time), not `jev-latest` — playbook: "model swap = baseline re-measurement".
6. **Low-confidence default = `developer`** — the safest technical tone
   (spec Assumptions; if the review sees it differently, it is corrected in tasks.md).

## Phases

1. **Phase 0 – Baseline (US1 precondition)**: the current model's audience decisions
   recorded on the 9 gold examples (into a file, not into chat); verification of the gold audience labels
   (as per the Assumptions, otherwise manual labelling).
2. **Phase 1 (US1)**: `decide_audience` module + recording + fail-open + tests.
3. **Phase 2 (US2)**: confidence threshold + fallback + work_notes note + tests.
4. **Phase 3 – Measurement and calibration**: live recording on the gold + mock sample, offline replay,
   SC-001..SC-004 gates with exit codes.
```

## Complexity Tracking

There is no constitution violation — the table stays empty.
