# spec 014 runner report — Component Name Verification Against the Instance + Production Push Gate

**Status: DONE — T001-T015 closed, the gate switched on in production (enabled=true, behavior=flag).**
Date: 2026-09-30 | Branch: `014-component-instance-verification` | Run: DEV mode (SNOW_KB_DEV_MODE=1; 0 Kimi tokens for the task model — every generation ran on the local Qwen3.8-27B)

## Preflight (all GREEN, 2026-09-30 15:4x)

branch ✅ | DEV mode task_model=local ✅ | local LLM ✅ | TYPESAFE_API_KEY + system_one ✅ |
typesafe-sdk 0.7.2 + dspy 3.4.0 ✅ | SNOW table-API ✅ | pytest 309 green ✅

## T005 MANUAL GATE — APPROVED BY A HUMAN (checkbox intentionally NOT ticked)

- (a) continue: YES; (b) more SNOW-specific extraction: YES — implemented
  (state word + log message suffix + FQDN filtering, with a recall-protection test).

## Per-phase results

### Phase 1 — Setup
- **T001** ✅ `verification_gate` config block: enabled=false (default — I did NOT turn it on),
  behavior=flag|strip|block (default flag), pinned model (jev-1.13.0; the `-latest` alias → ConfigError),
  confidence_threshold=0.7, spotcheck_cache_path, recording_path. +5 config tests.
- **T002** ✅ `.env.example` is fine (TYPESAFE_API_KEY has been there since 013); `deploy/README.md`:
  spot-check metadata tables + read permission.

### Phase 2 — Baseline (T003/T004)
- **T003** ✅ `eval/component_inventory.py` — a replica of the 011 pattern, 12 examples
  (9 gold + 3 freshly generated with the local Qwen), 49 candidates → `artifacts/component_inventory.json`.
- **T004** ✅ `eval/spotcheck_baseline.py` — update-set whitelist + live spot-check:
  **not_found=26, exists=6, in_update_set=5, whitelisted=12, error=0**
  → `artifacts/component_baseline_report.json/.md`, `..._blindspot.json`.
  All 26 not_found names also appear in the story (the blind spot of the 011 axis is proven);
  in 2 of the 3 freshly generated articles such a name appears → reproducible TODAY.

### Phase 3 — US1 metric axis (T006/T007)
- **T006** ✅ test first (FAIL → implementation).
- **T007** ✅ `src/snow_kb/verification.py`: candidate extraction (011 pattern + the
  SNOW filtering approved in T005), update-set whitelist (from the `get_update_set_changes`
  output), `SpotChecker` (per name, JSON cache — part of the recording, the basis of SC-004),
  fail-open on every error. `eval/metric.py` gets an **instance axis** ALONGSIDE the
  existing axes: inactive (configure_instance_axis(None)) the score formula is bit-identical
  to the old behaviour (FR-006 — the 004/011 story-based check is untouched).

### Phase 4 — US2 production push-gate (T008/T009)
- **T008** ✅ test first (7 tests, FAIL → implementation).
- **T009** ✅ `_apply_verification_gate` in front of `create_kb_article` (FR-004):
  flag → a `verification_note` in the Story work_notes with the measured confidence (KD1 default);
  strip/block only via config; fail-open on a drop-out; JSONL recording (FR-003).

### Phase 5 — US3 calibrated layer (T010/T011)
- **T010/T011** ✅ TypeSafe Noul (pinned jev-1.13.0), 3-way decision:
  yes (exists/reference) / external (external system — spec Out of Scope, NO flag) /
  no (fabricated). Threshold operator `<` + eps (the 013 pattern). SDK error → fail-open to
  the deterministic path.

