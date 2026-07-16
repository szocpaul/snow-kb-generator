# Implementation Plan: Team-Based KB Templates

**Branch**: `002-team-based-templates` | **Date**: 2026-07-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-team-based-templates/spec.md`

## Summary

The pipeline currently generates KB articles using a single, generic structure. To support different teams (Network, IT Support, HR) requiring distinct article structures, the system will read the Story's `assignment_group`, fetch the team's specific HTML template from the ServiceNow KB Knowledge Base `text` field, and inject it dynamically into the DSPy generation pipeline as a "Few-Shot" example. If the `assignment_group` is missing, generation is blocked.

## Technical Context

**Language/Version**: Python 3.12 (DSPy pipeline) + ServiceNow REST API (Table API for fetching templates)

**Primary Dependencies**: DSPy 3.2.x, Pydantic v2, ServiceNow Table API (`requests`)

**Storage**: ServiceNow (`kb_knowledge_base` `text` field stores team templates; `rm_story` `assignment_group` routes them)

**Testing**: pytest (mocked ServiceNow responses for template fetching)

**Target Platform**: Hetzner VPS (FastAPI server)

**Project Type**: web-service (AI pipeline)

**Performance Goals**: Fetching the template should add < 1 second to the overall generation time.

**Constraints**: External LM and ServiceNow calls must be mocked in tests (Constitution Principle III). All ServiceNow access must flow through `servicenow_client.py` (Constitution Principle V). The template must be passed as a dynamic input, not hardcoded (Constitution Principle II).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Principle I (Spec-Driven Pipeline Arch)**: ✅ PASS. The pipeline fetches the template via the ServiceNow client and passes it through the DSPy module structure. No logic in transport.
- **Principle II (DSPy-First)**: ✅ PASS. The team template is passed as a dynamic `InputField` to the DSPy Signature (`DraftSections` or `FormatKB`), instructing the LM to mimic it. This is idiomatic DSPy few-shot, not prompt hardcoding.
- **Principle III (Test-First)**: ✅ PLANNED. New methods (fetch template, validate group) and the missing group error will be developed test-first.
- **Principle IV (Secrets Hygiene)**: ✅ PASS. No new secrets.
- **Principle V (ServiceNow API Isolation)**: ✅ PASS. All KB template fetching encapsulated in `servicenow_client.py`.

No violations. Complexity Tracking table omitted.

## Project Structure

### Documentation (this feature)

```text
specs/002-team-based-templates/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── team-template-mapping.md  # How assignment_group maps to templates
└── tasks.md             # Phase 2 output (/speckit.tasks command)
```

### Source Code (repository root)

```text
src/snow_kb/
├── servicenow_client.py  # Modified: get_team_template(assignment_group) method
├── schemas.py            # Modified: StoryData gains assignment_group field
├── signatures.py         # Modified: DraftSections/FormatKB gains template_context InputField
├── program.py            # Modified: Pass template_context through the pipeline
├── pipeline.py           # Modified: Fetch template before generation, block if no group
└── errors.py             # NEW: MissingAssignmentGroupError

servicenow/
└── ui_action_script.js   # Modified: Handle "Missing Assignment Group" HTTP 422 response

tests/
├── test_servicenow_client.py  # New tests for get_team_template
├── test_pipeline.py           # New tests for missing group blocking
└── test_signatures.py         # Update for new InputField
```

**Structure Decision**: Existing single-package structure retained. A new `errors.py` module is introduced for custom pipeline exceptions to keep `pipeline.py` clean.
