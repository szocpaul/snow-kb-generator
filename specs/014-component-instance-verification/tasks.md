# Tasks: Component Name Verification Against the Instance + Production Push Gate

**Input**: Design documents from `/specs/014-component-instance-verification/`
**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can be run in parallel (different file, no dependency)
- **[USn]**: which user story it belongs to
- **MANUAL GATE**: human decision — the runner/agent MUST NOT tick it

## Phase 1: Setup

- [ ] T001 [P] Config extension in `config.yaml`: `verification_gate.enabled` (initial: false), `verification_gate.behavior` (flag/strip/block, default: `flag`), `verification_gate.model` (pinned version), `verification_gate.confidence_threshold` (initial: 0.7), `verification_gate.spotcheck_cache_path`, `verification_gate.recording_path` — + test for the config parsing
- [ ] T002 [P] `.env.example` check: `TYPESAFE_API_KEY` is already in it (since 013); if the spot-check needs a new permission on ServiceNow, document it under deploy/

## Phase 2: Baseline (US1 precondition — playbook: baseline first)

- [ ] T002b [US1] PDI preparation: import the Update Sets of the measured stories into the PDI (`scripts_pdi/bootstrap_pdi.py` extension or manual import) + verification with a spot-check on one sample component — the gold samples come from the customer instance, without import the spot-check is 100% false positive (spec Assumptions)
- [ ] T003 [US1] Baseline inventory: extract the component name candidates from the existing gold articles + one freshly generated article sample (011 pattern: quoted names, CamelCase, dotted), per-example JSON under `artifacts/` — with unchanged code
- [ ] T004 [US1] Check the candidates from T003: update set content (where available) + manual/spot-check in the instance → how many „does not exist" names there are TODAY (the size of the problem in numbers, written to a file)
- [ ] T005 [US1] **MANUAL GATE**: the review of the baseline inventory — the runner CANNOT check it off

## Phase 3: US1 – Instance axis in the metric (test first)

- [ ] T006 [US1] Test: metric instance axis — with mock spot-check answers: non-existent name → axis 0 + naming; only real names → 1.0; query error → fail-open (the axis is skipped with a warning, FR-002/FR-006); 0 false positive on the gold articles. FAIL before implementation
- [ ] T007 [US1] `src/snow_kb/verification.py` — candidate extraction (reusing the 011 pattern), update-set whitelist building (from the `get_update_set_changes` output), per-name spot-check on the `servicenow_client` session (cached, `spotcheck_cache_path`), fail-open on every query error; wiring into `eval/metric.py` as a new axis (the story-based axis stays untouched)

## Phase 4: US2 – Production push-gate (test first)

- [ ] T008 [US2] Test: gate before `servicenow_client._create_kb_article_live` — non-existent name → behavior per configuration (default: work_notes note with the names + confidence); real names → article unchanged; instance unreachable → fail-open, the article goes out with a warning. FAIL before implementation
- [ ] T009 [US2] Gate wiring into `pipeline.py` (before the `_create_kb_article_live` call): running `verify_component_names`, executing the behavior (flag: work_notes note; strip/block only with config), JSONL recording (013 format) — after T007

## Phase 5: US3 – Calibrated layer for the ambiguous cases (test first)

- [ ] T010 [US3] Test: borderline cases — a spelling variant of a real component → „exists (reference)" with high confidence; unknown name → low confidence / „does not exist"; SDK error → fail-open to the deterministic path. FAIL before implementation
- [ ] T011 [US3] Calibrated decision in `verification.py`: TypeSafe Noul per borderline candidate (pinned model), threshold logic based on the 013 sample (`<` operator, eps), recording + fail-open — after T007

## Phase 6: Measurement, calibration, closing

- [ ] T012 Building the labeled sample: **≥20 examples** (real names + intentional spelling variants + fabricated names), the labels committed next to the dataset — the lesson of 013: minimum sample size for the SC gate
- [ ] T013 [US3] Calibration measurement: live capture on the labeled sample with the pinned model, offline replay; ReAnchor only on the evaluation wrapper (the 013 T012 pattern); the resulting threshold into the config; gates: SC-001 (gold: 0 false positive), SC-002 (selective risk ≤0.15, coverage ≥0.7 at the 0.7 gate), SC-003 (fail-open tests), SC-004 (byte-identical double replay) — with exit code, `cache=False`/replay mode
- [ ] T014 **MANUAL GATE**: approval of the gate default behavior (KD1: flag) and the fail-open tradeoff before a production run; review of the SC gates; if the threshold changes, the justification goes into Agent.md — the runner CANNOT check it off
- [ ] T015 Closing: the full pytest suite green, Agent.md log entry (facts, decisions, lessons), commit + push, backlog update (closing TASK-2 / the state of the verification layer)

## Dependencies

- T006/T008/T010 (tests) BEFORE T007/T009/T011 (implementation) — test-first order
- T007 blocks T009 and T011
- T013 only after T003 (baseline), T009 and T012 (labelled sample)
- MANUAL GATEs (T005, T014) require a human

## Validation Checklist

- [ ] Every FR has a task (FR-001→T007, FR-002→T006/T008/T010, FR-003→T009/T011, FR-004→T009, FR-005→T001, FR-006→T006/T007)
- [ ] Every SC has a gate (SC-001→T013, SC-002→T013, SC-003→T006/T008/T010, SC-004→T013)
- [ ] The tests are in place before the implementation
- [ ] Every task names a concrete file
