# spec 016 runner report — CONTEXT SELECTION FOR ARTICLE GENERATION

**Status**: 🟡 PARKED at the **T003 MANUAL GATE** — waiting for a human decision
(baseline review + recording the SC-001 target value).

**Branch**: `016-context-selection` | **Run mode**: DEV (SNOW_KB_DEV_MODE=1,
local Qwen3.8-27B; no Kimi token usage) | **Date**: 2026-10-02

## Per-phase results

### Phase 1: Setup + Baseline

| Task | Status | Result |
|---|---|---|
| T001 config | ✅ DONE | `context_selection` config block (enabled=false, pinned jev-1.13.0, hide_below=0.25, summarize_below=0.60, min_confidence=0.6, summarizer_endpoint=local Qwen, recording_path) + 5 new config tests |
| T002 baseline | ✅ DONE | `artifacts/context_baseline.json`: 9 gold examples, local Qwen, cache=False; **8540 context tokens**, **1825 noise candidates (21.4%)**, **rich_metric avg 0.8417**; byte-identical from replay |
| T003 MANUAL GATE | 🟡 WAITING | gate report: `specs/016-context-selection/gate-T003.md`; proposed SC-001 target: **≥5% context token reduction** |

### Phase 2: US1 – the selection module

| Task | Status | Result |
|---|---|---|
| T004 tests | ✅ DONE | `tests/test_context_selection.py` — 22 tests, FAIL-first (collection error due to the missing module), then green |
| T005 module | ✅ DONE | `src/snow_kb/context_selection.py`: splitting (JSON/markdown story, update set XML, related rows) + Score decision (pinned jev-1.13.0, typesafe_sdk.Score) + Python policy (`<` operator, boundary value toward the safe direction) + fail-open show + FR-004 (no LLM call is started for story_core) + summarize at the local endpoint (fail-open to the original text) + jev-format JSONL recording |
| T006 integration | ✅ DONE | `pipeline.py`: the program receives the SELECTED context; the 014/015 gate and the strip guardrails get the ORIGINAL; enabled=False → bit-identical behavior; program.py/program.json untouched |

### Phase 3–5: prepared, runs after the T003 gate

- T007/T008/T010/T011/T013 eval scripts written (`eval/context_measure.py`,
  `eval/context_recall_gate.py`, `eval/context_labeled.py`,
  `eval/context_calibration_016.py`, `eval/context_sc_gates_016.py`) —
  the live measurements start after the gate decision.

## Baseline key numbers (the subject of the T003 gate)

- Measurable noise: **21.4%** (1825/8540 tokens) — the spec does NOT stop.
- Obvious hide candidates (number/state/assigned_to/assignment_group): 333 tokens (3.9%).
- Summarize candidates (work_notes/comments): ~1492 tokens.
- Token method: llama.cpp `/tokenize` (Qwen's real tokenizer) — the after measurement uses the same.

## SC-gate-ek

Not yet run (T013 at the closing; the SC-001 target value is recorded at the T003 gate).

## Pytest-suite

- Starting point: **387 passed** ✅
- After T001/T004–T006: **414 passed** ✅ (under `env -u SNOW_KB_DEV_MODE`)

## Commit-hash-ek

- `ee0d6e4` T001: context_selection config-blokk + config-tesztek
- `8cbec87` T004+T005+T006: context_selection module + pipeline integration + 22 tests (414 green)
- `3502be3` T002: baseline measurement + eval scripts
- `2485fc8` T003 MANUAL GATE: gate report — runner WAITS

## Stuck / waiting

The runner waits at the T003 MANUAL GATE: the human review is needed for the baseline and
for recording the SC-001 target value (proposal: 5%). The gate message was sent to the
`snow-main` session. Until the decision, the runner does NOT continue with T007.
