# Tasks: Audience Decision with Calibrated Confidence

**Input**: Design documents from `/specs/013-audience-typed-decision/`
**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can be run in parallel (different file, no dependency)
- **[USn]**: which user story it belongs to
- **MANUAL GATE**: human decision — the runner/agent MUST NOT tick it

## Phase 1: Setup

- [x] T001 [P] Add the `typesafe-sdk` dependency to `pyproject.toml` and `requirements.txt` (the package is on the public PyPI, an extra index is NOT needed) + the `dspy[typesafe]` extra for the `ReAnchor` optimizer (calibration, see T012); `TYPESAFE_API_KEY` into `.env.example` and into the `Environment=` line of the systemd unit (under deploy/)
- [x] T002 [P] Config extension in `config.yaml`: `audience_decision.enabled`, `audience_decision.model` (pinned version), `audience_decision.confidence_threshold` (starting value: 0.7), `audience_decision.recording_path` — + a test for the config parsing

## Phase 2: Baseline (US1 precondition — playbook: baseline first)

- [x] T003 [US1] Baseline recording: the audience decisions of the current (generative) model on the 9 gold examples, per-example JSON under `data/` or `artifacts/` — unchanged code, recorded conditions
- [x] T004 [US1] Verification of the gold audience labels: can the correct audience be derived from the style of the 9 gold articles; if not, manual labelling and committing the labels next to the dataset
- [x] T005 [US1] **MANUAL GATE**: review of the baseline result and the labels — the runner MUST NOT tick it *(APPROVED 2026-09-29: the label evidence is strong, see Agent.md §42)*

## Phase 3: US1 – Decision with confidence (test first)

- [x] T006 [US1] Test: `tests/test_audience_decision.py` — mock story for an unambiguous developer case (high confidence) and for an edge case (lower confidence), with a mocked SDK response; fail-open test with a simulated SDK exception. The tests must FAIL before the implementation
- [x] T007 [US1] `src/snow_kb/audience.py` — `decide_audience(story_text) -> dict` (choice, probabilities, confidence); TypeSafe Choice call with the three options; JSONL recording (request hash, response, latency, model identifier — following the jev-dspy-lab format); error/timeout → fail-open to the existing generative path, warning log
- [x] T008 [US1] Wiring into `pipeline.py`: the audience comes from `decide_audience` (switchable off with a config flag), the `change_summary`/`key_steps` stay from the DSPy program as before — after T006 and T007

## Phase 4: US2 – Handling low confidence (test first)

- [x] T009 [US2] Test: low confidence → audience="developer" + work_notes note with the measured value; above the threshold → no note; exactly at the threshold → fallback (`<`, not `<=`)
- [x] T010 [US2] Threshold logic in `src/snow_kb/audience.py` + work_notes note on the write path of `servicenow_client.py` — after T007
- [x] T011 [US2] **MANUAL GATE**: approval of the fail-open + developer-default tradeoff before the production run (plan.md Key Decisions 4 and 6) — the runner MUST NOT tick it *(APPROVED 2026-09-29: during the run the mechanism behaved as specified, see Agent.md §42)*

## Phase 5: Measurement, calibration, closure

- [x] T012 [US1] Calibration measurement: live recording on the gold + mock sample with a pinned model, offline replay. **The primary calibration tool is the `ReAnchor` optimizer** (`dspy.experimental`, from the `dspy[typesafe]` extra): since ReAnchor optimizes a `dspy.Predict` module (not a direct SDK call), the measurement uses an **evaluation-only DSPy wrapper** that mirrors the T007 decision call (the same three options + the `desc` question, with the TypeSafe LM, pinned version); ReAnchor tunes the `threshold` on it without LLM calls (one run + cached probabilities). The resulting threshold goes into `audience_decision.confidence_threshold` in `config.yaml`, which the T007/T010 direct SDK path reads — the production call does NOT become a DSPy module. The gate is given by the jev-dspy-lab metrics (selective risk, coverage, ECE with the calibrated threshold) → SC-001/SC-002 gate with exit code; SC-003 via the T006 fail-open test; SC-004 byte-identical double replay — `cache=False` / replay mode, the measurement must actually run
- [x] T013 **MANUAL GATE**: review of the SC gate results; if the threshold changes, the rationale goes into the Agent.md — the runner MUST NOT tick it *(CLOSED 2026-09-29: path C — the threshold STAYS at 0.7, interim production, SC-002 restart condition = the gold dataset extended with ≥20 helpdesk examples; rationale in Agent.md §42)*
- [x] T014 Closure: the full pytest suite (286 + new tests) green, log entry in the Agent.md (facts, decisions, lessons learned), commit + push, backlog update (the status of the verification-layer spec's restart condition)

## Dependencies

- T006/T009 (tests) come FIRST, before T007/T010 (implementation) — test-first order
- T007 blocks T008 and T010
- T012 only after T003 (baseline) and T008
- MANUAL GATEs (T005, T011, T013) require a human

## Validation Checklist

- [ ] Every FR has a task (FR-001→T006/T007, FR-002→T002, FR-003→T007, FR-004→T008)
- [ ] Every SC has a gate (SC-001/SC-002→T012, SC-003→T006, SC-004→T012)
- [ ] The tests are in place before the implementation
- [ ] Every task names a concrete file
