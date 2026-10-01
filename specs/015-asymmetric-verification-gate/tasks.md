# Tasks: Asymmetric Calibration + Moving the Gate into the Writing Component

**Input**: Design documents from `/specs/015-asymmetric-verification-gate/`
**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] [Story] Description`

* **\[P]**: can be run in parallel (different file, no dependency)

* **\[USn]**: which user story it belongs to

* **MANUAL GATE**: human decision — the runner/agent MUST NOT tick it

## Phase 1: Fixture + baseline (US1, playbook: baseline first)

* [x] T001 [US1] Fixture script following the `scripts_pdi/` pattern. **The Story is about the snow\_kb\_generator project** (as an integration project: "ServiceNow-side webhook receiving and KB draft generation integration"). **The components are records that ALREADY EXIST on the PDI** (capture, NOT creation): the script queries the metadata tables via the table-API (sys\_script\_include / sys\_script / sys\_properties / sys\_dictionary; active=true, global scope, sys\_updated\_on preference), selects a total of **10–15 existing components** per type (from several types: Script Include, Business Rule, System Property, field — and UI Policy or ACL if they exist on the PDI), captures them into an Update Set, and writes the Story text for THESE real names (the logic is inverted: the story does not define the components). Every step is logged

* [x] T002 \[US1] Dumping the selected component names into an artifact (name, type, sys\_id, sys\_updated\_on) + the fixture-integrity gate: EVERY name in the update set "exists" via spot-check (SC-001, exit-code script)

* [x] T003 [US1] **MANUAL GATE**: human review of the dumped component list (filtering out the odd/unstable names) — the runner MUST NOT tick it

* [x] T004 \[US1] Baseline recording: the ASYMMETRIC cost of the current threshold (0.7) on the existing 24-example sample, into a file (the basis of the later comparison)

## Phase 2: US1 – Labelled sample from the fixture

* [x] T005 [US1] Sample-derivation script: mechanical generation of the real / spelling variant / fabricated / type mismatch examples from the dumped name set (a minimal version: a single story context, a name-level sample); **minimum condition: if the approved master-name set has < 8 names, the task MUST STOP and report — the sample MUST NOT be diluted with correlated variants**; merge with the existing 24 examples (the dev-derived "exists" labels excluded from the PDI measurement, FR-002) → ≥30 examples in total, the labels committed under `data/examples/`

## Phase 3: US2 – Asymmetric calibration

* [x] T006 \[US2] Test: the behaviour of the asymmetric metric (false "exists" = 10×, false "does not exist" = 1× penalty, correct decision = 0); the report schema (threshold before/after, cost before/after, symmetric comparison). MUST FAIL before the implementation

* [x] T007 \[US2] Asymmetric metric + ReAnchor run on the merged sample (extension of `eval/verification_reanchor.py`, the 014 pattern); the calibration report into a file, including the rationale for the "threshold stays" case as well; the production call remains a direct SDK call

* [x] T008 \[US2] Regression gate (SC-003): the new (or staying) threshold re-measured on the existing 24-example sample, compared with the 014 baseline → in case of degradation the report is RED, the config is NOT modified

* [x] T009 [US2] **MANUAL GATE**: review of the calibration report; if the threshold is modified, the rationale goes into the Agent.md — the runner MUST NOT tick it

## Phase 4: US3 – Moving the gate into the client (test first)

* [x] T010 [US3] Test: a direct `_create_kb_article_live` call (bypassing the pipeline) is gated as well; in a normal pipeline run exactly 1 gate decision + 1 recording entry; fail-open in the in-client gate; the old pipeline call is gone (no double protection). MUST FAIL before the implementation

* [x] T011 [US3] The `_apply_verification_gate` logic moves into the write path of `servicenow_client`; the pipeline-layer call is deleted; deployment note into `deploy/README` (the in-flight requests at the moment of the restart)

## Phase 5: Closure

* [x] T012 Running the SC gates (SC-001 fixture integrity, SC-002 calibration report, SC-003 regression, SC-004 gate tests, SC-005 byte-identical replay) — with exit codes, `cache=False`/replay mode

* [x] T013 Closure: the full pytest suite green (349 + new), a log entry in the Agent.md (facts, decisions, lessons learned), commit + push, backlog update

## Dependencies

* T001 blocks T002 and T005; T003 (MANUAL GATE) blocks T005

* T006/T010 (tests) come FIRST, before T007/T011 (implementation) — test-first order

* T007 only after T004 (baseline) and T005 (sample); T008 after T007

* T011 is independent of the calibration (T007) — it can run in parallel with Phase 3, but T012 runs after both

## Validation Checklist

* [ ] Every FR has a task (FR-001→T006/T007, FR-002→T005, FR-003→T007/T009, FR-004→T010/T011, FR-005→T010/T011, FR-006→T007)

* [ ] Every SC has a gate (SC-001→T002, SC-002→T007, SC-003→T008, SC-004→T010, SC-005→T012)

* [ ] The tests are in place before the implementation

* [ ] Every task names a concrete file

