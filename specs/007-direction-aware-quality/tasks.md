# Tasks: Direction-Aware KB Quality

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Direction-Aware Metric (US1)

- [ ] T001 [US1] `detect_direction(story_text)` helper az `eval/metric.py`-be (inbound/outbound/both/unknown, kulcsszó-számlálás)
- [ ] T002 [US1] Direction violation ellenőrzés a `template_adherence`-ben: nem alkalmazható szekció kitöltve → büntetés + explicit feedback ("Direction violation: ...")
- [ ] T003 [US1] Tesztek: outbound+kitöltött Inbound → büntetés; outbound+N/A → OK; both/unknown → kihagyott ellenőrzés (`tests/test_eval_metric.py`)

## Phase 2: Signature Rule (US2)

- [ ] T004 [US2] `GenerateKbFromTemplate` docstring: kategorikus irányszabály + megosztott komponensek elhelyezési szabálya

## Phase 3: SkilledProposer (US3)

- [ ] T005 [US3] `pip install skilled-proposer` + pyproject.toml dev/extras frissítés
- [ ] T006 [US3] `run_gepa_optimization()`: `instruction_proposer=SkilledProposer(extra_guidance=...)` (irányszabály + "never invent KB numbers/titles"), fallback stock proposerre warning-gal
- [ ] T007 [US3] Teszt: a GEPA a SkilledProposer-rel jön létre (mock import), fallback ág tesztelve

## Phase 4: Re-optimization & Validation (US4)

- [ ] T008 [US4] Baseline + GEPA újrafuttatás (tiszta `gepa_logs/`) → új `artifacts/program.json`; ellenőrzés: a proposals tartalmazzák az irányszabályt
- [ ] T009 [US4] Valset-ellenőrzés: 0 direction violation; optimized score ≥ 0.850
- [ ] T010 [US4] Teljes tesztcsomag zöld + szerver restart + éles STRY0010010 validáció (Inbound = N/A, komponensek az Outboundban)
- [ ] T011 [US4] Agent.md + README.md frissítés, commit
