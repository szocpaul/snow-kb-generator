# Feature Specification: KB Duplicate Prevention & Update

**Feature Branch**: `001-kb-duplicate-prevention`

**Created**: 2026-07-15

**Status**: Draft

**Input**: User description: "Szeretném, hogy a KB Cikkek ne duplikáltan jöjjenek létre."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - First-Time KB Generation (Priority: P1)

A developer completes a Story and clicks the "Create KB Article" button for the first time. The system detects that no Knowledge Base article is linked to this Story yet, so it generates a new article, publishes it, and links it to the Story by recording the Story's identifier on the article record.

**Why this priority**: This is the core MVP flow. It ensures the primary value (creating a KB article) continues to function while establishing the metadata needed for tracking.

**Independent Test**: Can be fully tested by triggering generation on a fresh Story and verifying a single KB article is created and linked.

**Acceptance Scenarios**:

1. **Given** a completed Story with no linked KB article, **When** the developer clicks "Create KB Article", **Then** the system generates exactly one new KB article and links it to the Story.
2. **Given** a KB article was just generated, **When** the developer views the Story's work notes, **Then** the link to the newly created article is visible.

---

### User Story 2 - Preventing Duplicate Creation (Priority: P2)

A developer clicks the "Create KB Article" button on a Story that already has a linked KB article. Instead of creating a duplicate, the system detects the existing article and prompts the developer with a confirmation dialog. If the developer cancels, no new article is created and the existing one remains untouched.

**Why this priority**: This directly solves the user's stated problem of duplicate articles cluttering the Knowledge Base.

**Independent Test**: Can be tested by clicking the button on an already-processed Story and verifying a duplicate is NOT created when the prompt is dismissed.

**Acceptance Scenarios**:

1. **Given** a Story with an existing linked KB article, **When** the developer clicks "Create KB Article" and selects "Cancel" in the confirmation dialog, **Then** the system aborts the operation and creates no new article.
2. **Given** a Story with an existing linked KB article, **When** the generation is aborted, **Then** the work notes reflect that the user chose not to regenerate.

---

### User Story 3 - Regeneration / Overwriting (Priority: P3)

A developer clicks the "Create KB Article" button on a Story that already has a linked KB article, but the content is outdated or incorrect. The system prompts the developer, and upon confirmation, the pipeline regenerates the content and updates the existing article record in place, preserving the original article's system identifier.

**Why this priority**: Provides flexibility and corrects mistakes without leaving orphaned/duplicate articles behind.

**Independent Test**: Can be tested by confirming the prompt on an existing article and verifying the article content updates without creating a second record.

**Acceptance Scenarios**:

1. **Given** a Story with an existing linked KB article, **When** the developer clicks "Create KB Article" and confirms the regeneration prompt, **Then** the system updates the content of the existing article.
2. **Given** the regeneration has completed, **When** the developer views the KB article, **Then** the article retains its original system identifier but displays the newly generated content.

### Edge Cases

- What happens if the `u_source_story` field is manually cleared from a KB article? (The system will treat it as unlinked and generate a new one).
- What happens if a Story is deleted but the linked KB article remains? (The article becomes orphaned; the link is lost, but the article persists).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST record the originating Story's identifier on the generated Knowledge Base article via a dedicated metadata field (`u_source_story`).
- **FR-002**: Prior to generation, the system MUST query the Knowledge Base to check if an article already exists where `u_source_story` matches the current Story's identifier.
- **FR-003**: If no existing article is found (First-Time Generation), the system MUST create a new article and link it.
- **FR-004**: If an existing article is found, the user interface MUST present a confirmation dialog asking whether to update the existing article.
- **FR-005**: If the user declines the confirmation dialog, the system MUST abort the generation process completely.
- **FR-006**: If the user accepts the confirmation dialog, the system MUST overwrite the content of the existing article record (same system identifier) with the newly generated content.
- **FR-007**: Upon successful generation or update, the system MUST update the Story's work notes with a link to the final KB article.

### Key Entities *(include if feature involves data)*

- **Knowledge Base Article (kb_knowledge)**: The generated document. Gains a new custom attribute (`u_source_story`) linking it to its origin Story.
- **Story (rm_story)**: The source of development context. Triggers the generation workflow.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A single Story can never result in more than one active Knowledge Base article in the system.
- **SC-002**: 100% of successful "Create KB Article" actions result in the Story being correctly linked to a KB article via the metadata field.
- **SC-003**: Users can successfully update/regenerate an existing article via the confirmation prompt without creating duplicate records.

## Assumptions

- The `u_source_story` custom field can be added to the `kb_knowledge` table in the ServiceNow instance.
- The pipeline has write access to update existing KB article records via the ServiceNow Table API (PATCH method).
- The UI Action script running on the Story form can execute the necessary logic to present a confirmation dialog to the user before invoking the backend pipeline.
- The ServiceNow instance allows outbound REST calls to the FastAPI server with sufficient timeout to accommodate both create and update operations.
