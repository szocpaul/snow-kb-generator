# Feature Specification: Component Name Verification Against the Instance + Production Push Gate

**Feature Branch**: `014-component-instance-verification`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "The generated KB articles contain ServiceNow record, component or field names that do not exist in the given instance and cannot be derived from the source Story either — the LLM hallucinated them. Today these can slip into published articles unnoticed and mislead the L2/L3 engineer who reads the article."

## Background (diagnosis)

- **The existing protection is story-based, not instance-based** (spec 004/011): the metric
  checks whether the component name appears in `story_text`. This covers the "not in the
  Story" error class, but not whether the name **exists at all** in the instance —
  the Story itself may also contain a misspelled or never-created component name.
- **There is no component name gate on the production path**: `strip_hallucinated_references`
  (pipeline.py) filters only KB article numbers before the push; component names pass
  through to ServiceNow unchecked.
- **The measurement infrastructure exists** (archived dividend of spec 013, Agent.md §43): JSONL
  recording, replay, calibration metrics (selective risk / coverage / ECE), ReAnchor
  eval-only wrapper, exit-code-based SC-gate pattern. Spec 014 reuses these —
  we do NOT build anything new.
- **The lesson from 013 is incorporated**: the SC gates have a minimum sample size (see SC-002);
  the calibration sweep is exploratory, not confirmatory.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instance-based Component Name Verification in the Metric (Priority: P1)

Verification of the named component names in the generated article (tables, fields, Business Rules,
Script Includes, etc.) extends to **instance reality**: the name must exist
in the given instance (in the metadata tables); it is not enough that it appears in the Story.
The metric penalises the non-existent names by naming them.

**Why this priority**: This is the problem statement itself — today the hallucinated names pass
through the blind spot of the metric if they appear in the Story (or if the Story itself is wrong).

**Independent Test**: Mock instance metadata (known table/field list) + mock article with a
non-existent table name → the metric gives 0 on the instance axis and names the name;
the same with a real name → 1.0.

**Acceptance Scenarios**:

1. **Given** mock instance metadata (known table/field list) and a generated article with a non-existent
   table name, **When** the instance verification runs, **Then** the name gets the "does not exist"
   status and appears by name in the report.
2. **Given** an article that contains only names existing in the instance, **When** the
   verification runs, **Then** every name has the "exists" status, there is no false positive.
3. **Given** the instance metadata query is unavailable, **When** the verification runs,
   **Then** fail-open: the check is skipped with a warning, the pipeline continues (the
   story-based metric protection stays untouched).
4. **Given** generic terms ("Business Rule", "Incident"), **When** the article
   contains them, **Then** they do NOT count as component names (the whitelist pattern of 011).

---

### User Story 2 - Production Push Gate for Component Names (Priority: P1)

The pipeline validates the named component names against the instance BEFORE writing
the article to ServiceNow. In the case of a non-existent name the article does NOT go out unnoticed:
the suspicious names get a work_notes flag with the measured confidence (following the 013 pattern),
and the behaviour is configurable (flag / strip / block — the default is the Key Decision in plan.md).

**Why this priority**: Defense-in-depth — the metric protects the eval path, this gate protects
production. The sharp edge of the problem statement ("they slip out unnoticed") is exactly what this closes.

**Independent Test**: Unit test: the gate flags/blocks an article containing a non-existent component name
based on the mock instance list; real names pass through untouched.

**Acceptance Scenarios**:

1. **Given** an article with a non-existent component name, **When** the push gate runs, **Then** the name
   is flagged/named in work_notes (or the behaviour configured), and the log
   contains the decision.
2. **Given** an article with only real names, **When** the gate runs, **Then** the article goes out
   unchanged, plus negligible latency.
3. **Given** the instance verification is unavailable, **When** the gate runs, **Then** fail-open:
   the article goes out with a warning (availability comes first — the KD4 pattern of 013).

---

### User Story 3 - Calibrated Decision for Ambiguous Cases (Priority: P2)

