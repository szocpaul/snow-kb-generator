# Feature Specification: Context Selection for Article Generation

**Feature Branch**: `016-context-selection`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "Today article generation receives the full story text, all update set XMLs and all related KB articles unchanged as context — part of that is noise, which unnecessarily raises the cost and the hallucination opportunities (what is not in the context cannot be copied in wrongly by the model), and the relevant parts can also get lost in the bulk."

## Background (diagnosis)

- **The pipeline today is "everything in"**: GenerateKb gets the full story + update set XMLs +
  related articles gets the raw set. The noise causes two harms: token cost
  (at every run) and hallucination surface (the series of 004/011/014 specs
  proves that the noise in the context can leak into the article).
- **The measurement infrastructure is complete**: recording, replay, jev-metrics, ReAnchor
  eval-only wrapper, SC-gate pattern, rich_metric for the quality measurement — 016
  reuses these.
- **Lesson accumulation**: asymmetric cost (015 — also relevant here: the relevant
  hiding the context is more expensive than showing the noise); safety floor manually (015);
  min. sample size for the SC gates (013); the extractor/context change with recall protection
  (014: the real hits must not be dropped).
- **The extractor refinement is ready** (fix/extractor-refinement): the false candidates
  4→0, recall 21/21 — 016 builds on it, does not overlap.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Qualifying Context Pieces Before Generation (Priority: P1)

Before generation every context piece (story sections, update set records,
related KB articles) gets a closed, three-state classification: **hide /
summarize / be included unchanged**. The classification is calibrated, typical decision
(with confidence, pinned model); the execution plain Python policy
(thresholds manually/from config); every decision is logged into replay-compatible JSONL.
In case of low confidence or an error the piece is **included unchanged** (fail-open
on the current behavior).

**Why this priority**: This is the problem statement itself — pushing out the noise at the cost-
and the engine of hallucination reduction.

**Independent Test**: with mock context pieces (obviously relevant update set
record vs. boilerplate XML snippet) → the relevant "show"/"summarize", the noise "hide";
in case of an error every piece is included (fail-open).

**Acceptance Scenarios**:

1. **Given** an obviously irrelevant context piece (e.g. empty/boilerplate
   update set record), **When** the selection runs, **Then** "hide" or "summarize"
   the classification, and it does not get into the generating prompt unchanged.
2. **Given** a record carrying the actual content of the change, **When** the selection
   runs, **Then** "show" and it is included unchanged.
3. **Given** the decision service goes down, **When** the pipeline runs, **Then**
   every piece is included unchanged (fail-open), with a warning log.
4. **Given** low confidence below the threshold, **When** the policy evaluates,
   **Then** the piece is "show" (it leans toward the safe direction — recall protection).

---

### User Story 2 - Measuring the Impact of the Selection (Priority: P1)

The effect of the selection measured: token cost delta and quality delta (rich_metric) on the
on gold examples, baseline-first rule, replay-compatible. The quality is NOT
may degrade; the cost reduction should be numerical and justified.

**Why this priority**: „Measured, not claimed" — a feature is only worth something if
if the noise reduction completes without quality degradation.

**Independent Test**: on the gold examples baseline (without selection) vs with selection
measured token and quality numbers compared, written to the file.

**Acceptance Scenarios**:

1. **Given** the gold examples, **When** both the baseline and the selected run are done,
   **Then** the report contains the per-example and aggregated token delta and
   rich_metric delta.
2. **Given** the selection is enabled, **When** the rich_metric runs on the outputs,
   **Then** the aggregated quality is not worse than the baseline beyond the noise band
   (the 013/014 non-overlapping interval rule).
3. **Given** the measurement runs twice in replay mode, **Then** a byte-identical report.

---

### User Story 3 - Calibrating the Hide/Show Threshold (Priority: P2)

The threshold of the "hide" decision is calibrated (ReAnchor, eval-only wrapper, the 014/015 pattern):
the metric is asymmetric — hiding a relevant piece (recall error) multiple times
is more expensive than showing the noise (precision error). The safety floor (fail-open = "show")
not movable with calibration.

