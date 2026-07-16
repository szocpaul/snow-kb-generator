# Feature Specification: Team-Based KB Templates

**Feature Branch**: `002-team-based-templates`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "Különböző csapatok vannak azok különböző struktúrájú KB Cikkeket várnak. Itt jönne be a különböző template használat. Minden csapat számára lenne egy amit tud használni a KB generálásra. Az AI feltudná ismerni az adott Story alapján melyik csapathoz melyik KB template tartozik, például Assignment Group alapján."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Template-Driven Generation (Priority: P1)

A developer completes a Story that belongs to a specific Assignment Group (e.g., "Network Team"). When generating the KB article, the system fetches the HTML structure/example defined for that team from the Knowledge Base configuration and uses it as a "gold standard" template. The generated article strictly follows the Network Team's required structure (e.g., Symptom, Cause, Resolution) rather than the generic default.

**Why this priority**: This delivers the core value of the feature—ensuring each team gets documentation in their preferred, specific format.

**Independent Test**: Can be fully tested by triggering generation on a Story with a valid Assignment Group and verifying the output matches the team's configured template structure.

**Acceptance Scenarios**:

1. **Given** a completed Story with `assignment_group=Network`, **When** the developer clicks "Create KB Article", **Then** the system retrieves the Network Team's template from the Knowledge Base `text` field and generates an article matching that specific structure.
2. **Given** the template contains an example "gold" article in the `text` field, **When** the generation completes, **Then** the resulting KB article mimics the formatting, headings, and tone of the provided example.

---

### User Story 2 - Missing Assignment Group Handling (Priority: P2)

A developer or the system attempts to generate a KB article for a Story where the `assignment_group` field is empty or invalid. Because the team context is mandatory for selecting the correct template, the system halts the process immediately and clearly informs the user that the team must be specified.

**Why this priority**: Prevents the generation of incorrectly formatted articles and enforces data hygiene (Assignment Group is mandatory).

**Independent Test**: Can be tested by clearing the Assignment Group on a Story and verifying the system returns a clear error without attempting a generic generation.

**Acceptance Scenarios**:

1. **Given** a completed Story with an empty `assignment_group`, **When** the developer clicks "Create KB Article", **Then** the system aborts the generation and displays a clear error message: "Cannot generate KB: Assignment Group is missing."
2. **Given** the generation was aborted due to missing team, **Then** no KB article is created or modified in the system.

---

### User Story 3 - Template Maintenance (Priority: P3)

A ServiceNow administrator or team lead wants to update the structure expected for their team's articles. They update the standard template/example directly within the ServiceNow Knowledge Base or Category configuration (specifically the description/metadata fields). The next time a developer generates an article for that team, the system automatically uses the newly updated template without requiring code changes or restarts.

**Why this priority**: Ensures the system is autonomous and maintainable by non-developers directly within ServiceNow.

**Independent Test**: Can be tested by modifying a Knowledge Base description in ServiceNow and verifying the next generation uses the new structure.

**Acceptance Scenarios**:

1. **Given** the administrator updates the template in the Knowledge Base `text` field, **When** a new Story is processed for that team, **Then** the pipeline fetches and uses the newly updated template dynamically.

### Edge Cases

- What happens if the Knowledge Base configuration has an empty `text` field/template? (The system falls back to a generic structure or warns that the template is missing).
- What happens if a team's template is excessively long? (It may consume too many tokens; the system should cap the template length passed to the AI).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST read the `assignment_group` field from the Story record before generation.
- **FR-002**: If `assignment_group` is empty or invalid, the system MUST abort the process and return a specific "Missing Assignment Group" error.
- **FR-003**: The system MUST fetch the corresponding team template (HTML structure/example) from the ServiceNow Knowledge Base configuration (`kb_knowledge_base` or `kb_category` `text` field).
- **FR-004**: The pipeline MUST pass the retrieved template to the AI generation step as a "Few-Shot" example, instructing the model to mimic the structure.
- **FR-005**: The final generated KB article MUST reflect the structure, headings, and formatting defined in the team's template.

### Key Entities *(include if feature involves data)*

- **Story (`rm_story`)**: The source record. The `assignment_group` field is now a critical input for routing the generation.
- **Knowledge Base Configuration (`kb_knowledge_base`/`kb_category`)**: Acts as the storage entity for team templates. The `text` field is leveraged to store the HTML template or example.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of generated articles for a specific team conform to that team's configured template structure.
- **SC-002**: Stories missing an Assignment Group are successfully blocked (0% attempt generic generation).
- **SC-003**: Template updates made in ServiceNow take effect in the generation pipeline dynamically (within the next execution), without code deployment.

## Assumptions

- The `assignment_group` field on the Story table is standard and points to a valid `sys_user_group` record.
- The pipeline can map an `assignment_group` to a specific Knowledge Base (`kb_knowledge_base`) or Category. (This mapping logic will be defined in the implementation plan).
- Storing the template HTML in the Knowledge Base `text` field is technically feasible and accessible via the ServiceNow Table API.
- The "Few-Shot" example provided by the template may increase the AI token usage slightly, which is acceptable for higher quality output.