The clean "exists / does not exist" cases are deterministic (exact name matching against the
instance metadata). For the ambiguous cases (spelling variant, abbreviation, "does this name refer
to this real component?") a calibrated, typed decision is produced with a confidence and with
replay-compatible logging — by reusing the 013 measurement infrastructure.

**Why this priority**: The deterministic core of the P1 gate delivers value on its own;
the calibrated layer reduces the false positives for spelling variants.

**Independent Test**: Spelling variant ("JiraIntegrationUtils" vs "Jira Integration Utils")
→ the calibrated decision assigns it to the real component with high confidence; a completely new name
→ low confidence / "does not exist".

**Acceptance Scenarios**:

1. **Given** a name spelling variant that refers to a real component, **When** the calibrated decision runs,
   **Then** the decision is "exists (reference)", with high confidence.
2. **Given** a completely unknown name, **When** the decision runs, **Then** low confidence
   or "does not exist", and a work_notes flag.
3. **Given** the calibration service goes down, **When** the gate runs, **Then** fail-open to the
   deterministic verification.

### Edge Cases

- The name appears in the Story AND in the instance, but means something else (conflicting name usage) →
  the calibrated layer's job; the deterministic path treats it as "exists".
- The instance metadata query is partial (some table types are unavailable) → the affected
  types are skipped with a warning, the remaining checks stay alive.
- The article contains a placeholder or generic terms → not a component name (011 whitelist).
- Very large component list in the instance → the cache refresh and memory
  limits of the spot-check are in plan.md.
- The Story has no Update Set → the gate only goes as far as the instance spot-check layer
  (without whitelist); the Phase 0 inventory measures how often this happens.
- Threshold operator: following the 013 pattern `<` (not `<=`), the exact boundary value leans
  in the safe direction.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST validate the named component names in the generated article
  against the instance metadata (exists / does not exist / ambiguous).
- **FR-002**: Fail-open is mandatory: in case of any error of the instance query or the decision service
  the pipeline continues on the existing path, with a warning log.
- **FR-003**: Every decision MUST be logged to replay-compatible JSONL (reusing the 013
  recording format).
- **FR-004**: The gate MUST be placed in front of the `servicenow_client` write path; the behaviour
  (flag/strip/block) MUST be switchable from config, the generative path stays untouched.
- **FR-005**: The model version of the decision service MUST be pinned (floating alias FORBIDDEN).
- **FR-006**: The instance axis of the metric MUST be backward compatible: the existing
  story-based verification stays untouched alongside it.

### Key Entities

- **Component name candidate**: the named entity extracted from the article (the extraction pattern of 011:
  quoted names, CamelCase, dotted identifier) + type hint (table/field/script).
- **Ground truth (hierarchical)**: 1) the component names of the Story's Update Set
  (primary whitelist), 2) per-name spot-check in the instance metadata (cached)
  for those that are not in the update set.
- **Validation decision**: per candidate {exists / does not exist / ambiguous} + confidence +
  logged evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The instance axis does not degrade the existing eval result: on the gold articles
  there is no false positive (0/9 false "does not exist" marking at the moment of measurement
  on a valid metadata snapshot).
- **SC-002**: The calibrated gate on the gold + deliberately wrong sample: selective risk ≤ 0.15 and
  coverage ≥ 0.7 at the confirmatory 0.7 gate, **on a labelled sample of minimum 20 examples**
  (the lesson of 013: the minimum sample size is mandatory — on 9 examples the gate cannot be justified).
- **SC-003**: Fail-open proven: with a simulated instance and service outage the
  pipeline stays green (test exit code).
- **SC-004**: Replay reproducibility: running the measurement twice gives a byte-identical
  report (cache hygiene: `cache=False` or replay mode).

## Assumptions

- The instance metadata (table/field/script names) can be queried from the PDI via API, and the
  snapshot size is manageable (cacheable).
- The component names of the gold articles are real at the time of the measurement (if an old gold name was
  deleted from the instance in the meantime, we fix it during labelling — the T004 pattern of 013).
- The share of "ambiguous" cases is small; most decisions are deterministic.
- The calibrated layer (US3) uses the archived infrastructure of 013; if the typed
  decision service becomes unavailable, the deterministic core of P1 is meaningful on its own.

## Out of Scope

- Modifying the story-based verification (004/011) — it works, it stays untouched.
- Changing the generative program (program.py / program.json) and the GEPA program.
- *Preventing* hallucination in the prompts — this spec is about detection and the gate.
  *(Restart condition: if the SC-002 measurement shows that the hallucination rate is
  high even with the calibrated gate, a prevention spec follows.)*
- Validating non-ServiceNow entities (URLs, objects of external systems).
  *(Restart condition: if the measurement data shows that most of the outgoing errors are
  of this kind.)*
