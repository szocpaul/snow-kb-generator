# Runner report — spec 015 (asymmetric calibration + gate move)

**Status: PARKED at the T003 MANUAL GATE** (waiting for a human review).
Last update: 2026-10-01T17:16:55

## Preflight — all GREEN

| # | Check | Result |
|---|---|---|
| 0 | branch `015-asymmetric-verification-gate` + the spec files | OK |
| 0b | SNOW_KB_DEV_MODE=1 → task_model=local | OK |
| 0c | local LLM (Qwen3.8-27B, Tailscale) smoke completion | OK (HTTP 200) |
| 1 | TYPESAFE_API_KEY + minimal system_one | OK (choice=yes, conf=0.74) |
| 2 | dspy 3.4.0 + typesafe_sdk in the project venv | OK |
| 3 | PDI table-API (sys_script_include, admin user) | OK (HTTP 200) |
| 4 | the 014 measurement infrastructure is present | OK |
| 5 | pytest initial state | 349 passed |

## Phase results

### Phase 1 — Fixture + baseline (T001, T002, T004 DONE)

- **T001**: `scripts_pdi/fixture_verification_gate.py` — a komponensek a PDI-n
  an ALREADY EXISTING record (capture, NOT creation). The direct `sys_update_xml`
  insertje ACL-tiltott → a capture a platform standard mechanizmusa: az user
  current update set set to the fixture set (user preference), benign
  field touch + IMMEDIATE restore (the record content did not change), the
  preference restored to the original at the end (`ea9a4e63...`).
  - Story: **STRY0010004** ("ServiceNow oldali webhook-fogadas es KB-draft
    generalas bekotese"), Update Set: **STRY0010004** (sys_id e17d49d7...).
  - 13 captured components: 4 Script Include (PrototypeServer,
    MosaicHermesUtils, RAGResponseGenerator, CodeSigningUtil), 3 Business Rule
    ('Change Phase Events Before', 'Contract Instance', 'Choice Events'),
    3 System Property (com.snc.sdlc.scrum.pp.smclass, glide.lastplugin,
    glide.ui.session_timeout), 3 fields (kb_knowledge.u_source_story,
    rm_story.story_points, rm_story.type).
  - Dump: `artifacts/verification_fixture_components.json` (name, type, sys_id,
    sys_updated_on) — **THIS has to be reviewed in T003.**
  - Incident during the run: the first attempt left an orphan Story/Update Set
    (STRY0010005) and 9 unnecessary dictionary capture rows — both were
    CLEANED UP (deleted), the dump finally points to STRY0010004.
- **T002 / SC-001**: the `verify` sub-command as an exit-code gate — **GREEN:
  13/13 names exist via spot-check (0 deviation)**.
- **T004**: baseline — the asymmetric cost of the current 0.7 threshold on the
  existing 24 examples: **4** (0 slipped-through hallucinations ×10, 4 unnecessary
  signals ×1; symmetric: 4). File: `artifacts/verification_asymmetric_baseline.json`.

### Phase 3 — Asymmetric calibration (T006 DONE, T005/T007/T008 CODE ready, run after T003)

- **T006**: `eval/verification_asymmetric.py` + 9 tests (the 10:1 ratio, KD1; the
  report schema; the "stays" decision with a rationale) — green.
- **T005**: `eval/verification_labeled_015.py` (mechanical derivation of the
  real/variant/fabricated/type-mismatch examples; **minimum: <8 approved names →
  exit 2**; merging ≥30 examples). Run AFTER the T003 approval:
  `python -m eval.verification_labeled_015 build [--approved <json>]`
- **T007**: `eval/verification_measure_015.py` (capture/report, per-case RAW
  (choice, confidence) for the clean replay sweep) + `eval/verification_reanchor_015.py`
  (ReAnchor with the asymmetric metric, eval-only wrapper; no GEPA).
- **T008**: the SC-003 regression block is part of the measure report (degradation →
  the decision "stays", the config is NOT modified).

### Phase 4 — Gate move (T010, T011 DONE)

- **T010**: `tests/test_verification_gate_client.py` (5 tests, fail-first) — a
  direct `_create_kb_article_live` call is gated; in the pipeline exactly 1
  decision + 1 recording; fail-open also in block mode; the old pipeline
  function is gone.
- **T011**: the gate moved INTO the body of `servicenow_client._create_kb_article_live`
  (the `_apply_verification_gate` method); the pipeline-layer call and the
  `VerificationBlocked` were DELETED from pipeline.py (the exception lives in
  `snow_kb.errors`); deployment note in `deploy/README.md` (the restart is a
  HUMAN STEP; the in-flight requests finish on the old path).
- The 014 `tests/test_verification_gate.py` was rewired to the new architecture
  (real client + stubbed HTTP), the behaviour tests are unchanged.
- **pytest: 363 passed** (349 + 14 new).

### Phase 5 — Closure (T012 CODE ready, T013 outstanding)

- **T012**: `eval/verification_sc_gates_015.py` (SC-001..SC-005 exit codes) —
  run after the calibration.

## MANUAL GATE — T003 (human to-do)

**Review the dumped component list**: `artifacts/verification_fixture_components.json`
(filtering out the odd/unstable names). If you narrow it down, give the approved
names (e.g. as a `{"approved_names": [...]}` JSON), T005 builds the sample with that.
If the list can stay as it is, say so and the runner continues with all 13 names.

The runner MUST NOT tick the T003 checkbox.

## Commit hashes (branch: 015-asymmetric-verification-gate)

- `1271cc4` T001+T002: PDI-native fixture + SC-001 gate GREEN
- `72e8ae6` T006+T004: asymmetric metric + baseline (cost=4)
- `55be7a8` T010+T011: gate move into the client, 363 tests green
- `5644c8a` T005/T007/T008/T012 code (run after T003)

## Notes

- The `git add -A` pulled in the `.groma/` autoscan files (the `groma agent-instructions`
  first scan created it) in the 55be7a8 commit — I did NOT write/curate it
  on them; if they are not needed for the branch, they can be removed in a separate commit.
- Kimi token usage: 0 (everything local/dev mode; the TypeSafe jev calls
  only ran in the smoke test, the calibration capture is due after T003).


---

# CONTINUATION after the T003 approval (2026-10-01T17:41:27)

**Status: PARKED at the T009 MANUAL GATE** (human review of the calibration report).

## T003 approval + cleanup proof

- The human APPROVED all 13 names; an independent check proved: the
  sys_updated_on change is a side effect of the capture (touch+revert), there is
  NO content modification, NO '[spec015-capture]' residue.
- The orphan STRY0010005 + 8b6e1911 update set were already DELETED during the
  run (the runner's cleanup); re-checked: both are 404.

## Phase 2/3/5 results (T005, T007, T008, T012)

- **T005**: `data/examples/verification_labeled_015.json` — 57 examples
  (24 old + 33 fixture-derived). The T005 MINIMUM: 9 extractable names (≥8 ✓) —
  4 approved names (RAGResponseGenerator, kb_knowledge.u_source_story,
  rm_story.story_points, rm_story.type) the gate's conservative 011
  not visible to the extractor's regexes → as a non-measurable example
  (the label is still true; this is the documented limitation of the extractor).
  The FR-002 filter is cache-based: each of the 6 old "exists" ones is empirically
  PDI-verified, not a single one was dropped.
- **T007**: capture (57 cases, live jev-1.13.0 + PDI spot-check) + replay report
  + ReAnchor (asymmetric metric, eval-only wrapper):
  - ReAnchor: aszimmetrikus score **−0.526 → −0.281**, szimmetrikus accuracy
    0.474 → 0.719 (EXPLORATORY fitted parameters).
  - Sweep (EXPLORATORY): the candidate threshold **0.35** (asymmetric cost
    21 → 18; fp_exists 0, fn 21 → 18). The dominant error class: the calibrated
    layer says "no"/"external" for the spelling variants of the real names (this the
    threshold does NOT fix).
  - **Sensitivity analysis (KD1): the threshold is SENSITIVE to the ratio** —
    At 10:1 and 20:1 the 0.35 wins, at 5:1 the 0.0-0.10 band would win.
    This is the key data for the T009 decision.
  - The symmetric comparison in the report (spec US2): 21 → 18.
- **T008 / SC-003**: the old 24 examples: asymmetric cost **4 → 3** at 0.35 —
  There is NO degradation.
- **T012**: `eval/verification_sc_gates_015.py` — **SC-001..SC-005 ALL GREEN**:
  - SC-001 GREEN: 13/13 fixture names exist via spot-check (live PDI)
  - SC-002 GREEN: n=57 (≥30), the decision is justified, the symmetric comparison exists
  - SC-003 GREEN: no degradation on the old sample
  - SC-004 GREEN: the gate-move tests (12+9) exit=0
  - SC-005 GREEN: double replay byte-identical (37007 bytes)
- pytest teljes suite: **363 passed**.

## MANUAL GATE — T009 (human to-do)

**Review the calibration report**: `artifacts/verification_calibration_report_015.json`
(+ `artifacts/verification_reanchor_report_015.json`).

The candidate decision: `confidence_threshold: 0.7 → 0.35` (asymmetric cost
21 → 18 on the 57 examples; on the old sample 4 → 3, no degradation). WARNING: the candidate
EXPLORATORY sweep result, and because of the ratio sensitivity (at 5:1 the 0.0
would win) confirming the 10:1 KD1 ratio is also part of the decision.

- If you APPROVE: the runner writes the 0.35 into config.yaml + the rationale into the
  goes into Agent.md (this is part of T013), then closing.
- If NOT: the threshold stays 0.7, the "stays" rationale goes into the report/Agent.md.

The config.yaml is NOT modified until the approval (it is 0.7 now as well). The
runner MUST NOT tick the T009 checkbox.

## Commit hashes (continuation)

- `d77daa4` T005: merged sample (70→57 examples after the extractability filter)
- `07c2b52` T005 fix: extractability filter + extractable variants
- `64166f9` T007+T008+T012: calibration + SC gates ALL GREEN


---

# CLOSURE (2026-10-01T17:54:16) — FINAL

**Status: DONE.** The T009 MANUAL GATE was APPROVED by the human.

## The T009 decision and its execution

- The **10:1 weight ratio is CONFIRMED**; the `confidence_threshold` was **CHANGED
  from 0.7 → 0.35** in config.yaml (with the human's approval).
- **MANDATORY CONDITION (the human's comment): the 0.35 threshold rests on a SINGLE
  false positive case (in the sweep 0.35 is the lowest value that filters out the 1
  fabricated case that slipped through) — the threshold MUST BE RE-MEASURED at the
  NEXT sample extension.** It is recorded in the Agent.md §45 rationale and in the
  config.yaml comment as well.
- Agent.md §45 log entry: facts / decisions / lessons learned.

## Final audit (every point of the objective)

| Requirement | Status |
|---|---|
| T001-T013 implemented in dev mode | ✅ (T003/T009 human gates: not ticked by the runner, approved by the human) |
| Kimi token usage | 0 (task model: local Qwen3.8-27B; the calibration was measured with the pinned jev-1.13.0 TypeSafe calls — measurement infrastructure, not the task model) |
| SC-001..SC-005 green with exit codes | ✅ `python -m eval.verification_sc_gates_015` → exit 0 (SC-001 13/13, SC-002 n=57 with a justified decision, SC-003 4→3 no degradation, SC-004 gate tests, SC-005 byte-identical replay) |
| MANUAL GATEs parked for a human decision | ✅ T003, T009 — the runner ticked neither; both got a human approval |
| Closing report in runner-report.md | ✅ this file |
| full pytest suite | ✅ 363 passed (349 initial + 14 new) |
| commit + push | ✅ origin/015-asymmetric-verification-gate |
| backlog | TASK-3 (the spec 016 candidate) stays To Do — the 015 was not a backlog task |

## All commits (branch: 015-asymmetric-verification-gate)

- `1271cc4` T001+T002: PDI-native fixture (STRY0010004), SC-001 gate
- `72e8ae6` T006+T004: asymmetric metric + baseline
- `55be7a8` T010+T011: gate move into the client
- `5644c8a` T005/T007/T008/T012 code
- `74bf45c` runner-report (T003 parking)
- `d77daa4` T005: merged sample
- `07c2b52` T005 fix: extractability filter
- `64166f9` T007+T008+T012: calibration + SC gates GREEN
- `7a2a02e` runner-report (T009 parking)
- `405ea5f` T013 closure: config 0.35 + Agent.md §45

## Open human steps

- **Deploy**: the go-live of the gate move is a HUMAN step (`sudo systemctl restart
  snow-kb.service`) — the deploy/README.md note. The runner did NOT deploy.
- **When expanding the sample**: the 0.35 threshold must be re-measured (T009 condition).
- A human can tick the T003/T009 tasks.md checkboxes (the runner did not).
