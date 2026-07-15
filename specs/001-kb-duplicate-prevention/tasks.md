# Tasks: KB Duplicate Prevention & Update

**Input**: Design documents from `/specs/001-kb-duplicate-prevention/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests are included (Test-First/TDD per Constitution Principle III).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Update schemas and client to support the new `u_source_story` linkage.

- [X] T001 Add `source_story` field to `KBArticle` Pydantic model in `src/snow_kb/schemas.py`
- [X] T002 Add `force_update: bool = False` field to `GenerateKBRequest` in `src/snow_kb/server.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: ServiceNow client methods to find and update existing KB articles (required by all user stories).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Write failing tests for `find_existing_kb_article()` in `tests/test_servicenow_client.py`
- [X] T004 Implement `find_existing_kb_article(story_number)` in `src/snow_kb/servicenow_client.py` (queries `u_source_story`)
- [X] T005 Write failing tests for PATCH behavior in `create_kb_article()` (when `existing_sys_id` provided) in `tests/test_servicenow_client.py`
- [X] T006 Modify `create_kb_article()` in `src/snow_kb/servicenow_client.py` to support PATCH update when `existing_sys_id` is passed, and set `u_source_story` on POST create

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - First-Time KB Generation (Priority: P1) 🎯 MVP

**Goal**: Generate a new article linked to the Story via `u_source_story` when none exists.

**Independent Test**: Trigger generation on a fresh Story; verify single KB article is created and linked.

- [X] T007 [US1] Write failing test in `tests/test_pipeline.py` for pipeline calling `create_kb_article` with `source_story` set when no existing article is found
- [X] T008 [US1] Update `generate_kb_article()` in `src/snow_kb/pipeline.py` to call `find_existing_kb_article()`, and if None, pass `source_story` to `create_kb_article`
- [X] T009 [US1] Verify work_notes update logic in `src/snow_kb/servicenow_client.py` still functions with the linked article

---

## Phase 4: User Story 2 - Preventing Duplicate Creation (Priority: P2)

**Goal**: Detect existing article and abort generation without user confirmation.

**Independent Test**: Click button on processed Story, cancel prompt, verify no API call or duplicate.

- [X] T010 [US2] Write failing test in `tests/test_server.py` verifying HTTP 409 Conflict when duplicate exists and `force_update=false`
- [X] T011 [US2] Update `generate_kb` endpoint in `src/snow_kb/server.py` to return 409 with existing article details when `force_update` is False
- [X] T012 [US2] Update `servicenow/ui_action_script.js` to handle 409 response gracefully (abort, do not create duplicate, show message)

---

## Phase 5: User Story 3 - Regeneration / Overwriting (Priority: P3)

**Goal**: Update existing article in place when user confirms regeneration.

**Independent Test**: Click button on processed Story, confirm prompt, verify existing article content updates without creating a second record.

- [X] T013 [US3] Write failing test in `tests/test_pipeline.py` verifying `create_kb_article` is called with `existing_sys_id` when `force_update=True`
- [X] T014 [US3] Update `generate_kb_article()` in `src/snow_kb/pipeline.py` to pass `existing_sys_id` to client when `force_update` is True and duplicate found
- [X] T015 [US3] Update `servicenow/ui_action_script.js` to send `force_update: true` in request body when user confirms the regeneration prompt

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation and documentation.

- [X] T016 Run full pytest suite (`pytest tests/ -q`) to ensure 173+ tests are green and no regressions
- [X] T017 Update `Agent.md` and `README.md` to document the duplicate prevention feature and the new `u_source_story` field requirement
- [ ] T018 Manual end-to-end validation against ServiceNow PDI per `specs/001-kb-duplicate-prevention/quickstart.md`

---

## Dependencies

1. **Phase 2 (Foundation)** MUST complete before Phase 3, 4, or 5.
2. **Phase 3 (US1 - MVP)** is independent and deliverable on its own.
3. **Phase 4 (US2)** and **Phase 5 (US3)** both depend on Phase 3 logic but can be developed in sequence (US2 handles the abort, US3 handles the confirm-update flow).

## Parallel Execution Examples

- Within Phase 2: T003 (tests for find) and T005 (tests for PATCH) can be written in parallel before their implementations.
- T001 (schema) and T002 (request model) in Phase 1 are independent.

## Implementation Strategy

1. Build the foundation (find + update client methods) with TDD.
2. Deliver the MVP (US1): basic linkage on first creation.
3. Add the duplicate detection (US2) and update flow (US3) incrementally.
4. Finish with full regression testing and live ServiceNow validation.
