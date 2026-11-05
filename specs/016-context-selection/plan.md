# Implementation Plan: Context Selection for Article Generation

**Branch**: `016-context-selection` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/016-context-selection/spec.md`

## Summary

The context pieces of GenerateKb (story sections, update set records, related KB articles) get a calibrated, typed Score-based qualification (hide/summarize/show) before generation; the execution is a plain Python policy, fail-open towards "show". The impact (token delta, quality delta) is proven with a baseline-first, replay-compatible measurement; the hide/show threshold is calibrated with an asymmetric ReAnchor — the 013–015 infrastructure is reused unchanged.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `typesafe-sdk` + `dspy[typesafe]` (part of the project since 013; the new decision is of the `dspy.experimental.Score` type — an eval wrapper following the 014/015 pattern), vendored `jev_replay.py` + `eval/jev_metrics.py`; the "summarize" comes from the local Qwen endpoint (see KD3)

**Storage**: JSONL recording (013 format) + the baseline/measurement artifacts (`artifacts/context_selection_*.json`)

**Testing**: pytest (the 387-test suite stays green + new tests)

**Target Platform**: Linux VPS, systemd-managed FastAPI service

**Performance Goals**: the additional latency of the selection ≤ the time saved on tokens (a System One decision takes ~70–500 ms/piece; the number of pieces is small — the story sections + update set records + related articles are typically < 30 pieces in total)

**Constraints**: fail-open = "show" (FR-002); the story body is never "hide" (FR-004); the quality MUST NOT degrade (SC-002); recall protection (SC-003); pinned model version; the safety floor cannot be moved by calibration

**Scale/Scope**: one new module (`context_selection.py`) + pipeline wiring + eval extension + tests; program.py/program.json stay untouched

## Constitution Check

*GATE: there is still no formal constitution — the check is based on the implicit principles in Agent.md.*

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

1. **Score-type decision per piece** (not a separate Noul per piece) — hide/summarize/show is an ordered scale, and the `Score` cuts point exactly at this (the cmpnd-ai v3 pattern); the question: "How much of this piece matters for writing the KB article?" (Alternative: two Noul steps — rejected, one scale instead of two thresholds is the natural model.)
2. **The execution is a plain Python policy** — the probabilities come from Jev, the thresholds from config/by hand; the model never "decides", it only scores (the base rule of the patterns repo: "Jev returns the probability, plain Python owns the policy").
3. **The "summarize" runs on the local Qwen endpoint** (the api_base in dev mode), NOT with the task model — in production as well the cheap layer does the summarizing; if the endpoint is not reachable, fail-open: the piece goes in as show. (Alternative: the task model (Kimi K3) summarizes — rejected, token cost and the Kimi token exposure; per the 015 dev-mode experience the local 27B is enough for summarizing.)
4. **Asymmetric calibration of the hide threshold**: hiding a relevant piece (recall error) is several times more expensive than showing noise — the ratio is examined with a sensitivity analysis in the calibration report (the 015 KD1 pattern; the initial ratio is 5:1, because fail-open protects towards show anyway).
5. **The selection lives in the pipeline layer, BEFORE the program** — the GEPA program and program.json stay untouched (Constitution Check). (Alternative: built into the signature — rejected, that would modify the program.)
6. **The SC-001 target is fixed after the baseline** — the Phase 0 noise inventory gives the realistic target (if there is no measurable noise, the spec stops — the 014 pattern).

   **FIXED at the T003 MANUAL GATE (2026-10-02, human approval): ≥5% token saving measured on the FULL PROMPT (template + context, the basis of the generating LM usage prompt_tokens) — NOT only on the context pieces.** The SC-002 quality gate is PRIMARY: if the 5% is only reachable with a quality degradation, quality wins (the T009 report reports this honestly, also with RED). The context-token reduction stays in the report as a reference number (baseline: 8540 context tokens, 1825 noise candidates = 21.4%; the full prompt is ~3200-8100 tokens/piece, so the 5% full-prompt target leaves less room — see
   artifacts/context_sc001_target.json).

## Phases

1. **Phase 0 – Baseline**: splitting the context of the gold examples + token inventory (per piece), noise estimate; the rich_metric baseline re-measured with `cache=False`; the SC-001 target is fixed AFTER this with a plan update.
2. **Phase 1 (US1)**: `context_selection.py` (Score decision + policy + recording + fail-open) + pipeline wiring + tests.
3. **Phase 2 (US2)**: measurement on the gold examples — token delta + rich_metric delta report, in replay mode.
4. **Phase 3 (US3)**: labelled context sample (min. 20 pieces: relevant/noise/borderline — machine + manual labelling following the fixture pattern) + ReAnchor calibration + report.
5. **Phase 4 – Closure**: the SC-001..SC-006 gates with exit code, Agent.md, backlog.

## Complexity Tracking

No constitution violation — the table stays empty.
