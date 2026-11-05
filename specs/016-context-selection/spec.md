# Feature Specification: Context Selection for Article Generation

**Feature Branch**: `016-context-selection`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Today article generation receives the full story text, all update set XMLs and all related KB articles unchanged as context — part of that is noise, which unnecessarily raises the cost and the hallucination opportunities (what is not in the context cannot be copied in wrongly by the model), and the relevant parts can also get lost in the bulk."

## Background (diagnosis)

- **The pipeline today takes "everything"**: GenerateKb receives the full story + update set XMLs + related articles raw, all together. The noise causes two kinds of harm: token cost (on every run) and a hallucination surface (the 004/011/014 spec series proves that noise present in the context can leak into the article).
- **The measurement infrastructure is complete**: recording, replay, jev-metrics, ReAnchor eval-only wrapper, SC-gate pattern, rich_metric for quality measurement — 016 reuses all of them.
- **Accumulated lessons**: asymmetric cost (015 — relevant here too: hiding relevant context costs more than showing noise); safety floor set by hand (015); minimum sample size for the SC gates (013); extractor/context change with recall protection (014: the real markers must not drop out).
- **The extractor refinement is done** (fix/extractor-refinement): false candidates 4→0, recall 21/21 — 016 builds on top of it and does not overlap it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Qualifying Context Pieces Before Generation (Priority: P1)

Before generation every context piece (story sections, update set records, related KB articles) receives a closed, three-way qualification: **hide / summarize / include unchanged**. The qualification is a calibrated, typed decision (with confidence, pinned model); the execution is a plain Python policy (thresholds set by hand/from config); every decision is logged to replay-compatible JSONL. On low confidence or an error the piece **is included unchanged** (fail-open to the current behaviour).

**Why this priority**: This is the problem statement itself — removing the noise is the engine of cost and hallucination reduction.

**Independent Test**: with mock context pieces (clearly relevant update set record vs. boilerplate XML fragment) → the relevant piece gets "show"/"summarize", the noise gets "hide"; on error every piece is included (fail-open).

**Acceptance Scenarios**:

1. **Given** a clearly irrelevant context piece (e.g. an empty/boilerplate update set record), **When** the selection runs, **Then** the qualification is "hide" or "summarize" and the piece does not enter the generating prompt unchanged.
2. **Given** a record that actually carries the substance of the change, **When** the selection runs, **Then** it gets "show" and is included unchanged.
3. **Given** the decision service goes down, **When** the pipeline runs, **Then** every piece is included unchanged (fail-open), with a warning in the log.
4. **Given** low confidence below the threshold, **When** the policy evaluates, **Then** the piece gets "show" (it leans to the safe direction — recall protection).

---

### User Story 2 - Measuring the Impact of the Selection (Priority: P1)

The impact of the selection is measured: token cost delta and quality delta (rich_metric) on the gold examples, following the baseline-first rule, replay-compatibly. Quality MUST NOT degrade; the cost reduction must be numerical and justified.

**Why this priority**: "Measured, not claimed" — the feature is only worth something if the noise reduction happens without a quality degradation.

**Independent Test**: comparing the measured token and quality numbers of the baseline (without selection) versus with selection on the gold examples, written to a file.

**Acceptance Scenarios**:

1. **Given** the gold examples, **When** both the baseline and the selected run have been executed, **Then** the report contains the per-example and the aggregated token delta and rich_metric delta.
2. **Given** the selection is enabled, **When** rich_metric runs on the outputs, **Then** the aggregated quality is not worse than the baseline beyond the noise band (the 013/014 non-overlapping interval rule).
3. **Given** the measurement runs twice in replay mode, **Then** the report is byte-identical.

---

### User Story 3 - Calibrating the Hide/Show Threshold (Priority: P2)

The threshold of the "hide" decision is calibrated (ReAnchor, eval-only wrapper, the 014/015 pattern): the metric is asymmetric — hiding a relevant piece (recall error) costs several times more than showing noise (precision error). The safety floor (fail-open = "show") cannot be moved by calibration.