### Phase 6 — Measurement (T012/T013)
- **T012** ✅ `data/examples/verification_labeled.json` — **24 labelled examples**
  (6 exists + 5 missing_real + 4 variant + 5 fabricated + 4 external), the labels are committed.
  **Labelling facts (at the request of the launcher)**: the gold stories are REAL ALDI stories
  that live on the **dev** instance (the dev ServiceNow URL and the sys_id of the Script
  Include are visible in the gold-7 story HTML); the instance of the measurement (the PDI
  prod instance) is NOT that one — the spec assumption ("the gold names are real at the time
  of the measurement") is therefore not met on the PDI.
  Update-set coverage: 8 of the 9 gold stories have NO update set on the PDI (only
  STRY0010016) — the spec edge case is the common path.
- **T013** ✅ live capture (TypeSafe jev-1.13.0 + PDI spot-check) + deterministic replay
  + ReAnchor evaluation-only wrapper (the 013 T012 pattern; the production call remains
  a direct SDK call).

## SC-gate outputs (`python -m eval.verification_sc_gates` → exit 1)

| Gate | Result | Detail |
|---|---|---|
| **SC-001** | 🔴 **RED** | 1 of 9 gold articles (gold-7) got a "does not exist" marking: `interface.solman`, `integration.solman` (external SolMan hostnames — out of scope per the spec, false positives by intent), `ChTask`, `FrameWork` (CamelCase fragments). The rest of the gold is clean. Environmental fact: the gold stories belong to the dev instance, and the PDI metadata snapshot does not contain their components. |
| **SC-002** | 🟢 GREEN | n=24 (≥20 ✅); at the confirmatory 0.7 gate **selective_risk=0.111 (≤0.15)**, **coverage=0.750 (≥0.7)**, ECE=0.049 |
| **SC-003** | 🟢 GREEN | fail-open tests (5 of them) exit=0 |
| **SC-004** | 🟢 GREEN | two replays are byte-identical (12814 bytes) |

Exploratory sweep (NOT confirmatory): at 0.75+ risk=0.000, but coverage 0.583 < 0.7
(the gate would fail) — the **confirmatory 0.7 is the good compromise**, the config stays 0.7
(the threshold was NOT changed; the ReAnchor weight fit (yes=20.5, acc 0.708→0.875) is exploratory).
Wrong cases at the 0.7 gate (4 of 24): 3 spelling variants with low confidence
(0.26-0.73) + 1 external case exactly on the threshold (0.70, `<` operator → flag).

## T014 MANUAL GATE — awaiting decision (checkbox NOT ticked)

1. **Approval of the gate default behaviour**: per KD1 `flag` (a work_notes flag,
   the article goes out) — strip/block is available via config. Proposal: **approval**.
2. **Approval of the fail-open tradeoff** (FR-002): unreachable instance/TypeSafe →
   the article goes out with a warning. Proposal: **approval** (availability comes
   first, the 013 KD4 pattern).
3. **Review of the SC gates**: SC-002/003/004 green; SC-001 red — with the environmental
   explanation above. Open question: are the gold-7-style hostname fragment false positives
   acceptable noise for a flag-only gate, or should there be one more refinement round
   (e.g. an API path/host heuristic) BEFORE switching it on.
4. **Proposal for switching the gate on (enabled=false → ?)**: my proposal is
   **enabled=true + behavior=flag** for an observation period (the flag is non-destructive,
   the JSONL recording provides the measurement basis); strip/block only later, on the basis
   of the data. The final decision is the human one.

## Commits

| Hash | Content |
|---|---|
| df709b8 | spec 014 files |
| c8da6e0 | T001+T002: config block + deploy permissions |
| 9919aaa | T003+T004: baseline inventory + spot-check |
| 2d3823c | T006: tests (FAIL) |
| d01d495 | T007: verification.py + metric instance axis |
| (T008-T011) | push-gate + calibrated layer (345 green) |
| (T012) | labelled sample + external 3-way decision |
| (T005-review b) | more SNOW-specific extraction |
| (T013) | measurement + SC-gates + ReAnchor (349 green) |

## Prohibition check

- GEPA: did not run ✅ | T005/T014 not ticked ✅ | program.py/program.json untouched ✅
- the 004/011 story-based check is untouched (the instance axis is ALONGSIDE) ✅
- the production decision is a direct SDK call, ReAnchor is for measurement only ✅
- verification_gate.enabled=false ✅ | Kimi tokens for the task model: 0 ✅
- the threshold sweep is reported as exploratory, the confirmatory gate: 0.7 ✅

## T014 MANUAL GATE — RESULT (human approval, 2026-09-30)

All four proposals are APPROVED: (1) default behaviour = flag (KD1) ✅; (2) the fail-open
tradeoff (FR-002) ✅; (3) SC-001 red ACCEPTED with the environmental explanation (the gold
stories are dev-instance ones; the hostname/fragment noise is tolerated in flag-only mode) ✅;
(4) the gate MAY BE SWITCHED ON: enabled=true + behavior=flag for an observation period ✅.

## T015 — Closing

- `config.yaml`: `verification_gate.enabled: true` (behavior=flag) — per the T014 decision,
  with a justifying comment.
- `Agent.md` §44: log entry (facts, decisions, lessons, commit hashes).
- Backlog: **TASK-2 → Done** (final summary with the measurement evidence).
- Checkboxes: T005 + T014 ticked (the human approved, with explicit permission).
- **Open follow-up**: T002b (PDI preparation / update-set import) — the human added it to
  the spec AFTER the measurement was closed (commit 2dca8cb); it is a precondition for the
  future measurements, this run closed with the T014 acceptance without the import.
- Rebase onto the human spec change (2dca8cb) + push: **a4dfe25**.
- Final gate: **349 pytest green** (state after the push).

## Final commit hashes (after the rebase, pushed)

| Hash | Content |
|---|---|
| a4dfe25 | T015 closing (gate ON, Agent.md §44, TASK-2 Done) |
| 716421a | T014 package runner report |
| 15e81c0 | T013 measurement + SC-gates + ReAnchor |
| (earlier ones) | see `git log origin/014-component-instance-verification` |
