# Tasks: GEPA Optimization for KB Article Quality

**Input**: Design documents from `/specs/003-gepa-kb-quality/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included (Test-First/TDD per Constitution Principle III).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the eval/ directory structure and load the gold dataset with validation.

- [X] T001 Create `eval/` directory structure (`eval/__init__.py`, `eval/dataset.py`, `eval/metric.py`, `eval/baseline.py`, `eval/gepa_optimize.py`)
- [X] T002 [P] Write failing tests for `load_gold_dataset()` in `tests/test_eval_dataset.py` (parses gold_dataset.md, returns 5 examples with story_text + expected_html)
- [X] T003 Implement `load_gold_dataset()` in `eval/dataset.py` (parses markdown, splits into trainset 3 / valset 2 as dspy.Example objects)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement the rich_metric contract (score + feedback) required by GEPA.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Write failing tests for `rich_metric()` in `tests/test_eval_metric.py` (returns dspy.Prediction with score float and feedback str)
- [X] T005 Implement `rich_metric()` in `eval/metric.py` (multi-axis score: structure_match, content_accuracy, template_adherence; natural-language feedback)
- [X] T006 [P] Write failing tests for baseline evaluation integration in `tests/test_eval_baseline.py` (dspy.Evaluate(devset=valset, metric=rich_metric) returns EvaluationResult)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Gold Dataset Preparation (Priority: P1) 🎯 MVP

**Goal**: Load and validate the 5 gold example pairs (Story → KB article) for training and validation.

**Independent Test**: Load gold_dataset.md and verify 5 complete examples are parsed into trainset (3) and valset (2).

- [ ] T007 [US1] Validate dataset in `eval/dataset.py` (each example has complete Story fields and expected_html following KBA1-KBA11)
- [ ] T008 [US1] Add dataset validation error handling in `eval/dataset.py` (abort with clear error if malformed/incomplete)

---

## Phase 4: User Story 2 - Baseline Performance Measurement (Priority: P2)

**Goal**: Measure the current (unoptimized) program's performance on the valset (score + feedback).

**Independent Test**: Run the current program on the valset and verify metric returns score + feedback per example.

- [ ] T009 [US2] Implement baseline evaluation in `eval/baseline.py` (dspy.Evaluate(devset=valset, metric=rich_metric, num_threads=1))
- [ ] T010 [US2] Save baseline results to `runs/baseline.json` in `eval/baseline.py` (average_score, per_example feedback, timestamp)

---

## Phase 5: User Story 3 - Automated Prompt Optimization (Priority: P3)

**Goal**: Run GEPA optimization using Kimi K3 reflection model to improve Signature instructions.

**Independent Test**: Run GEPA on trainset and verify reflection model produces concrete improvement suggestions applied to Signatures.

- [ ] T011 [US3] Implement GEPA optimizer in `eval/gepa_optimize.py` (dspy.GEPA(metric, auto="light", reflection_lm=Kimi K3, candidate_selection_strategy="pareto", track_stats=True, log_dir="./gepa_logs"))
- [ ] T012 [US3] Run GEPA compile in `eval/gepa_optimize.py` (optimizer.compile(student=program, trainset=trainset, valset=valset))
- [ ] T013 [US3] Extract applied suggestions in `eval/gepa_optimize.py` (from optimizer.detailed_results, list of concrete reflection suggestions)

---

## Phase 6: User Story 4 - Optimized Program Export and Deployment (Priority: P4)

**Goal**: Save the optimized program and ensure FastAPI server loads it for production use.

**Independent Test**: Save optimized program to artifacts/program.json, restart FastAPI server, verify it uses optimized program.

- [ ] T014 [US4] Save optimized program in `eval/gepa_optimize.py` (optimized.save("artifacts/program.json", save_program=False))
- [ ] T015 [US4] Update FastAPI server in `src/snow_kb/server.py` (load optimized program from artifacts/program.json on startup, fallback to StoryToKBArticle if missing)
- [ ] T016 [US4] Update pipeline in `src/snow_kb/pipeline.py` (accept optional program_path parameter to load optimized program)

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation.

- [ ] T017 Run full pytest suite (`pytest tests/ -q`) to ensure 190+ tests are green and no regressions
- [ ] T018 Update `Agent.md` and `README.md` to document the GEPA optimization feature and the new eval/ module structure
- [ ] T019 Manual end-to-end validation per `specs/003-gepa-kb-quality/quickstart.md` (load dataset → baseline → GEPA → export → restart server → test)

---

## Dependencies

1. **Phase 2 (Foundation)** MUST complete before Phase 3, 4, or 5.
2. **Phase 3 (US1 - MVP)** is the core data layer and deliverable on its own.
3. **Phase 4 (US2)** depends on the metric from Phase 2 and dataset from Phase 3.
4. **Phase 5 (US3)** depends on the baseline from Phase 4 and trainset from Phase 3.
5. **Phase 6 (US4)** depends on the optimized program from Phase 5.

## Parallel Execution Examples

- T002 (dataset tests) and T004 (metric tests) can be written in parallel before their implementations.
- T005 (metric impl) and T006 (baseline test) touch related files but can be sketched in parallel before wiring.

## Implementation Strategy

1. Build the gold dataset loading and validation (Setup + US1).
2. Implement the rich_metric contract (Foundation + US2) — the GEPA superpower.
3. Run the baseline evaluation (US2) to establish the starting point.
4. Run GEPA optimization (US3) with Kimi K3 reflection.
5. Export and deploy the optimized program (US4) via FastAPI.
6. Finish with full regression testing and live validation (Polish).
