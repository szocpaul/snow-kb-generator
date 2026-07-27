# Tasks: Evidence-First KB Generation

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Evidence-Aware Metric (US1)

- [ ] T001 [US1] `detect_direction(story_text)` helper az `eval/metric.py`-be (inbound/outbound/both/unknown, kulcsszó-számlálás)
- [ ] T002 [US1] Direction violation ellenőrzés a `template_adherence`-ben: nem alkalmazható irány-szekció kitöltve → büntetés + "Direction violation: ..." feedback
- [ ] T003 [US1] Unsupported-section penalty: gold szerint N/A/hiányzó szekció a pred-ben kitöltve → büntetés + "Unsupported section: ..." feedback
- [ ] T004 [US1] Tesztek: direction violation büntet; N/A → OK; both/unknown → kihagyott; unsupported section → feedback (`tests/test_eval_metric.py`)

## Phase 2: Signature + Dataset (US2, US3)

- [ ] T005 [US2] `GenerateKbFromTemplate` docstring: evidence-first (menü, nem mandátum; támogatatlan szekció KIHAGYÁS; irány-corollary; megosztott komponensek szabálya)
- [ ] T006 [US3] Gold dataset: (a) N/A-only szekcióblokkok törlése (5 db irány-ellentétes blokk); (b) fiktív 'related articles' sorok törlése (5 db KBXXXXXXX placeholder sor — unsupported content; a valós hivatkozások a live keresésből jönnek) (script + manuális review)
- [ ] T007 [US3] Dataset tesztek igazítása az evidence-first struktúrához (`tests/test_eval_dataset.py`)

## Phase 3: SkilledProposer (US4)

- [ ] T008 [US4] Telepítés a HELYES venv-be: `../.venv/bin/pip install skilled-proposer` (PyPI: 0.1.1, Python ≥3.10, dspy ≥3.0 — ellenőrizve) + `pyproject.toml` extras frissítés (`gepa = ["skilled-proposer>=0.1.1"]`, a `dev` extras rá hivatkozik). FONTOS: NEM rendszer-pip!
- [ ] T009 [US4] `run_gepa_optimization()`: `instruction_proposer=SkilledProposer(extra_guidance=...)` (evidence-first + irány + KB-hallucináció tiltás), stock fallback warning-gal. Import: `from skilled_proposer import SkilledProposer`
- [ ] T010 [US4] Teszt: GEPA SkilledProposer-rel jön létre; fallback ág tesztelve

## Phase 4: Re-optimization & Validation (US5)

- [ ] T011 [US5] Baseline + GEPA újrafuttatás (tiszta `gepa_logs/`) → új `artifacts/program.json`; proposals ellenőrzése (evidence-first szabály benne)
- [ ] T012 [US5] Valset: 0 direction violation + 0 unsupported section; optimized score ≥ 0.850
- [ ] T013 [US5] Teljes tesztcsomag zöld + szerver restart + éles STRY0010010 validáció (nincs Inbound szekció, komponensek az Outboundban)
- [ ] T014 [US5] Agent.md + README.md frissítés, commit
