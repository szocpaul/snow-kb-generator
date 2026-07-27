# Feature Specification: Evidence-First KB Generation (Direction Violation as a Special Case)

**Feature Branch**: `007-direction-aware-quality` (merged spec 007+008)

**Created**: 2026-07-26

**Status**: Draft (review pending — NOT implemented)

**Input**: User description: "The template-filling architecture structurally forces hallucination: the gap between the mandatory template headings and the incomplete Story is filled in by the model with fabrications. Solution: 'evidence-first' — only the section the Story provides evidence for goes into the article; an unsupported section must NOT be N/A, it must be left out. The inbound/outbound direction violation is a special case of this (outbound story → Inbound section = unsupported section)."

## Background (diagnosis)

- The Inbound section of STRY0010010 (a purely outbound Story) was filled with content, even though the Story gives a 100% outbound signal and the gold examples show the correct N/A pattern.
- Root cause: the signature's "fill every section, do NOT remove headings" instruction + the local 35B model's weak adherence to conditional instructions + the metric's blindness to direction and supportedness (the feedback does not name the error → the Kimi K3 reflection is blind to it).
- Any incomplete Story produces the same pattern in any section — the direction violation is only the most conspicuous case.
- The stock GEPA proposer encourages copying "niche factual information" (see the KB0012345 hallucination) — we replace it with SkilledProposer with anti-overfitting control and `extra_guidance`.

## Core Principle

**"No evidence, no section."** From now on the template (KBA1–KBA11) is a *menu*, not a mandatory skeleton. The structure of the article follows the content of the Story; a missing section is at the same time an honest signal to the owner of the Story that the fields are incomplete.

## User Scenarios & Testing

### User Story 1 - Evidence-Aware Metric (Priority: P1)

The `rich_metric` gets two new checks:

1. **Direction violation (special case)**: direction detection on the story_text (inbound/outbound/both/unknown); outbound story + filled Inbound section (or the other way round) → penalty + explicit feedback: `"Direction violation: outbound story but 'Inbound Technical Implementation' section is filled."`
2. **Unsupported section penalty (general case)**: if a section is N/A/absent in the gold article but appears with content in the prediction → penalty + feedback: `"Unsupported section: '<h2>' has content but the gold article marks it N/A/absent."`

**Why this priority**: This is the sensor — GEPA reflection only fixes what the feedback names.

**Independent Test**: A mock prediction with a filled Inbound section + an outbound gold → "Direction violation" feedback; a mock prediction with N/A as per the gold → no penalty; a mock prediction with an extra heading → "Unsupported section" feedback.

**Acceptance Scenarios**:

1. **Given** an outbound story_text and a filled Inbound section, **When** the metric runs, **Then** the template axis < 1.0 and the feedback contains: "Direction violation".
2. **Given** an N/A/absent section in the gold article but filled in the prediction, **When** the metric runs, **Then** "Unsupported section" feedback.
3. **Given** a both/unknown direction, **When** the metric runs, **Then** the direction check is skipped (no false positive).

---

### User Story 2 - Evidence-First Signature (Priority: P1)

The `GenerateKbFromTemplate` instruction is reversed: "The html_template is a MENU, not a mandate. Include ONLY sections the story supports with concrete evidence. Omit unsupported sections entirely (do NOT write 'N/A' placeholders). Corollary: for an outbound-only story, omit 'Inbound Technical Implementation' (and vice versa); shared components belong to the direction the story implements."

**Acceptance Scenarios**:

1. **Given** an incomplete Story, **When** the generation completes, **Then** the article contains only the supported sections.
2. **Given** an outbound Story, **When** the generation completes, **Then** there is no Inbound section (neither N/A nor content).

---

### User Story 3 - Gold Dataset & Template Alignment (Priority: P2)

The example articles of the gold dataset switch to the evidence-first logic: fully N/A section blocks (e.g. the Inbound section in the outbound example) are **deleted** (they do not remain as N/A). The template files (md/html) stay unchanged — the template still contains the full menu.

**Acceptance Scenarios**:

1. **Given** the updated dataset, **When** we load it, **Then** the example articles contain no "N/A-only" section blocks.
2. **Given** the dataset tests, **When** they run, **Then** they pass (the structural validation is aligned with the updated expectation).

---

### User Story 4 - SkilledProposer Integration (Priority: P2)

The GEPA run uses `instruction_proposer=SkilledProposer(...)`:
- `extra_guidance`: "Include only sections the story supports; no evidence → omit the section entirely. For outbound-only stories omit the Inbound section (and vice versa). Never invent KB article numbers or titles."
- anti-overfitting meta-prompt; fallback to the stock proposer with a warning.

**Acceptance Scenarios**:

1. **Given** the GEPA run, **When** the proposals are produced, **Then** the instructions contain the evidence-first rule (gepa_logs run_log.json).
2. **Given** the optimized program, **When** it runs on the valset, **Then** 0 direction violations and 0 unsupported sections.

---

### User Story 5 - Re-optimization & E2E Validation (Priority: P3)

Baseline + GEPA re-run (clean `gepa_logs/`), export, server restart, production STRY0010010 validation: no Inbound section, the shared components in the Outbound section.

**Acceptance Scenarios**:

1. **Given** a production regeneration, **Then** the article, verified through the ServiceNow API, has 0 direction violations.
2. **Given** the full test suite, **Then** every test passes.

## Requirements

- **FR-001**: Direction detection: "inbound"/"outbound" keyword occurrence in the story_text (0 inbound + ≥1 outbound → outbound; the other way round → inbound; both → both; neither → unknown = check skipped).
- **FR-002**: The direction violation and the unsupported section degrade the template_adherence axis (weights unchanged); the feedback is explicit and suggests an action.
- **FR-003**: The signature is evidence-first: menu, not mandate; unsupported section OMITTED (not N/A).
- **FR-004**: Cleaning the gold dataset: deleting the N/A-only section blocks.
- **FR-005**: `skilled-proposer` pip package; fallback to the stock proposer with a warning.
- **FR-006**: The guardrails of spec 004/005 keep working unchanged.

## Success Criteria

- **SC-001**: Valset + production article: 0 direction violations, 0 unsupported sections.
- **SC-002**: Optimized score ≥ the previous run (0.850).
- **SC-003**: The full test suite is GREEN.

## Out of Scope

- Enforcing the sections with a pipeline guardrail (only if the metric+GEPA path is not enough — separate spec).
- A full LLM-based grounding metric (every statement checked against Story evidence) — later spec.
- Filtering the "KB article created:" self-reference in the work_notes (cleanup list).
