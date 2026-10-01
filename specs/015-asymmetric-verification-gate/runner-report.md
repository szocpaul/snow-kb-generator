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
  preference restored to the original at the end (`eb0825f9...`).
  - Story: **STRY0010004** ("ServiceNow oldali webhook-fogadas es KB-draft
    generalas bekotese"), Update Set: **STRY0010004** (sys_id e39388bc...).
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
