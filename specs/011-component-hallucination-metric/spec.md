# Feature Specification: Component Hallucination Detection in the Metric + Update Set Dataset Coverage

**Feature Branch**: `011-component-hallucination-metric`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "The T013 human review (2026-08-09) caught a hallucination ('CHG Scheduled' as a fabricated Business Rule name) that the metric did not see — the hallucination axis only validates KB article numbers. In addition, the GEPA run showed that the analyze_changes module never runs on the gold dataset (0 update_set examples), so half of the reflection iterations were no-ops."

## Background (diagnosis)

- **The blind spot (2026-08-09, T013 review):** the generated article mentioned the 'CHG Scheduled' Business Rule name, which occurs 0 times in the Story (the model fabricated it from the `example.atlassian.net` URL + an example sentence in the base docstring). The metric meanwhile showed `hallucination: 1.000` — the spec 004 `_find_hallucinated_kb_references` validates **only `KBxxxxxxx` numbers**, not component names.
- **The blind spot does NOT stem from a CLI/artifact bug** (those are fixed): this error class would stay invisible even with the optimized program — all previous eval measurements (baseline 2×, optimized 2×, GEPA 200 rollouts) were produced without component name checking.
- **A prototype already exists** (Agent.md section 30): extraction of quoted names + CamelCase + dotted identifiers → every candidate must appear in the `story_text`. With this, the approved article yielded 4/4 confirmed names.
- **Dataset gap (lesson from the T011 GEPA log):** the gold dataset contains 0 update_set examples → the `analyze_changes` module never runs in the rollouts (`program.py: if update_set_payloads:`) → 6/11 GEPA reflection iterations were "No valid reflective examples" no-ops, and the quality of analyze_changes was unmeasurable.
- **Metric change = baseline obsolescence** (spec 010 pattern): once the new detection is enabled, the baseline must be re-measured, with `cache=False`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Component Name Hallucination Detection (Priority: P1)

The hallucination check of `rich_metric` is extended to named components: every component name candidate in the generated article (quoted names, CamelCase identifiers, dotted identifiers) must appear in the `story_text` (or on the whitelist). If it finds a fabricated name, the hallucination axis is 0, and the feedback **names** the invented component.

**Why this priority**: This closes the blind spot uncovered yesterday — the metric (and GEPA) can only reward/punish what it sees.

**Independent Test**: Mock article with a fabricated component name ('CHG Scheduled') → hallucination 0 + the feedback contains the name; the same article with the real name ('JiraIntegrationUtils', which is in the story) → hallucination 1.0.

**Acceptance Scenarios**:

1. **Given** a generated article with a fabricated component name, **When** rich_metric runs, **Then** the hallucination axis is 0, and the feedback lists the invented names.
2. **Given** a generated article with only names that occur in the story, **When** the metric runs, **Then** the hallucination axis stays 1.0.
3. **Given** the gold HTMLs of the gold dataset, **When** the detection runs on them, **Then** there are NO false positives (the gold articles pass).
4. **Given** generic terms ("Business Rule", "Script Include", "Incident"), **When** the article contains them, **Then** they do NOT count as component names (whitelist).

---

### User Story 2 - Gold Example with Update Set (Priority: P2)

The gold dataset gets at least 1 example that contains `update_set_payloads` (real Update Set XMLs) — so that the `analyze_changes` module runs in the GEPA rollouts, becomes measurable and optimisable, and the "No valid reflective examples" no-ops disappear.

**Why this priority**: The metric blind spot (US1) is more important; extending the dataset improves GEPA effectiveness and the quality of analyze_changes.

**Independent Test**: the dataset loader loads the new example, and during a program call the `analyze_changes` actually runs (visible in the trace).

**Acceptance Scenarios**:

1. **Given** the new gold example, **When** the program runs on it, **Then** the `analyze_changes` runs, and its output enters the context of the article generation.
2. **Given** the extended dataset, **When** GEPA reflection is built, **Then** reflective examples are also collected for `analyze_changes.predict` (no more "No valid reflective examples").
3. **Given** the gold article of the new example, **When** rich_metric runs on it, **Then** the example is evaluable (the gold HTML is consistent with the existing 8 examples).

---

### User Story 3 - Validation with the New Metric (Priority: P3)

Baseline re-measurement with the extended metric (the metric change makes the earlier numbers obsolete — spec 010 pattern), a documented new reference, and a decision on an optional short GEPA run.

**Why this priority**: It only makes sense after the metric and the dataset; the GEPA decision is separate, and is made once the results are known.

**Independent Test**: `python -m eval.baseline --model local` runs, and the new `runs/baseline.json` is produced with per-axis data + the extended hallucination axis.

**Acceptance Scenarios**:

1. **Given** the new metric, **When** the baseline re-measurement finishes, **Then** the new reference is documented (Agent.md + tasks.md), and the old numbers are marked as obsolete.
2. **Given** the new baseline, **When** the mini-GEPA decision is made, **Then** the justification is recorded (postponing is a legitimate outcome as well).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Component detection is false-positive-free on the gold dataset — the gold articles pass the check (this is the most important constraint; a noisy axis would hurt GEPA).
- **FR-002**: The detection is fault-tolerant (spec 010 FR-002 pattern): on any internal error the axis must not halt the metric (warning + neutral behaviour).
- **FR-003**: The whitelist (generic terms, product names) lives in one shared, tested place (e.g. a constant in `eval/metric.py`, following the `BANNED_PHRASES` pattern).
- **FR-004**: The hallucination axis' **weight and name stay unchanged** (0.15); the detection is extended within the existing axis (KB numbers AND component names). The scope of the axis is clarified by a code comment/docstring (see Agent.md 30: avoiding the "kb_reference_accuracy" misunderstanding).
- **FR-005**: The update_set_payloads of the new gold example must consist of real (anonymised) Update Set XMLs, and the corresponding gold article must reflect the result of the code analysis.
- **FR-006**: After the metric change, a baseline re-measurement is mandatory, with `cache=False` (spec 010 cache hygiene).

### Success Criteria

- **SC-001**: Fabricated component name → hallucination 0 + the feedback names the name (mock test).
- **SC-002**: The gold articles of the gold dataset pass the component check 100% (0 false positives).
- **SC-003**: `analyze_changes` actually runs on at least 1 dataset example (trace evidence), and GEPA reflection is also able to collect reflective examples for it.
- **SC-004**: New baseline reference documented; the mini-GEPA decision is justified.

## Out of Scope

- Full (200 call) GEPA re-run — at most a short, separately approved validation run.
- Modifying the KB number detection (spec 004) — it works, we do not touch it.
- Production deploy changes (the pipeline stays untouched; the metric only lives on the eval side).
- Re-optimising `program.json` with the new metric — a separate decision after validation.
