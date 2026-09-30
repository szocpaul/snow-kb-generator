# Feature Specification: Audience Decision with Calibrated Confidence

**Feature Branch**: `013-audience-typed-decision`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "The `ExtractChange` audience field is provided by Kimi K3, but without a calibrated confidence signal — in edge cases we cannot see whether the model was certain or guessing, so the article style may be built on a wrong foundation."

## Background (diagnosis) *(project overlay)*

- The `audience` field of the `ExtractChange` signature is `Literal["helpdesk","end-user","developer"]` — a closed, three-option decision that the generative model currently returns as a plain string, without any confidence signal.
- The audience determines the style and technical depth of the generated article (`GenerateKbFromTemplate` docstring: "use it ONLY to adapt the writing style/tone") — a badly landed decision skews the voice of the whole article, and the error only surfaces during human review.
- Generative models (due to RLHF training) are typically overconfident: the edge case (e.g. "end-user vs helpdesk") comes back just as self-assured as the obvious case.
- The decision is a "gut-check" in nature anyway — a snap judgement among three options, not long reasoning; this makes it especially suitable for separating out from the generation step.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The audience decision with probability and confidence (Priority: P1)

The pipeline produces the audience field with a dedicated, typed decision call: the response contains the selected option, the per-option probabilities, and a confidence value. The `change_summary` and `key_steps` stay with the generative model as before.

**Why this priority**: This is the only value of this spec — making the confidence visible. Everything else builds on it.

**Independent Test**: Mock story (clearly developer-oriented) → audience="developer", high confidence; edge case mock story → measurably lower confidence.

**Acceptance Scenarios**:

1. **Given** an unambiguous story, **When** the pipeline runs, **Then** the audience is the same as the current model's, AND confidence ≥ 0.8.
2. **Given** a deliberately edge case story (describing a business process but with developer details), **When** the pipeline runs, **Then** confidence < 0.8, and the value is logged.
3. **Given** the 9 gold examples, **When** the new decision path runs on them, **Then** the agreement rate with the gold audience is no worse than the current model's (per-example JSON output).

---

### User Story 2 - Handling low confidence (Priority: P2)

If the confidence is below a configurable threshold, the pipeline behaves explicitly: default `developer` (the safest technical tone) + a note in the work_notes that the audience was uncertain.

**Why this priority**: It only makes sense once US1 provides a confidence value; the fallback policy is a small but deliberate decision.

**Independent Test**: Mock low-confidence response → audience="developer" + work_notes note.

**Acceptance Scenarios**:

1. **Given** confidence < threshold, **When** the pipeline runs, **Then** audience="developer" and the work_notes contain the note with the measured confidence.
2. **Given** confidence ≥ threshold, **When** the pipeline runs, **Then** there is no fallback and no note.

---

### Edge Cases

- What happens if the decision service is unavailable (timeout, 5xx, auth error)? → fail-open to the existing generative path, with a warning log (FR-001).
- What happens if the response confidence value is exactly at the threshold? → the "below the threshold" rule must be strictly inequality-free (`<`, not `<=`), so the boundary value falls to the safe (fallback) side.
- What happens if the story text is so incomplete that all three options have low probability? → the confidence will be low from the start, and the P2 fallback path handles it.
- What happens if the response schema is unexpected (SDK version drift)? → the same fail-open path as for an API error, plus logging the error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The decision call is error-tolerant (fail-open to the current behaviour): on any error the pipeline falls back to the existing generative-model audience, with a warning log. Availability comes first.
- **FR-002**: The threshold and the decision model version are configurable in `config.yaml`; a pinned version, not a floating alias, is used for the calibration measurement (playbook: "model swap = baseline re-measurement").
- **FR-003**: Every decision logs: the selected option, the per-option probabilities, and the confidence — this is the calibration data source. The log format must be replay-compatible (the jev-dspy-lab pattern: JSONL, request hash, response, measured latency, model identifier), so that the calibration measurement can be re-run deterministically without a live API.
- **FR-004**: The current generative audience path remains as a switchable fallback (config flag) until the calibration measurement is closed out.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gold dataset (9 examples): the new decision agrees with the gold audience on at least as many examples as the current one — verified in the per-example JSON with the compare script's exit code.
- **SC-002**: Calibration quality on the gold + mock sample (the jev-dspy-lab metric set): at the 0.7 confidence gate **selective risk ≤ 0.15** AND **coverage ≥ 0.7**, furthermore **ECE (expected calibration error) ≤ 0.10**. The measurement must come from a deterministic replay (recorded responses), not from live API calls — the threshold sweep is exploratory only, the confirmatory result is the pre-designated 0.7 gate.
- **SC-003**: Fail-open test: on a simulated API outage the pipeline runs without error, with the result of the fallback path.
- **SC-004**: Reproducibility: playing the same recorded response set twice yields a byte-identical measurement report (the lab ReplayClient pattern); on a live re-recording the per-example decisions are stable with a pinned model.

## Assumptions

- For the 9 examples of the gold dataset the correct audience can be derived from the style of the gold articles; if not, the labelling is a precondition of the measurement (a separate task in tasks.md).
- The decision service is allowed to be reached from the server (hosted API); the key is available in the systemd unit's environment.
- "developer" as the low-confidence default is the safest tone for the team — if the review sees it differently, US2 changes.
- The existing 286-test suite stays green; new tests are written for the new behaviour.

## Out of Scope *(project overlay, with restart conditions)*

- The post-generation verification layer (component-name hallucination gate) — a separate spec; restart condition: this spec is stable in production and the threshold tuning is meaningful based on the confidence data.
- Any rewrite of the `change_summary`/`key_steps` fields.
- Using the `dspy-typesafeify` fork or any other DSPy fork — a direct SDK call from the pipeline.
- Modifying the 5-axis eval metric — the existing rich_metric shows the effect of the audience change, the metric itself is untouched.
