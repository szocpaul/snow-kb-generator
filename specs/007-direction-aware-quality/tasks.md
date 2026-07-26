# Tasks: Direction-Aware KB Quality

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Direction-Aware Metric (US1)

- [ ] T001 [US1] `detect_direction(story_text)` helper in `eval/metric.py` (inbound/outbound/both/unknown, keyword counting)
- [ ] T002 [US1] Direction violation check in `template_adherence`: a non-applicable section filled in → penalty + explicit feedback ("Direction violation: ...")
- [ ] T003 [US1] Tests: outbound+filled Inbound → penalty; outbound+N/A → OK; both/unknown → check skipped (`tests/test_eval_metric.py`)

## Phase 2: Signature Rule (US2)

- [ ] T004 [US2] `GenerateKbFromTemplate` docstring: categorical direction rule + placement rule for shared components

## Phase 3: SkilledProposer (US3)

- [ ] T005 [US3] `pip install skilled-proposer` + pyproject.toml dev/extras update
- [ ] T006 [US3] `run_gepa_optimization()`: `instruction_proposer=SkilledProposer(extra_guidance=...)` (direction rule + "never invent KB numbers/titles"), fallback to stock proposer with a warning
- [ ] T007 [US3] Test: the GEPA is created with SkilledProposer (mock import), fallback branch tested

## Phase 4: Re-optimization & Validation (US4)

- [ ] T008 [US4] Re-run baseline + GEPA (clean `gepa_logs/`) → new `artifacts/program.json`; check: the proposals contain the direction rule
- [ ] T009 [US4] Valset check: 0 direction violation; optimized score ≥ 0.850
- [ ] T010 [US4] Full test suite green + server restart + live STRY0010010 validation (Inbound = N/A, components in Outbound)
- [ ] T011 [US4] Agent.md + README.md update, commit
