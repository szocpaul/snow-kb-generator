# Tasks: Hallucination-Free KB Article Generation

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Gold Dataset Sanitization (US1)

- [ ] T001 [US1] Replace fictional KB numbers (KB0012345, KB0012346) with `KBXXXXXXX` placeholder in `data/examples/gold_dataset.md`
- [ ] T002 [US1] Add dataset test: no fictional KB numbers in gold articles (`tests/test_eval_dataset.py`)

## Phase 2: Hallucination Detection in Metric (US2)

- [ ] T003 [US2] Implement hallucination axis in `eval/metric.py` (extract KB\d{6,} from pred HTML, compare against story_text, exclude placeholders; score + feedback)
- [ ] T004 [US2] Add metric tests: fictional KB → penalized + feedback, real KB → no penalty, placeholder/N-A → no penalty (`tests/test_eval_metric.py`)
- [ ] T005 [US2] Rebalance metric weights to 0.3/0.3/0.2/0.2 and update existing weight-sensitive tests

## Phase 3: Post-Generation Guardrail (US3)

- [ ] T006 [US3] Implement `strip_hallucinated_references(html, story_text)` in `src/snow_kb/pipeline.py` (remove hallucinated KB references, keep real ones, log warnings)
- [ ] T007 [US3] Wire guardrail into `generate_kb_article()` before push (and into dry-run output for consistency)
- [ ] T008 [US3] Add guardrail tests: strip fictional, keep real, idempotent on clean HTML (`tests/test_pipeline.py` vagy új modul)

## Phase 4: Re-optimization & Validation (US4)

- [ ] T009 [US4] Re-run baseline (`python -m eval.baseline`) → friss `runs/baseline.json`
- [ ] T010 [US4] Re-run GEPA (`python -m eval.gepa_optimize --auto light`, tiszta `gepa_logs/`) → új `artifacts/program.json`
- [ ] T011 [US4] Validate: valset generálások hallucináció-mentesek (guardrail-mérés 0 találat)
- [ ] T012 [US4] Run full pytest suite (208+ teszt zöld, no regressions)
- [ ] T013 [US4] Update `Agent.md` (új szekció: spec 004 eredményei) és restart szerver + éles STRY0010010 validáció
