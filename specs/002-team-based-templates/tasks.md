# Tasks: Team-Based KB Templates

**Input**: Design documents from `/specs/002-team-based-templates/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included (Test-First/TDD per Constitution Principle III).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Update schemas and create custom exceptions to support the new routing logic.

- [X] T001 Create `MissingAssignmentGroupError` exception class in `src/snow_kb/errors.py`
- [X] T002 [P] Add `assignment_group` field to `StoryData` Pydantic model in `src/snow_kb/schemas.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ServiceNow client method to fetch the team-specific template via the `ownership_group` reference field.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Write failing tests for `get_team_template()` in `tests/test_servicenow_client.py` (queries `ownership_group`, returns `text` or None)
- [X] T004 Implement `get_team_template(assignment_group)` in `src/snow_kb/servicenow_client.py` (queries `kb_knowledge_base` where `ownership_group={sys_id}`)

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Template-Driven Generation (Priority: P1) 🎯 MVP

**Goal**: Fetch the correct team template and pass it dynamically to the DSPy pipeline (Few-Shot).

**Independent Test**: Trigger generation on a Story with a valid Assignment Group; verify output matches the team's template structure.

- [X] T005 [US1] Write failing tests in `tests/test_pipeline.py` verifying `get_team_template` is called and template is passed to the program
- [X] T006 [US1] Add `template_context` InputField to `DraftSections` and `FormatKB` Signatures in `src/snow_kb/signatures.py`
- [X] T007 [US1] Update `StoryToKBArticle.forward()` in `src/snow_kb/program.py` to accept and pass `template_context` to predictors
- [X] T008 [US1] Update `generate_kb_article()` in `src/snow_kb/pipeline.py` to fetch template and pass it to the program

---

## Phase 4: User Story 2 - Missing Assignment Group Handling (Priority: P2)

**Goal**: Block generation immediately if the Story's `assignment_group` is empty.

**Independent Test**: Clear the Assignment Group on a Story; verify generation is blocked with a specific error.

- [X] T009 [US2] Write failing tests in `tests/test_pipeline.py` verifying `MissingAssignmentGroupError` is raised when group is empty
- [X] T010 [US2] Update `generate_kb_article()` in `src/snow_kb/pipeline.py` to check `story.assignment_group` and raise the error
- [X] T011 [US2] Update `generate_kb` endpoint in `src/snow_kb/server.py` to catch `MissingAssignmentGroupError` and return HTTP 422

---

## Phase 5: User Story 3 - Template Maintenance (Priority: P3)

**Goal**: Ensure templates edited in ServiceNow are fetched dynamically without code changes.

**Independent Test**: Modify a KB `text` field in ServiceNow; verify the next generation uses the new structure.

- [X] T012 [US3] Write integration test in `tests/test_servicenow_client.py` verifying `get_team_template` always queries the live API (no hardcoding/caching)
- [X] T013 [US3] Update `servicenow/ui_action_script.js` to gracefully handle the HTTP 422 (Missing Group) response and display a user-friendly message

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation.

- [X] T014 Run full pytest suite (`pytest tests/ -q`) to ensure 185+ tests are green and no regressions
- [X] T015 Update `Agent.md` and `README.md` to document the team-based template feature and the `ownership_group` field requirement

---

## Dependencies

1. **Phase 2 (Foundation)** MUST complete before Phase 3, 4, or 5.
2. **Phase 3 (US1 - MVP)** is the core flow and deliverable on its own.
3. **Phase 4 (US2)** depends on the errors created in Phase 1 and pipeline logic from Phase 3.
4. **Phase 5 (US3)** validates dynamic fetching (depends on Phase 2 client method).

## Parallel Execution Examples

- T001 (errors) and T002 (schema) in Phase 1 are independent.
- Within US1, T006 (Signatures) and T007 (Program) touch related files but can be sketched in parallel before wiring in T008.

## Implementation Strategy

1. Establish the new `MissingAssignmentGroupError` and `assignment_group` schema (Setup).
2. Build the ServiceNow client template fetcher (Foundation).
3. Deliver the MVP (US1): dynamic Few-Shot generation based on team.
4. Add the strict blocking rule (US2) and UI error handling.
5. Verify dynamic updates work (US3) and finalize documentation.
