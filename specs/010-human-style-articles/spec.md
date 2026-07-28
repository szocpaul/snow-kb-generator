# Feature Specification: Human-Written Style for Generated KB Articles

**Feature Branch**: `010-human-style-articles`

**Created**: 2026-07-28

**Status**: Draft

**Input**: User description: "The finished KB articles look very AI-written, not human enough. The structure and the facts are fine, but the tone is robotic: boilerplate phrases ('This document describes', 'seamless', 'leverage'), uniform sentence rhythm, generalizations instead of specifics. The goal: the articles should read as if a senior engineer had written them — the hand-written STYLE-REF is the style reference."

## Background (diagnosis)

- The `rich_metric` currently measures 4 axes (structure, content, template, hallucination) — **not style**. The basic law of GEPA: it only fixes what the metric sees. Therefore the robotic tone is invisible to the optimization.
- The STYLE-REF (hand-written SolMan article) is already present in the gold dataset — this is the human style sample to compare against.
- Since the Kimi-direct architecture, the task model is strong (0.655 baseline), so the style is the only remaining quality gap.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tone Guidance in Signature (Priority: P1, "free" step)

The `GenerateKbFromTemplate` docstring is extended with a SINGLE style block (boilerplate ban list + human tone). IMPORTANT: we do NOT touch the existing instruction text — the consolidation/shortening of the docstring is the subject of a SEPARATE spec (the length increase is an accepted transitional state).

**Why this priority**: An immediate, zero-cost improvement — before measuring anything, the prompt should not ask for the robotic style in the first place.

**Independent Test**: One generation on STRY0010010, and a human review: the banned phrases do not appear.

**Acceptance Scenarios**:

1. **Given** the updated signature, **When** the pipeline generates an article, **Then** the output does not contain the elements of the ban list ("This document describes", "seamless", "leverage", "In today's fast-paced world").
2. **Given** the same Story, **When** we compare the old and the new article, **Then** the new one contains fewer generic phrases and more specifics (field name, endpoint, value).

---

### User Story 2 - Style Judge in Metric (Priority: P2)

The fifth axis of `rich_metric`: an **LLM-as-judge** (Kimi K3) that evaluates on a 0-1 scale whether the article speaks in a human expert tone, and gives concrete criticism ("which phrase is robotic and why"). The judge prompt contains the STYLE-REF as a positive style sample.

**Why this priority**: This makes style *measurable* — from this point on GEPA sees it and can optimize it.

**Independent Test**: Two mock articles — one robotic (full of boilerplate) and one human — the judge rates the robotic one significantly lower, and the feedback names the concrete problems.

**Acceptance Scenarios**:

1. **Given** a robotic article (full of banned phrases), **When** the style judge runs, **Then** the style score < 0.4 and the feedback contains a concrete example.
2. **Given** an article with a human tone, **When** the judge runs, **Then** the style score > 0.7.
3. **Given** the metric weights, **When** the style axis is added, **Then** the total score is updated with the weighting (structure 0.25 + content 0.25 + template 0.15 + hallucination 0.15 + style 0.20), and the existing tests are aligned and pass.

---

### User Story 3 - Small-Budget GEPA on Style (Priority: P3)

Small-budget GEPA run (~250 metric call) with the Kimi task model, whose sole purpose is to demonstrate the style improvement: the style axis average should improve on the valset.

**Why this priority**: It only makes sense after the style has been measured — and with a limited quota (the rollouts are Kimi calls).

**Acceptance Scenarios**:

1. **Given** a GEPA run, **When** it completes, **Then** the optimized program's style average > baseline style average (measured in runs/*.json).
2. **Given** the optimized program, **When** a production STRY0010010 generation happens, **Then** according to a human review the article is less robotic than the previous version.

---

### User Story 4 - Small-Budget GEPA on Style (Priority: P3)

Small-budget GEPA run (~250 metric call) with the Kimi task model, whose sole purpose is to demonstrate the style improvement: the style axis average should improve on the valset.

**Why this priority**: It only makes sense after the style and the style-aware proposer — and with a limited quota (the rollouts are Kimi calls).

**Acceptance Scenarios**:

1. **Given** a GEPA run, **When** it completes, **Then** the optimized program's style average > baseline style average (measured in runs/*.json).
2. **Given** the optimized program, **When** a production STRY0010010 generation happens, **Then** according to a human review the article is less robotic than the previous version.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The style rules of the signature do NOT degrade the existing behaviour (evidence-first, template conformance, the guardrails are untouched).
- **FR-002**: The style judge is deterministically error-tolerant: if the judge call goes astray, the style axis is 0.5 (neutral) plus a warning — the metric never stops because of it.
- **FR-003**: The judge prompt contains the ban list and the STYLE-REF reference excerpt.
- **FR-004**: The GEPA run stays at `max_metric_calls <= 300` (quota protection).
- **FR-005**: `run_gepa_optimization()` creates the SkilledProposer with the style-focused `additional_instructions`; the existing evidence-first and KB-hallucination rules remain.

### Success Criteria

- **SC-001**: 0 banned phrases in the production articles (also measurable with an automatic regex check).
- **SC-002**: The style judge is validated (robotic < 0.4, human > 0.7 on the test icons).
- **SC-003**: Human review: the final articles "look human" (subjective, but the spec records it as a goal too).

## Out of Scope

- A full manual rewrite by a human (the goal is the quality of the generated articles, not the manual work).
- Fine-tuning the style judge with a separate LM (the Kimi K3 judge is sufficient for now).
