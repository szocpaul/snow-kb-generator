# Implementation Plan: KB Duplicate Prevention & Update

**Branch**: `001-kb-duplicate-prevention` | **Date**: 2026-07-15 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-kb-duplicate-prevention/spec.md`

## Summary

The pipeline currently creates a brand-new KB article on every "Create KB Article" button press, leading to duplicates. To prevent this, the system will introduce an `u_source_story` metadata field on the KB article record linking it to its originating Story. The pipeline will query this field before generation; if an article exists, it will update the existing record (regeneration) rather than creating a new one, gated by a user confirmation prompt in the UI Action.

## Technical Context

**Language/Version**: Python 3.12 (DSPy pipeline) + ServiceNow server-side JavaScript (GlideRecord/RESTMessageV2)

**Primary Dependencies**: DSPy 3.2.x, FastAPI, Pydantic v2, ServiceNow Table API (`requests`)

**Storage**: ServiceNow (`kb_knowledge`, `rm_story` tables) + `u_source_story` custom field

**Testing**: pytest (173-test baseline, must stay green; LM/HTTP mocked)

**Target Platform**: Hetzner VPS (FastAPI server) + ServiceNow instance (`kb_knowledge` table modifications)

**Project Type**: web-service (AI pipeline with HTTP webhook)

**Performance Goals**: Generation request completes within the existing 120-second timeout.

**Constraints**: External LM and ServiceNow calls must be mocked in tests (Constitution Principle III). All ServiceNow access must flow through `servicenow_client.py` (Constitution Principle V).

**Scale/Scope**: Single new field on `kb_knowledge`, modification to `create_kb_article` method, UI Action script update.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Spec-Driven Pipeline Arch)**: ✅ PASS. Changes target `servicenow_client.py` (API isolation), `pipeline.py` (orchestration), and `server.py` (transport). No LLM prompting logic added to transport.
- **Principle II (DSPy-First)**: ✅ PASS. No new Signatures required for this feature; it's an orchestration/metadata change.
- **Principle III (Test-First)**: ✅ PLANNED. New behavior (check-before-create, update-if-exists) will be developed test-first with mocked ServiceNow responses.
- **Principle IV (Secrets Hygiene)**: ✅ PASS. No new secrets introduced.
- **Principle V (ServiceNow API Isolation)**: ✅ PASS. The `u_source_story` query and PATCH update will be encapsulated entirely within `ServiceNowClient`.

No violations. Complexity Tracking table omitted.

## Project Structure

### Documentation (this feature)

```text
specs/001-kb-duplicate-prevention/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── servicenow-kb-api.md  # Interface contract for the new KB update behavior
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/snow_kb/
├── servicenow_client.py  # Modified: find_existing_kb_article(), update create_kb_article()
├── pipeline.py           # Modified: GenerateKbRequest gains force_update flag
├── server.py             # Modified: Pass through force_update flag
└── schemas.py            # Modified: KBArticle gains source_story field

servicenow/
└── ui_action_script.js   # Modified: Confirmation dialog logic before REST call

tests/
├── test_servicenow_client.py  # New tests for find/update logic
├── test_pipeline.py           # New tests for force_update flow
└── test_server.py             # New tests for request parsing
```

**Structure Decision**: Existing single-package structure (`src/snow_kb/`) is retained. This feature modifies existing modules in place rather than introducing new top-level packages, adhering to Constitution Principle I (modular replacement).
