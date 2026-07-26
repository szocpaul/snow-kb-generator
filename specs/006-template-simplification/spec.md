# Feature Specification: Template Simplification (Audience as Style, Not Section)

**Feature Branch**: `006-template-simplification`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "Remove from the template: the 'Knowledge Base Structure for Interface Documentation' main title, the 'Theme' rows, and the 'Target Audience' sections (including the 3rd column of the related articles table). The audience, however, shall remain as a STYLE: the content of each section shall be phrased in language appropriate to the target audience, without the Target Audience explicitly appearing in the article."

## User Scenarios & Testing

### User Story 1 - Simplified Template (Priority: P1)

Stripping down the template (the local `integration_team_template.md/.html` + the "Structure" article live in ServiceNow): the KBA1-KBA11 sections consist of a heading and a Content list only. No H1 main title, no Theme row, no Target Audience section, and the related articles table has 2 columns (Short description + Article number).

**Acceptance Scenarios**:

1. **Given** the new template, **When** we load it, **Then** it contains no "Theme:" line, no "Target Audience" section and no H1 main title; the KBA1-KBA11 headings remain.
2. **Given** the template article live in ServiceNow, **When** `get_team_template()` fetches it, **Then** it returns the updated, simplified HTML.

### User Story 2 - Audience as Writing Style (Priority: P1)

The program still extracts the target audience (ExtractChange.audience) and receives it as a style instruction in the template-generation step: "Write for {audience}, but do NOT include a Target Audience section."

**Acceptance Scenarios**:

1. **Given** a Story with a developer target audience, **When** the generation completes, **Then** the article has a technical tone but contains no "Target Audience" section.
2. **Given** the updated gold dataset, **When** the dataset tests run, **Then** the example articles do not contain the removed elements either.

### User Story 3 - Dataset + Re-optimization (Priority: P2)

Cleaning the gold dataset's 5 example articles (delete the H1, the Theme, the Target Audience and the 3rd column), baseline + GEPA re-run, production validation.

**Acceptance Scenarios**:

1. **Given** the new dataset, **When** GEPA runs, **Then** the optimized program generates according to the new template.
2. **Given** production STRY0010010, **When** we regenerate it, **Then** the article has no Theme/Target Audience/H1 structure title, and the related table has 2 columns.

## Requirements

- **FR-001**: The KBA1-KBA11 structure of the template remains (heading + Content), all other meta-elements are removed.
- **FR-002**: The related articles table has 2 columns (Short description | Article number).
- **FR-003**: The `GenerateKbFromTemplate` signature instruction is extended: the audience is a style, not a section.
- **FR-004**: The gold dataset and the local template files are in sync with the new structure.
- **FR-005**: The `text` field of the template article live in ServiceNow is updated (Table API PATCH).
