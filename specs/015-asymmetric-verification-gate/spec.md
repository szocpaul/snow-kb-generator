# Feature Specification: Asymmetric Calibration + Moving the Gate into the Writing Component

**Feature Branch**: `015-asymmetric-verification-gate`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "The verification gate currently treats the false "exists" and the false "does not exist" labels as if they had the same weight — but a hallucinated name that slips through misleads the engineer reading the article, while a false signal is at most noise. Moreover, the gate lives in the pipeline layer, not in the writing component itself, so a future alternative call path could bypass it."

## Background (diagnosis)

- **The 014 gate works** (SC-002 GREEN with n=24, in flag mode in production), but the
  calibration metric is **symmetric**: both error classes "cost" the same. In
  reality the false "exists" (a hallucinated name passing through) is far more
  expensive than the false "does not exist" (an unnecessary signal) — so the
  threshold does not necessarily minimize the real cost.
- **The gate lives in the pipeline layer** (`_apply_verification_gate` before the
  `create_kb_article` call), not in the writing client — a future alternative call
  path (CLI, another endpoint) could bypass it. The reference pattern (cmpnd-ai v1
  permission gate): the gate lives INSIDE the tool, "nothing the caller writes can
  bypass it".
- **The dev samples cannot be used for instance measurement** (company policy: they
  cannot be migrated) — a large part of the 014 SC-001 RED stems from this. The
  calibration sample therefore builds on a **new fixture of a story+update set that
  natively exists on the PDI** (the snow-kb-generator project itself as an
  integration project), where the ground truth is clean. This also patches the 011
  dataset gap (an update-set gold example).
- **The 013/014 infrastructure is reused**: recording, replay, jev-metrics,
  ReAnchor eval-only wrapper, SC-gate pattern — we build nothing new.
- Lessons accumulated: minimum sample size for the SC gates (013), exploratory ≠
  confirmatory (013/014), threshold operator `<` (013).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PDI-native story+update set fixture (Priority: P1)

The snow-kb-generator project itself (as an integration project) gets a real Story
on the PDI, plus an Update Set that contains components that REALLY exist on the
PDI. This calibration sample is the ground truth: the "exists" labels come from the
reality of the instance, the spelling variants and the fabricated examples are
derived from it mechanically.

**Why this priority**: Blocking precondition — a large part of the current
24-example sample is an artifact of the dev↔PDI difference; clean calibration only
makes sense on a PDI-native sample.

**Independent Test**: after the fixture is created, a verification script proves
that EVERY component name in the story's update set "exists" on the PDI via
spot-check.

**Acceptance Scenarios**:

1. **Given** the new Story + Update Set on the PDI, **When** the spot-check runs over
   the component names of the update set, **Then** each one "exists" (0 not_found).
2. **Given** the labelled sample derived from the fixture (real names + spelling
   variants + fabricated names), **When** the labels are reviewed, **Then** every
   label can be derived from the facts of the instance.
3. **Given** the extended dataset, **When** the dataset loader runs, **Then** the new
   example conforms to the 011 format (story + update_set_payloads + gold article
   draft).

---

### User Story 2 - Calibration with asymmetric cost (Priority: P1)

The calibration metric weights the error classes by their real cost: the false
"exists" (a hallucination that slips through) is multiple times more expensive than
the false "does not exist" (an unnecessary signal). ReAnchor tunes the threshold
with this metric on the PDI-native sample; the resulting threshold goes into the
config with a rationale, compared against the earlier symmetric result (or it stays,
if it does not win on the folds — the behaviour of the reference pattern).

**Why this priority**: This is the first half of the problem statement — the gate
currently does not minimize the real cost.

**Independent Test**: the calibration run's report shows the cost measured with the
symmetric vs the asymmetric metric on the same sample, and the rationale for the
threshold change (or non-change) goes into a file.

**Acceptance Scenarios**:

1. **Given** the PDI-native labelled sample, **When** the calibration runs with the
   asymmetric metric, **Then** the report contains: threshold before/after, cost
   before/after, and the comparison with the symmetric metric.
2. **Given** the calibration finds no better threshold, **When** the report is
   produced, **Then** the threshold stays + the rationale is written to a file (not
   a "silent stay").
3. **Given** the new threshold in the config, **When** the production call runs,
   **Then** the direct SDK path reads it (the ReAnchor wrapper remains
   measurement-only — the 013/014 pattern).

---

### User Story 3 - Moving the gate into the writing component (Priority: P2)

The verification gate moves into the write path of `servicenow_client` (into the
body of `_create_kb_article_live`), so that EVERY call path — current and future —
goes through the same gate. The pipeline-layer call disappears (a single
unavoidable point instead of double protection).

