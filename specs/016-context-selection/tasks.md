# Tasks: Context Selection for Article Generation

**Input**: Design documents from `/specs/016-context-selection/`
**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can be run in parallel (different file, no dependency)
- **[USn]**: which user story it belongs to
- **MANUAL GATE**: human decision — the runner/agent MUST NOT tick it

## Phase 1: Setup + Baseline (playbook: baseline-first)

- [x] T001 [P] Config extension in `config.yaml`: `context_selection.enabled` (initial: false), `context_selection.model` (pinned), `context_selection.hide_below` / `summarize_below` thresholds, `context_selection.summarizer_endpoint` (local Qwen api_base, KD3), `context_selection.recording_path` — + a test for the config parsing
- [x] T002 [US2] Baseline measurement: splitting the context of the gold examples (story sections / update set records / related articles) + per-piece token inventory; rich_metric baseline re-measured with `cache=False` → `artifacts/context_baseline.json` (into a file, not into chat). **Detailed rules**: (a) the baseline is produced with the dev-mode local Qwen (the after-measurement runs with the same one — the comparison on the identical model is mandatory); (b) the token count is done with the Qwen tokenizer, or if that is not available, with a documented estimator (e.g. tiktoken) — the method used is marked in the report, and the after-measurement MUST use the SAME one
- [ ] T003 [US2] **MANUAL GATE**: the review of the baseline + noise inventory; the SC-001 token target value is FIXED here (per plan.md KD6, with a plan update); if there is no measurable noise → the spec stops (014 pattern) — the runner CANNOT check it off

## Phase 2: US1 – The Selection Module (test-first)

- [x] T004 [US1] Test: `tests/test_context_selection.py` — obvious noise → hide/summarize; relevant piece → show; low confidence → show (recall protection, `<` operator); SDK error → every piece show (fail-open); the story body is never hide (FR-004); recording entry schema. MUST fail before the implementation
- [x] T005 [US1] `src/snow_kb/context_selection.py` — splitting + Score decision (pinned model, `dspy.experimental.Score` eval-only pattern or direct SDK following the 013/014 pattern) + Python policy (hide/summarize/show from the threshold) + summarize on the local Qwen endpoint (fail-open: show) + JSONL recording
- [x] T006 [US1] Wiring into `pipeline.py`: GenerateKb receives the selected context (switchable via config flag, FR-006); program.py/program.json stay untouched — after T005

## Phase 3: US2 – Impact Measurement

- [ ] T007 [US2] Measurement on the gold examples: selected run vs baseline — per-example and aggregated token delta + rich_metric delta → `artifacts/context_selection_report.json`; the quality must not degrade beyond the noise band (SC-002); two runs in replay mode byte-identical (SC-005)
- [ ] T008 [US2] Recall gate (SC-003): test with exit code — the selected prompt contains the real component names referenced by the gold articles (0/9 missing)
- [ ] T009 [US2] **MANUAL GATE**: the review of the impact report — if the quality degraded or the recall dropped, the spec does NOT continue toward production — the runner CANNOT check it off

## Phase 4: US3 – Calibration

- [ ] T010 [US3] Labeled context sample (min. 20 chunks: relevant / noise / borderline — following the 015 fixture sample, machine + manual labeling), labels committed
- [ ] T011 [US3] ReAnchor calibration for the hide threshold, with the asymmetric metric (starting 5:1, KD4) + sensitivity analysis + report; the „threshold stays" branch also written to a file as a result; the safety floor (fail-open=show) is NOT calibratable
- [ ] T012 [US3] **MANUAL GATE**: the review of the calibration report; approval of the threshold change + the justification in Agent.md — the runner CANNOT check it off

## Phase 5: Closure

- [ ] T013 SC gates (SC-001..SC-006) with exit code, `cache=False`/replay mode; full pytest suite green (387 + new); Agent.md log entry; backlog: close TASK-3; commit + push

## Dependencies

- T004 (test) BEFORE T005 — test-first order
- T005 blocks T006; T007 only after T002 (baseline) and T006
- T011 only after T010; T012 (gate) blocks the config change
- MANUAL GATEs (T003, T009, T012) require a human

## Validation Checklist

- [ ] Every FR has a task (FR-001→T005, FR-002→T004/T005, FR-003→T005, FR-004→T004/T005, FR-005→T002/T007, FR-006→T001/T006)
- [ ] Every SC has a gate (SC-001→T003/T013, SC-002→T007, SC-003→T008, SC-004→T004, SC-005→T007, SC-006→T011/T012)
- [ ] The tests are in place before the implementation
- [ ] Every task names a concrete file
