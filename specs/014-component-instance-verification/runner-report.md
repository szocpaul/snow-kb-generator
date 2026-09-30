# spec 014 runner report — Component Name Verification Against the Instance + Production Push Gate

**Status: STOPPED at the T005 MANUAL GATE** — waiting for human review.
Date: 2026-09-30 | Branch: `014-component-instance-verification` | Run: DEV mode (SNOW_KB_DEV_MODE=1, local Qwen3.8-27B)

## Preflight (all GREEN)

| # | Check | Result |
|---|---|---|
| 0 | branch + spec files | ✅ `014-component-instance-verification`, spec/plan/tasks/handoff present |
| 0b | SNOW_KB_DEV_MODE=1 → task_model == "local" | ✅ (api_base: llm-server.local:8033) |
| 0c | local LLM minimal completion | ✅ Qwen3.8-27B responds |
| 1 | TYPESAFE_API_KEY + minimal system_one (jev-1.13.0) | ✅ ChoiceAnswer(confidence=0.92) |
| 2 | typesafe-sdk 0.7.2 + dspy 3.4.0 installed | ✅ (part of the pyproject, I did not install it again) |
| 3 | ServiceNow minimal table API | ✅ `sys_db_object` query OK (prod instance) |
| 4 | pytest -q green (WITHOUT dev mode) | ✅ 309 passed |

## Phase 1 — Setup

- **T001** ✅ `verification_gate` config-blokk (`config.yaml` + `VerificationGateConfig`):
  enabled=false (default), behavior=flag|strip|block (default flag), pinnelt model
  (jev-1.13.0, floating alias ConfigError), confidence_threshold=0.7 (0..1 validation),
  spotcheck_cache_path, recording_path. 5 new config tests green.
- **T002** ✅ `.env.example`: TYPESAFE_API_KEY is in it (since 013), no new env is needed.
  `deploy/README.md`: the metadata tables read by the spot check (sys_db_object,
  sys_dictionary, sys_script, sys_script_include) + read permission note.

## Phase 2 — Baseline (US1 prerequisite)

- **T003** ✅ `eval/component_inventory.py`: a replica of the 011 extraction pattern
  (unchanged regexes), 12 examples (9 gold + 3 freshly generated with local Qwen),
  49 candidates in total → `artifacts/component_inventory.json`.
- **T004** ✅ `eval/spotcheck_baseline.py`: Update Set whitelist (embedded
  payloads) + live per-name spot check (sys_db_object/sys_dictionary/sys_script/
  sys_script_include) → `artifacts/component_baseline_report.json/.md`.

  **Summary**: exists=6, in_update_set=5, whitelisted_generic=12,
  **not_found=26**, error=0.

  **Blindspot analysis** (`artifacts/component_baseline_blindspot.json`):
  all 26 not_found names also appear in the source story → the 011 story-based
  would catch neither axis — the spec blindspot is real. The not_found list
  splits into three classes (details in the report .md):
  1. external (SolMan/SAP) objects — out of scope per the spec, the gate should
     must handle it (false-positive risk!);
  2. workflow state/UI text in quotes — extraction false positive;
  3. plausible-looking SNOW component names (e.g. `JiraInboundUtils`,
     `S4ProjectInterface`) — **the actual problem core**, and the 3 freshly
     also appeared in 2 of the generated articles → the hallucination is reproducible TODAY.

- **T005** ⏸ **MANUAL GATE — NOT checked.** Review subject: the baseline inventory
  (artifacts/component_baseline_report.md). Question for the human:
  (a) is the size of the problem proven to continue (suggestion: YES — the 3
  class is reproducible today on the fresh generation);
  (b) handling of the external-system objects (SolMan/SAP): the spec marks it out of scope
  keeps their *validation*, but is it worth reducing the gate false positives
  make the candidate extraction more SNOW-specific (the T007 implementation decision,
  suggestion: yes, type hint + external-system heuristic).

## Phase 3-6

They have not run yet — waiting for the T005 gate decision.

## SC-gate-ek (T013)

They have not run yet.

## Commits

| Hash | Content |
|---|---|
| df709b8 | spec 014 files (starting point) |
| c8da6e0 | T001+T002: verification_gate config block + deploy permissions |
| 9919aaa | T003+T004: baseline inventory + instance spot check + blindspot analysis |

## Prohibition check

- GEPA: nem futott ✅
- T005/T014 MANUAL GATE: not checked ✅
- program.py / program.json / 004-011 story-based check: untouched ✅
- verification_gate.enabled: false maradt ✅
- Kimi tokens for the task model: 0 (every LLM run was a DEV mode local Qwen) ✅
