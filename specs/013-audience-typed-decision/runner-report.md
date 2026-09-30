# Runner Report: spec 013-audience-typed-decision (T001–T014, without MANUAL GATEs)

**Runner**: spec013-runner-k3 | **Date**: 2026-09-29 | **Branch**: `013-audience-typed-decision`
**Run mode**: SNOW_KB_DEV_MODE=1 (local Qwen3.8-27B as the task model; Kimi token usage: 0)

## Preflight (all GREEN)
- 0: branch + 4 spec files existed; 0b: `task_model == "local"` in dev mode; 0c: local llama.cpp smoke OK
- 1: TYPESAFE_API_KEY + minimal system_one call OK (jev-1.13.0)
- 2: typesafe-sdk 0.7.2 + dspy 3.4.0 a projekt-venvben (`/opt/snow-kb-venv`)
- 3: gold dataset with 9 runnable story inputs; 4: pytest starting state 287/287 green
- Note: `pytest -q` with SNOW_KB_DEV_MODE=1 fails 1 environment-polluted test
  (`test_default_task_model_is_kimi`) — the suite must be run without env, dev mode is
  is needed for LLM runs. In addition, a pre-existing isolation error: the `tests/test_pipeline.py`
  fails 9 tests when run on its own (green in the full suite) — this was already the case before spec 013.

## Per-phase results

| Phase | Task | Result |
|---|---|---|
| Setup | T001, T002 | ✅ typesafe-sdk + dspy[typesafe] dep (pin <3.5), `.env.example` + systemd placeholder, `audience_decision.*` config + 4 config tests |
| Baseline | T003 | ✅ 9 gold examples, generative path with local Qwen: **9/9 developer** → `artifacts/audience_baseline.json` |
| Baseline | T004 | ✅ gold labels with evidence → `data/examples/gold_audience_labels.json` (6 developer, 3 helpdesk) |
| US1 | T006-T008 | ✅ 12 new tests (fail-first → green), `src/snow_kb/audience.py`, pipeline integration with the wrapper |
| US2 | T009, T010 | ✅ threshold tests (exact boundary → fallback), work_notes flagging on the client's write path |
| Measurement | T012 | ✅ live recording + replay + ReAnchor + SC gates (see below) |
| Closing | T014 | ✅ 309/309 pytest green, Agent.md §41, backlog TASK-1, commit + push |

## SC-gate outputs (`python -m eval.audience_sc_gates` → exit 1)

- **SC-001 GREEN**: baseline 6/9 vs new 6/9 — the new decision is not worse (per-example JSON: `artifacts/audience_calibration_report.json`)
- **SC-002 RED** (the confirmatory 0.7 gate): selective_risk=0.200 (>0.15) | coverage=0.833 (≥0.7 ✅) | ECE=0.163 (>0.10)
- **SC-003 GREEN**: fail-open tests (SDK error, schema mismatch, resolve level)
- **SC-004 GREEN**: two replays produce a byte-identical report (4491 bytes)

## Anatomy of the RED SC-002 (for the T013 human review)

- The Jev assigned `developer` to all 9 gold examples; it got the 3 labeled helpdesk cases wrong (STRY0010003 LDAP, STRY0010004 SAP IDOC, STRY0010005 SolMan sync).
- Evidence in the labels: the "Investigation Steps" section of all three articles is explicitly a troubleshooting guide ("When to use this guide", "Escalate to infrastructure team") — it addresses the support reader.
- The confidence signal works: 2 of the 3 errors have low confidence (0.26, 0.60 → the 0.7 gate abstains/falls back); 1 is confidently wrong (0.95).
- **EXPLORATORY (NOT confirmatory)**: threshold sweep at 0.8 gives risk=0.111 / coverage=0.75; ReAnchor fitted helpdesk-weight=15.8 (train accuracy 0.667→0.917, the fold check passed). These are NOT confirmatory results — the config `confidence_threshold` therefore **stayed at 0.7**; changing it is the T013 decision.

## Decision notes

1. Threshold operator: the spec's edge case `<` (not `<=`) + T009 "exactly at the threshold → fallback" — implementation: `confidence < threshold + 1e-9` (documented in the audience.py docstring).
2. The baseline was produced in dev mode (local Qwen) → the SC-001 comparison is "generative path local vs Jev", NOT Kimi vs Jev.
3. The production decision call is a direct SDK call (`src/snow_kb/audience.py`); the ReAnchor wrapper (`eval/audience_reanchor.py`) is only for measurement.
4. program.py / program.json / eval metric untouched (the wrapper sits in the pipeline layer, via deepcopy).

## Commit hashes (branch: 013-audience-typed-decision, pushed)
- `2b89ce4` T001+T002: dependencies + audience_decision config block
- `7183b68` T003+T004: baseline (9/9 developer, local Qwen) + gold labels
- `fede169` T006-T010: audience.py + pipeline integration + work_notes flagging
- `07ce995` T012+T014: measurement, SC gates, Agent.md §41, runner report

## Open MANUAL GATEs (not ticked)
- **T005**: review of the baseline + labels (`artifacts/audience_baseline.json`, `data/examples/gold_audience_labels.json`)
- **T011**: approval of the fail-open + developer-default tradeoff before the production run
- **T013**: review of the SC gates; if the threshold changes, the rationale goes into Agent.md

## Restart condition for the verification-layer spec
**NOT YET MET**: spec 013 is not in a stable production state (T011 is open), and the threshold tuning is waiting for a human decision (SC-002 RED). Backlog: TASK-1.