**Why this priority**: This is a defense-architecture question; the functional
behaviour already works today, this is the "cannot be bypassed" guarantee.

**Independent Test**: a test that calls the client DIRECTLY (bypassing the pipeline)
→ the gate still runs; and a test that proves the pipeline-layer call is gone (no
double check + double recording).

**Acceptance Scenarios**:

1. **Given** a direct `_create_kb_article_live` call with a non-existent name, **When**
   the client runs, **Then** the gate runs (flag: work_notes note), even without the
   pipeline layer.
2. **Given** a normal pipeline run, **When** the article is written, **Then** exactly
   ONE gate decision and ONE JSONL entry are produced.
3. **Given** an instance outage, **When** the in-client gate runs, **Then** fail-open
   as before (warning + the article goes out).

### Edge Cases

- The threshold of the calibrated layer changes → the behaviour change must be
  re-measured on the existing 24-example sample too (regression report), not only on
  the new sample.
- The components that end up in the fixture's update set may be deleted when the PDI
  is refreshed → the fixture verification script (US1) always runs before the
  measurement; if a component is missing, the measurement stops (no improvisation).
- Threshold operator: `<` (not `<=`) — the 013 pattern.
- The calibration tunes ONLY the `confidence_threshold`: the fail-open and the
  flag-only base behaviour are a manually set "safety floor", not movable by
  calibration (the fit_thresholds.py pattern: DENY_BELOW stays manual — "one
  mistake that no other example repeats is not enough to move it").
- The in-flight articles during the gate move: the requests running at the moment of
  the restart finish on the old path (a deployment note, not a functional
  requirement).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The calibration metric uses asymmetric costs; the weight ratio
  (e.g. 10:1) is the plan.md Key Decision, not a hard-coded "random" value.
- **FR-002**: The calibration sample derives from the PDI-native fixture (US1); the
  dev-derived names MUST NOT enter the PDI measurement with an "exists" label.
- **FR-003**: The rationale for the threshold change (or non-change) is written to a
  file, together with the symmetric-metric counter-value.
- **FR-004**: The gate moves into the write path of `servicenow_client`; every
  article write (pipeline, CLI, future path) goes through it; double
  protection/double recording is FORBIDDEN.
- **FR-005**: Fail-open unchanged (instance/TypeSafe outage → the article goes out
  with a warning).
- **FR-006**: The 004/011 story-based check and the production direct SDK call stay
  untouched; the ReAnchor wrapper is measurement-only.

### Key Entities

- **PDI fixture**: Story + Update Set + the list of the real component names in it
  (the ground truth of the calibration).
- **Cost-weighted metric**: with the explicit cost of the false "exists" and of the
  false "does not exist" (the ratio is a Key Decision).
- **Calibration report**: threshold before/after, cost before/after, symmetric
  comparison, rationale — in a file, not in chat.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The fixture integrity is proven: EVERY component name of the update
  set "exists" on the PDI via spot-check (0/0 deviation), with an exit-code script,
  before the measurement.
- **SC-002**: The calibration report on the PDI-native sample (the existing 24 + the
  new fixture examples, ≥30 in total): the total cost measured with the asymmetric
  metric is NOT WORSE than with the symmetric one; the threshold decision (change or
  stay) is justified in the report.
- **SC-003**: Regression on the existing sample: the result of the 24-example sample
  with the new calibration is written to a file and compared with the 014 baseline —
  in case of degradation the report is RED and the threshold does not go live.
- **SC-004**: The gate move is proven: the direct client call is gated too (test),
  and the pipeline run produces exactly 1 gate decision + 1 recording entry (test).
- **SC-005**: Replay reproducibility: running the calibration measurement twice
  produces a byte-identical report (cache hygiene, the 013/014 pattern).

## Assumptions

- There is an admin user on the PDI → the permission blind spot of the metadata query
  is not relevant (the 014 mechanism 4 is excluded).
- The fixture components survive the lifetime of the PDI; if the PDI is rebuilt,
  recreating the fixture is part of the bootstrap.
- The deployment (the gate move) is a separate, human-directed step — the runner does
  not perform it.

## Out of Scope

- Tightening the behaviour (flag → strip/block) — that is a separate decision born of
  the data of the observation period. *(Restart condition: the JSONL statistics show
  that the flag noise is negligible AND the rate of the real hits justifies the
  tightening.)*
- "Saving" the dev samples in any form — the company policy excludes this; the
  fixture (US1) replaces them for measurement purposes.
- Reactivating the archived 013 audience feature.
- Extending the calibration sample beyond the ≥30 examples. *(Restart condition: if
  the SC-002-like gates prove unstable on the ≥30 sample as well.)*
