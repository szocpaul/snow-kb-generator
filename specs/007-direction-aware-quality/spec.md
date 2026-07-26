# Feature Specification: Direction-Aware KB Quality (Inbound/Outbound N/A Enforcement)

**Feature Branch**: `007-direction-aware-quality`

**Created**: 2026-07-26

**Status**: Draft (review pending — NOT implemented)

**Input**: User description: "In the case of an Outbound Story, the Inbound section of the generated article gets filled with content (and vice versa), although it should be N/A. The error must be fixed in 3 layers: (1) the metric must be direction-aware (the GEPA reflection must get a signal), (2) the signature must explicitly state the direction rule, (3) the GEPA run must use SkilledProposer with extra_guidance and anti-overfitting."

## Background (diagnosis)

- In the generated article of STRY0010010 (a purely outbound Story), the "Inbound Technical Implementation" section got filled with content (shared components, e.g. `JiraIntegrationUtils`, were placed there).
- The Story text gives a 100% outbound signal (0 inbound mentions); the gold examples of the gold dataset correctly show the N/A pattern.
- The current `template_adherence` axis only checks *whether* there is an N/A in the article — not *where* it should be. The feedback thus does not name the direction error → the problem is invisible to the reflection model (Kimi K3).
- The stock GEPA proposer encourages copying "niche factual information" (see the earlier KB0012345 hallucination) — the SkilledProposer (github.com/cmpnd-ai/skilled-proposer) structurally handles this with an anti-overfitting meta-prompt and `extra_guidance` control.

## User Scenarios & Testing

### User Story 1 - Direction-Aware Metric (Priority: P1)

The `rich_metric` detects the integration direction from story_text (inbound / outbound / both / unknown) and checks whether the inapplicable section (outbound story → Inbound Technical Implementation; inbound story → Outbound Technical Implementation) is "N/A". In case of an error the feedback is explicit: `"Direction violation: outbound story but 'Inbound Technical Implementation' section is filled with content."`

**Why this priority**: This is the sensor — without it, the GEPA reflection remains blind to the error.

**Independent Test**: Mock pred: outbound gold + filled Inbound section → decreased score + "Direction violation" feedback. Gold N/A pred → no penalty.

**Acceptance Scenarios**:

1. **Given** an outbound story_text and a filled Inbound section, **When** the metric runs, **Then** the template/direction axis < 1.0 and the feedback contains: "Direction violation".
2. **Given** an outbound story_text and an N/A Inbound section, **When** the metric runs, **Then** there is no penalty.
3. **Given** a "both" direction (both mentioned) or "unknown", **When** the metric runs, **Then** the direction check is skipped (no false positive).

---

### User Story 2 - Explicit Signature Rule (Priority: P2)

The instruction of the `GenerateKbFromTemplate` signature states categorically: "Determine the integration direction from the story. For an outbound-only story, the 'Inbound Technical Implementation' section MUST be exactly 'N/A' (and vice versa). Shared components belong to the direction the story implements."

**Acceptance Scenarios**:

1. **Given** the updated signature, **When** the program runs on an outbound story, **Then** the Inbound section is "N/A" (the shared components are in the Outbound section).

---

### User Story 3 - SkilledProposer Integration (Priority: P2)

The GEPA run uses `dspy.GEPA(instruction_proposer=SkilledProposer(...))`:
- `extra_guidance`: the direction rule + "never invent KB article numbers or titles" (lesson of spec 005)
- anti-overfitting meta-prompt (to trigger the stock "copy niche facts" behavior)
- optional: prompting-guide skill for the weak (35B) task model

**Acceptance Scenarios**:

1. **Given** a GEPA run, **When** the proposals are generated, **Then** the new instructions contain the direction rule (verifiable in the gepa_logs run_log.json).
2. **Given** the optimized program, **When** it runs on the valset, **Then** 0 direction violation according to the metric.

---

### User Story 4 - Re-optimization & E2E Validation (Priority: P3)

Baseline + GEPA re-run (clean `gepa_logs/`), export, server restart, production STRY0010010 validation: the Inbound section is "N/A", the Outbound section contains the shared components.

**Acceptance Scenarios**:

1. **Given** the production regeneration, **Then** there is no "Direction violation" in the article (verified with the ServiceNow API).
2. **Given** the full test suite, **Then** every test passes.

## Requirements

- **FR-001**: Direction detection: based on the occurrence of the "inbound"/"outbound" keywords in story_text (0 inbound + ≥1 outbound → outbound; vice versa → inbound; both → both; neither → unknown = check skipped).
- **FR-002**: The direction violation lowers the template_adherence axis (weights unchanged); the feedback is explicit and gives an actionable suggestion.
- **FR-003**: The signature's direction rule is categorical ("MUST be exactly 'N/A'"), and it also regulates the placement of shared components.
- **FR-004**: `skilled-proposer` pip package; `run_gepa_optimization()` uses the SkilledProposer (fallback: stock proposer, if the import fails — but that is a warning).
- **FR-005**: The behavior of the existing hallucination axis and guardrail is unchanged (no regression in spec 004/005).

## Success Criteria

- **SC-001**: Valset + production article: 0 direction violation.
- **SC-002**: The optimized score ≥ that of the previous run (0.850), ideally approaching gold consistency.
- **SC-003**: The full test suite is green (221+ new tests).

## Out of Scope

- The guardrail is a pipeline-level N/A enforcement (the metric + GEPA path is primary; if the error remains after GEPA, a separate spec).
- Other section-level content validations (e.g. the mandatory elements of the Testing Guide).