**Why this priority**: US1 works with a hand-guessed threshold too; the calibration confirms or improves it — as in 015.

**Independent Test**: labelled sample (relevant/noise pieces) + ReAnchor run + report; the "threshold stays" branch is written to a file as well.

**Acceptance Scenarios**:

1. **Given** a labelled context sample (min. 20 pieces, the 013 lesson), **When** the calibration runs, **Then** the report shows the threshold value before/after and the asymmetric cost.
2. **Given** the calibration does not find a better threshold, **Then** it stays + justification written to a file (no silent staying).
3. **Given** a degradation on the gold baseline, **Then** the threshold does not go live (regression gate, the 015 SC-003 pattern).

### Edge Cases

- Every piece would be "hide" → would the generation run with minimal context? No: the story text itself can NEVER be hidden (it can only be qualified section by section); at least the story body always gets in.
- The "summarize" summary is wrong/hallucinates → the summary is produced with a cheap local model; the hallucination risk is caught by the gate (014) on the article output.
- The selection slows down the pipeline (extra decision calls) → the decision model is fast (System One), the latency cost is measured against the token saving.
- Threshold operator `<`; the safety floor (fail-open = "show") MUST NOT be moved by calibration (the 015 pattern).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every context piece receives a closed three-way qualification before generation; the qualification is calibrated, with a pinned model and confidence.
- **FR-002**: Fail-open is mandatory: on error or low confidence the piece is included unchanged (the current behaviour is the safe base).
- **FR-003**: Every qualification is logged to replay-compatible JSONL (the 013 recording format).
- **FR-004**: The story body must never be hidden (at most it can be qualified section by section).
- **FR-005**: The quality measurement is baseline-first, uses the existing rich_metric, is replay-reproducible; the gate (014) and the extractor (§46/47) stay untouched.
- **FR-006**: The selection can be switched off from config (the 013/014 flag pattern).

### Key Entities

- **Context piece**: a unit of the generation input (story section / update set record / related article) + source type.
- **Qualification**: {hide / summarize / show} + confidence + logged evidence.
- **Selection report**: per-example and aggregated token and quality delta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cost: the token usage of the selected run is numerically smaller than the baseline on the gold examples (the target value is in plan.md, fixed after the baseline measurement — no guessing).
- **SC-002**: Quality protection: the aggregated rich_metric is NOT worse than the baseline beyond the non-overlapping noise interval (the 013/014 rule).
- **SC-003**: Recall protection: the selected prompt still contains the real component names referenced by the gold articles (0/9 drop-outs, exit-code test — the pattern of the extractor refinement).
- **SC-004**: Fail-open proven: on a simulated outage the pipeline runs with unchanged context (test).
- **SC-005**: Replay: running the measurement twice yields a byte-identical report.
- **SC-006** (calibration): the hide/show threshold decision (change or stay) is written to a file with a justification, on min. 20 labelled pieces (the 013 sample-size lesson).

## Assumptions

- The context pieces can be split up without the generating prompt structure collapsing (the template is sectioned — since spec 006).
- The local dev model (Qwen3.8-27B) is enough for the "summarize" summaries.
- There is real noise in the context of the gold examples (the Phase 0 baseline proves it — if there is no measurable noise, the spec may stop here, following the 014 "0 hits" pattern).

## Out of Scope

- Changing the generative program (program.py / program.json) and the GEPA program.
  *(Restart condition: if the US2 measurement shows that the selection does not bring an improvement without changing the prompt structure.)*
- Improving the related-article search (search_kb_articles) — that is the recall side; this spec selects the already found pieces.
  *(Restart condition: if after the selection the NUMBER of pieces is the narrow intersection.)*
- Fine-tuning the quality of the "summarize" (prompt tuning) — a simple summary in the first round; the quality is measured by SC-002.
- Re-measuring the threshold on the 015 gate (T009 condition) — that is a separate round, from the observation period data.
