# spec 016 runner report — CONTEXT SELECTION FOR ARTICLE GENERATION

**FINAL STATE**: ✅ **CLOSED** — the spec STOPPED at the T012 MANUAL GATE with a
human decision (**option (c)**, 2026-10-02): the feature closed with
`enabled=false`, inactive, with a full measurement trail and one real root cause
fix (state fix). This is the accepted final state according to the spec goal:
under the "measured, not claimed" principle a stop is a full-value output as
well, if the ceiling is numeric and the cause is identified.

**Branch**: `016-context-selection` | **Run mode**: DEV (SNOW_KB_DEV_MODE=1,
local Qwen3.8-27B; no Kimi token usage) | **Date**: 2026-10-02

## Final state of the SC gates (`python -m eval.context_sc_gates_016` → exit 0)

| Gate | Status | Numbers |
|---|---|---|
| SC-001 (cost) | 🔴 **DOCUMENTED RED (accepted, T012)** | measured 0.45% on the full prompt vs ≥5% target; cost-capped ceiling 0.0%; with the state fix ~1.1–1.2% — the target is not reachable without quality risk (the primacy of SC-002 drew the line) |
| SC-002 (quality) | 🟢 GREEN | rich_metric 0.8417 → 0.8511, paired CI95 [−0.029, +0.038] (covers zero) |
| SC-003 (recall) | 🟢 GREEN | 0/9 drops, gate with exit code |
| SC-004 (fail-open) | 🟢 GREEN | 23 tests green (SDK error → all show; low confidence → show; story core never hidden) |
| SC-005 (replay) | 🟢 GREEN | the impact measurement report is byte-identical when run twice |
| SC-006 (calibration) | 🟢 GREEN | n=56 (≥20); sweep decision exploratory; **T012 final decision: "stays" (0.25)**; config unchanged; safety floor untouched |

## Per-phase results

### Phase 1: Setup + Baseline
- **T001** ✅ `context_selection` config block + 5 config tests.
- **T002** ✅ Baseline: 9 gold, local Qwen, cache=False; **8540 context tokens,
  1825 noise candidates (21.4%)**, rich_metric avg **0.8417**; token method:
  llama.cpp `/tokenize`; byte-identical from replay.
- **T003** ✅ MANUAL GATE — **approved**: SC-001 = ≥5% on the FULL PROMPT
  (LM usage prompt_tokens), SC-002 primary.

### Phase 2: US1 – the selection module
- **T004/T005/T006** ✅ test-first order: `context_selection.py`
  (chunking + Score decision with pinned jev-1.13.0 + Python policy `<`
  operator + fail-open show + FR-004 story core protection + summarize on the
  local Qwen + jev recording) + pipeline wiring (the 014/015 gate receives the
  ORIGINAL context; program.py/program.json untouched).

### Phase 3: US2 – Impact measurement
- **T007** ✅ **INERT selection** (0 hide / 0 summarize / 92 show): full-prompt
  reduction **0.45%**; the quality did not degrade; context tokens +1.4% (JSON
  rebuild overhead).
- **T008** ✅ recall gate **0/9 drops**.
- **T009** ✅ MANUAL GATE — **continuation approved** with the T011 calibration
  (mandatory elements: ceiling number, distance from the target, sensitivity, the
  "stays" branch).

### Phase 4: US3 – Calibration
- **T010** ✅ 56 labeled parts (39 noise / 14 borderline / 3 relevant),
  per-part justified review, committed.
- **T011** ✅ ReAnchor (−0.2946 → −0.2946, no improvement) + sweep: the
  0.25→0.05 "improvement" is at noise level (16.5→16.0, recall error 0,
  ratio-insensitive). **Ceiling table**: raw 11.1% / cost-capped 0.0% / with the
  state fix ~1.1–1.2%. **Root cause finding**: the production `story_context`
  INFLATES the Score (noise: 0.86–0.99 with ctx vs 0.00–0.03 without ctx,
  conf 0.93–1.00).
- **T012** ✅ MANUAL GATE — **human decision: (c) STOP**: the threshold STAYS
  0.25 (no config change); the **state fix WAS INCLUDED** (the `_score_piece`
  state no longer contains the core text + test); the feature stays
  `enabled=false`; SC-001 documented RED; Agent.md §48 log entry.

### Phase 5: Closure
- **T013** ✅ SC-001..SC-006 gates with exit code (see the table above, exit 0);
  full pytest suite **415 passed** (`env -u SNOW_KB_DEV_MODE`);
  Agent.md §48 log entry; backlog **TASK-3 closed** (Done, with the documented
  output); commit + push to the `016-context-selection` branch.

## Key lessons (the full report: Agent.md §48)

1. "No measurable effect" is a full-value spec output as well — the ceiling is
   numeric, the root cause is identified, the stop is documented.
2. The probe condition (what goes into the state) is part of the quality of the
   decision — the calibration wrapper and the production state should be
   deliberately identical.
3. Context noise ≠ prompt noise: 21.4% of the context is noise candidates, but
   the context is ~23% of the full prompt — the target is tied to the name of
   the gate.

## Commit hashes (016-context-selection branch)

- `ee0d6e4` T001 config block + tests
- `8cbec87` T004+T005+T006 module + wiring (414 green)
- `3502be3` T002 baseline + eval scripts
- `2485fc8` T003 gate report
- `da4e7ab` T003 approved: SC-001 target (full prompt 5%)
- `9b6b4d1` T008+T010 recall gate + labeled sample
- `0b9c90d` T007 impact measurement (INERT)
- `3b4138a` T009 gate report
- `c88f2e1` T011 calibration + ceiling + root cause
- `053eb5b` T012 gate report
- `23fc303` T012 approved: state fix + test (415 green)
- T013 closing commit: SC gate code (SC-001 documented RED + SC-006 T012 final
  check), calibration report with the T012 decision, Agent.md §48, this report
