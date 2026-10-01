# Feature Specification: Asymmetric Calibration + Moving the Gate into the Writing Component

**Feature Branch**: `015-asymmetric-verification-gate`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "The verification gate currently treats the false "exists" and the false "does not exist" labels as if they had the same weight — but a hallucinated name that slips through misleads the engineer reading the article, while a false signal is at most noise. Moreover, the gate lives in the pipeline layer, not in the writing component itself, so a future alternative call path could bypass it."

## Background (diagnosis)

- **The 014 gate works** (SC-002 GREEN with n=24, in flag mode in production), but the
  calibration metric is **symmetric**: both error types „cost" the same. The
  in reality the false „exists" (a hallucinated name passes) is much more expensive than the false
  „non-existing" (unnecessary signal) — so the threshold is not sure that the real
  currently does not minimize the real cost.
- **The gate lives in the pipeline layer** (`_apply_verification_gate` before the `create_kb_article`
  before the call), not in the client that performs the write — a future other call path
  (CLI, another endpoint) could bypass it. The reference pattern (cmpnd-ai v1 permission
  gate): the gate lives INSIDE the tool, „nothing the caller writes can bypass it".
- **The dev samples cannot be used for instance measurement** (company policy: they cannot be migrated
  cannot) — the RED of the 014 SC-001 largely resulted from this. The calibration sample
  therefore a new **story+update set fixture that natively exists on the PDI** is built (the
  snow-kb-generator project itself as an integration project), where the ground truth
  are pure. This also patches the 011 dataset gap (update set gold example).
- **The 013/014 infrastructure is reused**: recording, replay, jev-metrics,
  ReAnchor eval-only wrapper, SC-gate pattern — we build nothing new.
- Accumulating lessons: min. sample size for the SC gates (013), exploratory ≠ confirmatory
  (013/014), threshold operator `<` (013).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PDI-native story+update set fixture (Priority: P1)

A real Story is created for the snow-kb-generator project (as an integration project)
on the PDI, plus an Update Set that contains components that REALLY EXIST on the PDI
contains. This is the ground truth of the calibration sample: the „existing" labels come from the instance
coming from reality, the spelling-variant and fabricated examples derive from this mechanically.

**Why this priority**: Blocking prerequisite — most of the current 24-example sample
the artifact of the dev↔PDI deviation; pure calibration is only meaningful on a PDI-native sample.

**Independent Test**: after the fixture is created, a verification script proves that
EVERY component name appearing in the story update set „exists" on the PDI via spot-check.

**Acceptance Scenarios**:

1. **Given** the new Story + Update Set on the PDI, **When** the spot-check runs over the update set
   runs over the component names, **Then** each one "exists" (0 not_found).
2. **Given** a labeled sample derived from the fixture (real names + spelling variants
   + fabricated names), **When** the labels are reviewed, **Then** every label
   derivable from the instance fact.
3. **Given** the extended dataset, **When** the dataset loader runs, **Then** the new example
   conforms to the 011 format (story + update_set_payloads + gold article draft).

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

1. **Given** the PDI-native labelled sample, **When** the calibration runs with the asymmetric
   runs with the asymmetric metric, **Then** the report contains: threshold before/after,
   cost before/after, and the comparison with the symmetric metric.
2. **Given** the calibration finds no better threshold, **When** the report is produced,
   **Then** the threshold remains + the rationale is written to a file (not „silent remaining").
3. **Given** the new threshold in the config, **When** the production call runs,
   **Then** the direct SDK path reads it (the ReAnchor wrapper remains
   measurement — 013/014 sample).

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

- The threshold of the calibrated layer changes → on the existing 24-example sample too, it must be
  to measure the behavior change (regression report), not only on the new sample.
- The components entering the fixture update set may be deleted at PDI refresh → the
  fixture check script (US1) always runs before the measurement; if a component is missing,
  the measurement stops (no improvising).
- Threshold operator: `<` (not `<=`) — the 013 pattern.
- The calibration tunes ONLY the `confidence_threshold`: the fail-open and the flag-only
  the default behavior is a manually set „safety floor", not movable by calibration
  (the fit_thresholds.py pattern: DENY_BELOW stays manual — "one mistake that no other
  example repeats is not enough to move it").
- The in-flight articles during the gate raise: the requests running at the moment of the restart use the old
  path are completed (deploy note, not a functional requirement).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The calibration metric uses asymmetric costs; the weight ratio
  (e.g. 10:1) is the plan.md Key Decision, not a hard-coded "random" value.
- **FR-002**: The calibration sample derives from the PDI-native fixture (US1); the
  dev-derived names do NOT enter the PDI measurement with the „exists" label.
- **FR-003**: The rationale for the threshold change (or non-change) is written to a file, the
  together with the symmetric-metric countervalue.
- **FR-004**: The gate moves into the write path of `servicenow_client`; every article write
  (pipeline, CLI, future path) runs through this; double protection/double recording is FORBIDDEN.
- **FR-005**: Fail-open unchanged (instance/TypeSafe outage → the article goes out with a warning).
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

- **SC-001**: The fixture integrity is proven: EVERY component name of the update set
  via spot-check „exists" on the PDI (0/0 deviation), with an exit-code script, before the measurement.
- **SC-002**: The calibration report on the PDI-native sample (the existing 24 + the new
  fixture examples, total ≥30): the total cost measured with the asymmetric metric
  is NOT WORSE than the symmetric one; the threshold decision (change or no change)
  rationale in the report.
- **SC-003**: Regression on the existing sample: with the new calibration the 24-example sample
  result is written to a file and compared with the 014 baseline — in case of degradation the
  report is RED and the threshold does not come into effect.
- **SC-004**: The gate move is proven: the direct client call is gated too (test),
  and the pipeline run produces exactly 1 gate decision + 1 recording entry (test).
- **SC-005**: Replay reproducibility: running the calibration measurement twice
  byte-identical report (cache hygiene, the 013/014 pattern).

## Assumptions

- There is an admin user on the PDI → the permission blind spot of the metadata query does not
  is relevant (excluding the 4th mechanism of 014).
- The fixture components survive the lifetime of the PDI; if the PDI is rebuilt,
  the recreation of the fixture is part of the bootstrap.
- The deploy (gate raise) is a separate, human-directed step — the runner does not perform it.

## Out of Scope

- Tightening the behavior (flag → strip/block) — that from the data of the observation period
  arising, a separate decision. *(Restart condition: the JSONL statistics show that
  that the flag noise is negligible AND the proportion of real hits justifies the tightening.)*
- The „saving" of the dev samples in any form — the company policy excludes this,
  the fixture (US1) replaces them from a measurement standpoint.
- Reactivation of the archived 013 audience feature.
- Further expansion of the calibration sample beyond ≥30 examples. *(Restart condition:
  if the SC-002-like gates also prove unstable on the ≥30 sample.)*
