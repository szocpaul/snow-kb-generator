# Feature Specification: GEPA Optimization for KB Article Quality

**Feature Branch**: `003-gepa-kb-quality`

**Created**: 2026-07-16

**Status**: Draft

**Input**: User description: "GEPA Optimalizáció a KB cikk generáláshoz. A rendszer a meglévő KB sablonok (Integration Team Template) és 5 arany példapár (gold_dataset.md) alapján automatikusan javítja a DSPy promptokat a Kimi K3 reflection modellel."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gold Dataset Preparation (Priority: P1)

A user wants to improve the quality of KB articles generated from Stories. They provide a set of "gold standard" example pairs (Story → perfect KB article) based on the Integration Team Template. The system loads these 5 examples and prepares them for training and validation.

**Why this priority**: Without high-quality reference examples, the system has no objective way to measure or improve quality. This is the foundation of all optimization.

**Independent Test**: Can be tested by loading the gold_dataset.md file and verifying that 5 complete example pairs (Story + expected KB article) are correctly parsed into trainset and valset splits.

**Acceptance Scenarios**:

1. **Given** the gold_dataset.md file exists in `data/examples/`, **When** the system loads the dataset, **Then** all 5 examples are correctly parsed into trainset (3 examples) and valset (2 examples) with no data loss.
2. **Given** the dataset is loaded, **When** the system validates the examples, **Then** each example contains a complete Story (number, description, acceptance_criteria, technical_specification, work_notes, comments, state, assignment_group) and a matching KB article (HTML structure following KBA1-KBA11).

---

### User Story 2 - Baseline Performance Measurement (Priority: P2)

Before any optimization, the user wants to know how good the current (unoptimized) KB generation pipeline is. The system runs the existing program against the valset and produces a numeric score and detailed feedback for each example.

**Why this priority**: "No baseline, no claim" (Constitution Principle). Without a measurable starting point, we cannot prove that optimization actually improved anything.

**Independent Test**: Can be tested by running the current StoryToKBArticle program on the valset and verifying that the metric returns a dspy.Prediction with score (0-1) and natural-language feedback for each example.

**Acceptance Scenarios**:

1. **Given** the valset is prepared, **When** the system runs the current program against it, **Then** a rich_metric is computed for each example, returning a score (0-1) and detailed feedback (e.g., "Missing 'Target Audience' section", "Structure matches template").
2. **Given** the baseline is measured, **When** the results are saved, **Then** the average score and per-example feedback are written to `runs/baseline.json` for auditability.

---

### User Story 3 - Automated Prompt Optimization (Priority: P3)

The user wants the system to automatically improve the KB generation prompts (Signatures) using the reflection model (Kimi K3). The system runs the optimization process, where the reflection model reads the metric feedback from the baseline and suggests concrete improvements to the Signature instructions.

**Why this priority**: This is the core value of the feature—leveraging AI to automatically improve AI-generated content quality without manual prompt engineering.

**Independent Test**: Can be tested by running the optimization process on the trainset and verifying that the reflection model produces at least one concrete improvement suggestion (e.g., "Add instruction to preserve 'Target Audience' section") that gets applied to the Signatures.

**Acceptance Scenarios**:

1. **Given** the trainset and baseline feedback exist, **When** the optimization runs, **Then** the reflection model (Kimi K3) analyzes the feedback and proposes specific changes to the Signature instructions (e.g., to better handle missing information with "N/A").
2. **Given** the optimization completes, **When** the optimized program is compared to baseline, **Then** the optimized program achieves a higher average score on the valset than the baseline.

---

### User Story 4 - Optimized Program Export and Deployment (Priority: P4)

After optimization, the user wants to save the improved program and use it in production. The system exports the optimized program to a file, and the FastAPI server loads this optimized version instead of the original one for future KB generation.

**Why this priority**: Optimization is useless if the improved program isn't actually used in production. Export and deployment ensure the value is realized.

**Independent Test**: Can be tested by saving the optimized program to `artifacts/program.json` and verifying that the FastAPI server loads it on startup, and generates KB articles using the optimized Signatures.

**Acceptance Scenarios**:

1. **Given** the optimization is complete, **When** the program is saved, **Then** the optimized program is written to `artifacts/program.json` (state-only format, portable).
2. **Given** the FastAPI server restarts, **When** it loads the program, **Then** it uses the optimized program (with improved Signatures) for all subsequent KB generation requests.

### Edge Cases

- What happens if the gold dataset is malformed or incomplete? (The system validates the dataset and aborts with a clear error).
- What happens if the reflection model (Kimi K3) is unavailable or hits a usage limit? (The system gracefully degrades and reports the error without crashing).
- What happens if the optimized program performs worse than baseline? (The system keeps the original program and reports that optimization did not improve quality).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST load the 5 gold example pairs from `data/examples/gold_dataset.md` and split them into trainset (3 examples) and valset (2 examples).
- **FR-002**: The system MUST validate that each example contains a complete Story and a matching KB article (HTML structure following the Integration Team Template).
- **FR-003**: The system MUST compute a rich_metric (score + natural-language feedback) for each valset example by comparing the generated KB article to the expected gold article.
- **FR-004**: The system MUST run the current (unoptimized) program on the valset and save the results (average score, per-example feedback) to `runs/baseline.json`.
- **FR-005**: The system MUST use the reflection model (Kimi K3) to analyze the baseline feedback and propose concrete improvements to the Signature instructions.
- **FR-006**: The system MUST apply the reflection suggestions to the Signatures and produce an optimized program.
- **FR-007**: The optimized program MUST achieve a higher average score on the valset than the baseline program (or the system reports that no improvement was achieved).
- **FR-008**: The system MUST save the optimized program to `artifacts/program.json` (state-only format) and ensure the FastAPI server loads it on startup.

### Key Entities *(include if feature involves data)*

- **Gold Dataset**: 5 example pairs (Story → expected KB article) stored in `data/examples/gold_dataset.md`, used for training and validation.
- **Baseline**: The numeric score and feedback of the current (unoptimized) program on the valset, saved to `runs/baseline.json`.
- **Optimized Program**: The improved program with better Signatures, saved to `artifacts/program.json` and loaded by the FastAPI server.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The optimized program achieves a measurable improvement in average score on the valset compared to the baseline (e.g., from 0.65 to 0.85, or at least +0.1 improvement).
- **SC-002**: The reflection model (Kimi K3) provides at least one concrete, actionable suggestion per optimization round that gets applied to the Signatures (e.g., "Preserve 'Target Audience' section", "Use 'N/A' for missing sections").
- **SC-003**: The optimized program is successfully saved to `artifacts/program.json` and loads correctly in the FastAPI server, generating KB articles with the improved Signatures.

## Assumptions

- The gold dataset (`gold_dataset.md`) is well-formed and contains 5 complete example pairs following the Integration Team Template structure (KBA1-KBA11).
- The reflection model (Kimi K3) is available and has sufficient usage quota for the optimization process (which may require multiple rounds).
- The current KB generation pipeline (StoryToKBArticle) is functional and can be measured on the valset without errors.
- The FastAPI server can be restarted to load the optimized program from `artifacts/program.json`.
- The metric feedback from the reflection model is specific enough to guide concrete improvements to the Signature instructions.
