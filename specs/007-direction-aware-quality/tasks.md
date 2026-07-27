# Tasks: Evidence-First KB Generation

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Evidence-Aware Metric (US1)

- [ ] T001 [US1] `detect_direction(story_text)` helper in `eval/metric.py` (inbound/outbound/both/unknown, keyword counting)
- [ ] T002 [US1] Direction violation check in `template_adherence`: a direction section that does not apply is filled → penalty + "Direction violation: ..." feedback
- [ ] T003 [US1] Unsupported-section penalty: a section that is N/A/absent per the gold is filled in the prediction → penalty + "Unsupported section: ..." feedback
- [ ] T004 [US1] Tests: direction violation is penalized; N/A → OK; both/unknown → skipped; unsupported section → feedback (`tests/test_eval_metric.py`)

## Phase 2: Signature + Dataset (US2, US3)

- [ ] T005 [US2] `GenerateKbFromTemplate` docstring: evidence-first (menu, not mandate; unsupported section OMITTED; direction corollary; rule for shared components)
- [ ] T006 [US3] Gold dataset: (a) deleting the N/A-only section blocks (5 direction-contradicting blocks); (b) deleting the fictional 'related articles' rows (5 KBXXXXXXX placeholder rows — unsupported content; the real references come from the live search) (script + manual review)
- [ ] T007 [US3] Aligning the dataset tests with the evidence-first structure (`tests/test_eval_dataset.py`)

## Phase 3: SkilledProposer (US4)

- [ ] T008 [US4] `pip install skilled-proposer` + pyproject.toml extras update
- [ ] T009 [US4] `run_gepa_optimization()`: `instruction_proposer=SkilledProposer(extra_guidance=...)` (evidence-first + direction + KB hallucination ban), stock fallback with a warning
- [ ] T010 [US4] Test: GEPA is created with SkilledProposer; the fallback branch is tested

## Phase 4: Re-optimization & Validation (US5)

- [ ] T011 [US5] Baseline + GEPA re-run (clean `gepa_logs/`) → new `artifacts/program.json`; checking the proposals (the evidence-first rule is in them)
- [ ] T012 [US5] Valset: 0 direction violations + 0 unsupported sections; optimized score ≥ 0.850
- [ ] T013 [US5] The full test suite passes + server restart + production STRY0010010 validation (no Inbound section, components in Outbound)
- [ ] T014 [US5] Update Agent.md + README.md, commit
