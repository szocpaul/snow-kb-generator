# spec 016 runner report — CONTEXT SELECTION FOR ARTICLE GENERATION

**Status**: 🟡 PARKED at the **T012 MANUAL GATE** — waiting for a human decision
(review of the calibration report: threshold stays + state fix + target value revision,
rubric redesign or stop).

**Branch**: `016-context-selection` | **Run mode**: DEV (SNOW_KB_DEV_MODE=1,
local Qwen3.8-27B; no Kimi token usage) | **Date**: 2026-10-02

## Per-phase results

### Phase 1: Setup + Baseline

| Task | Status | Result |
|---|---|---|
| T001 config | ✅ DONE | `context_selection` config block (enabled=false, pinned jev-1.13.0, hide_below=0.25, summarize_below=0.60, min_confidence=0.6, summarizer_endpoint=local Qwen, recording_path) + 5 new config tests |
| T002 baseline | ✅ DONE | `artifacts/context_baseline.json`: 9 gold examples, local Qwen, cache=False; **8540 context tokens**, **1825 noise candidates (21.4%)**, **rich_metric avg 0.8417**; byte-identical from replay |
| T003 MANUAL GATE | ✅ APPROVED (human, 2026-10-02) | **SC-001 = ≥5% on the FULL PROMPT** (LM usage prompt_tokens), SC-002 primary; recorded: plan.md KD6 + `artifacts/context_sc001_target.json` |

### Phase 2: US1 – the selection module

| Task | Status | Result |
|---|---|---|
| T004 tests | ✅ DONE | `tests/test_context_selection.py` — 22 tests, FAIL-first (collection error due to the missing module), then green |
| T005 module | ✅ DONE | `src/snow_kb/context_selection.py`: splitting (JSON/markdown story, update set XML, related rows) + Score decision (pinned jev-1.13.0, typesafe_sdk.Score) + Python policy (`<` operator, boundary value toward the safe direction) + fail-open show + FR-004 (no LLM call is started for story_core) + summarize at the local endpoint (fail-open to the original text) + jev-format JSONL recording |
| T006 integration | ✅ DONE | `pipeline.py`: the program receives the SELECTED context; the 014/015 gate and the strip guardrails get the ORIGINAL; enabled=False → bit-identical behavior; program.py/program.json untouched |

### Phase 3: US2 – Impact measurement

| Task | Status | Result |
|---|---|---|
| T007 measurement | ✅ DONE | **INERT selection** (0 hide / 0 summarize / 92 show): full prompt reduction **0.45%** (SC-001 RED at the current thresholds); quality **did not degrade** (0.8417 → 0.8511, CI95 [−0.029, +0.038], SC-002 green); report byte-identical (SC-005 mechanics green); context tokens +1.4% (JSON rebuild overhead) |
| T008 recall gate | ✅ DONE | **0/9 dropouts**, with exit code (SC-003 green) |
| T009 MANUAL GATE | ✅ APPROVED (human, 2026-10-02) | CONTINUATION with the T011 calibration; mandatory in the report: ceiling number, distance from 5%, sensitivity analysis, "threshold stays" branch |

### Phase 4: US3 – Calibration

| Task | Status | Result |
|---|---|---|
| T010 labeled sample | ✅ DONE | **56 pieces** (39 noise / 14 borderline / 3 relevant), justified review per piece; `data/examples/context_labeled_016.json` committed |
| T011 calibration | ✅ DONE | `artifacts/context_calibration_report_016.json` + ReAnchor report: labeled sweep 0.25→0.05 MARGINAL (16.5→16.0, recall error 0, ratio-insensitive) → **proposal: the threshold STAYS**; ReAnchor −0.2946→−0.2946; **ceiling: raw 11.1% / cost-limited 0.0% / with state fix ~1.1-1.2%**; **root cause: the production story_context inflates the Score**; the 5% target is not reachable with the rubric |
| T012 MANUAL GATE | 🟡 WAITING | gate report: `specs/016-context-selection/gate-T012.md`; options: (a) threshold stays + state fix + target value revision ~1%, (b) rubric redesign (spec restart), (c) documented stop with SC-001 RED |

### Phase 5: Closure

| Task | Status | Result |
|---|---|---|
| T013 SC gates | ⏸ | `eval/context_sc_gates_016.py` ready; according to the T003 decision the SC-001 gate measures the full prompt ratio |

## Baseline key numbers (the subject of the T003 gate)

- Measurable noise: **21.4%** (1825/8540 tokens) — the spec does NOT stop.
- Obvious hide candidates (number/state/assigned_to/assignment_group): 333 tokens (3.9%).
- Summarize candidates (work_notes/comments): ~1492 tokens.
- Token method: llama.cpp `/tokenize` (Qwen's real tokenizer) — the after measurement uses the same.

## SC gates (preliminary, from the T007 measurement)

| Gate | Status | Comment |
|---|---|---|
| SC-001 (cost) | 🔴 RED at the current thresholds | measured 0.45% < 5% (inert selection) |
| SC-002 (quality) | 🟢 GREEN | CI95 [−0.029, +0.038] covers the 0 |
| SC-003 (recall) | 🟢 GREEN | 0/9 dropouts |
| SC-004 (fail-open) | 🟢 GREEN | 22 tests (T013 runs them with exit code) |
| SC-005 (replay) | 🟢 GREEN | report byte-identical |
| SC-006 (calibration) | ⏸ after the T012 decision | the report is ready (n=56, decision+justification, safety floor untouched); the gate runs in T013 |

## Pytest-suite

- Starting point: **387 passed** ✅
- After T001/T004–T006: **414 passed** ✅ (under `env -u SNOW_KB_DEV_MODE`)

## Commit-hash-ek

- `ee0d6e4` T001: context_selection config-blokk + config-tesztek
- `8cbec87` T004+T005+T006: context_selection module + pipeline integration + 22 tests (414 green)
- `3502be3` T002: baseline measurement + eval scripts
- `2485fc8` T003 MANUAL GATE: gate report
- `da4e7ab` T003 APPROVED: SC-001 = ≥5% on the full prompt — target.json + plan KD6
- `9b6b4d1` T008+T010: recall gate green + 56-piece labeled sample
- `0b9c90d` T007: impact measurement — INERT selection, quality green
- `3b4138a` T009 MANUAL GATE: gate report
- `0b9c90d`…`9b6b4d1` T007/T008/T010 (committed in the order preceding T009)
- `c88f2e1` T011: ReAnchor + sweep + ceiling analysis + story_context root cause
- `053eb5b` T012 MANUAL GATE: gate report — runner WAITS

## Stuck / waiting

The runner waits at the T012 MANUAL GATE: the review of the calibration report. The
gate message sent to the `snow-main` session. The config is NOT modified until the
before approval; until the decision, the runner does NOT continue with T013.