**Why this priority**: US1 also works with a hand-guessed threshold; the calibration
proves or improves it — as in 015.

**Independent Test**: labeled sample (relevant/noise pieces) + ReAnchor run +
report; the "threshold stays" branch is also a result written to the file.

**Acceptance Scenarios**:

1. **Given** a labeled context sample (min. 20 pieces, the 013 lesson),
   **When** the calibration runs, **Then** the report contains the value before/after the threshold and
   shows the asymmetric cost.
2. **Given** the calibration finds no better threshold, **Then** it stays + justification
   into the file (not a silent stay).
3. **Given** a degradation on the gold baseline, **Then** the threshold does not go live
   (regression gate, the 015 SC-003 pattern).

### Edge Cases

- Every piece would be "hide" → would the generation run with minimal context? No: the
  the story text itself can NEVER be hidden (it can only be classified when sectioned); at least
  the story body always gets included.
- The "summarize" summary errs/hallucinates → the cheap local summary
  is done with a model; the hallucination risk is caught by the gate (014) on the article output.
- The selection slows down the pipeline (plus decision calls) → the decision model
  fast (System One), the latency cost measured against the token savings.
- Threshold operator `<`; the safety floor (fail-open = „show") is NOT
  movable (the 015 pattern).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every context piece gets a closed three-state classification at generation
  before; the classification is calibrated, with a pinned model, with confidence.
- **FR-002**: Fail-open is mandatory: in case of an error or low confidence the piece
  is included unchanged (the current behavior is the safe base).
- **FR-003**: Every qualification is logged to replay-compatible JSONL (the 013
  recording format).
- **FR-004**: The story main body can never be hidden (at most sectioned
  can be classified).
- **FR-005**: The quality measurement baseline-first, with the existing rich_metric,
  replay-reproducibly; the gate (014) and the extractor (§46/47) untouched.
- **FR-006**: The selection can be switched off from config (the 013/014 flag pattern).

### Key Entities

- **Context piece**: one unit of the generation input (story section /
  update set record / related article) + source type.
- **Qualification**: {hide / summarize / show} + confidence + logged evidence.
- **Selection report**: per-example and aggregated token and quality delta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cost: the token usage of the selected run numerically
  smaller than the baseline on the gold examples (the target value in plan.md, the baseline
  after its measurement is recorded — not from thin air).
- **SC-002**: Quality protection: the aggregated rich_metric is NOT worse than the
  the baseline beyond the non-overlapping noise interval (the 013/014 rule).
- **SC-003**: Recall protection: the selected prompt still contains the
  real component names referenced by gold articles (0/9 dropouts, with exit code
  test — the recall pattern of the extractor refinement).
- **SC-004**: Fail-open proven: on a simulated failure the pipeline unchanged
  runs with context (test).
- **SC-005**: Replay: running the measurement twice gives a byte-identical report.
- **SC-006** (calibration): the decision on the hide/show threshold (change or stay)
  into the file with a justification, on min. 20 labeled pieces (the 013 sample size lesson).

## Assumptions

- The context pieces can be split without the generating prompt structure
  would collapse (the template is sectioned — since the 006 spec).
- The local dev model (Qwen3.8-27B) is enough for the „summarize" summaries.
- There is real noise in the context of the gold examples (the Phase 0 baseline proves it —
  if there is no measurable noise, the spec can stop here, per the 014 "0 hits" pattern).

## Out of Scope

- Changing the generative program (program.py / program.json) and the GEPA program.
  *(Restart condition: if the US2 measurement shows that the selection the
  does not bring improvement without changing the prompt structure.)*
- Improving the related-article search (search_kb_articles) — that is the recall side,
  this spec is the selection of the already found pieces.
  *(Restart condition: if after the selection the NUMBER of pieces is the narrow intersection.)*
- Fine-tuning the quality of "summarize" (prompt tuning) — in the first round
  simple summary; the quality is measured at SC-002.
- The threshold re-measurement on the 015 gate (T009 condition) — that is a separate round, the
  from the data of the observation period.
