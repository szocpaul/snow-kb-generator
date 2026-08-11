# Tasks: Komponens-hallucináció detektálás + Update Set dataset-lefedettség

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Komponensnév-detektálás (US1)

- [x] T001 [US1] `_find_hallucinated_components(html, story_text, related_articles_context)` az `eval/metric.py`-be — az Agent.md 30. szekcióbeli prototípusból: idézett nevek + CamelCase + dotted azonosítók kinyerése, whitelist-szűrés, story_text-ellenőrzés
- [x] T002 [US1] `COMPONENT_NAME_WHITELIST` konstans (általános terminusok: "Business Rule", "Script Include", "Incident", "ServiceNow", stb.) — a `BANNED_PHRASES` mintájára, közös helyen
- [x] T003 [US1] Integráció a `rich_metric`-be: a hallucination tengely 0, ha van fabrikált komponens; a feedback nevesítse őket; a KB-szám-check (spec 004) érintetlen marad; hibatűrés (FR-002)
- [x] T004 [US1] Tesztek: (a) fabrikált név → 0 + feedback (SC-001); (b) valódi nevek → 1.0; (c) **mind a 8 gold HTML átmegy** (SC-002, false-positive teszt); (d) whitelist-teszt; (e) axes-ben a hallucination továbbra is szerepel

## Phase 2: Update Set-es gold példa (US2)

- [x] T005 [US2] Gold példa készítése update_set_payloads-szal: valódi (anonymizált) Update Set XML-ek egy meglévő vagy új Story-hoz + a gold cikk igazítása (FR-005); a split frissítése (döntés: 5 train / 4 val vagy 4/5)
- [x] T006 [US2] Dataset-loader ellenőrzés/igazítás: az `update_set_payloads` mező bekerül a példákba; a meglévő 8 példa visszafelé kompatibilis (üres payload)
- [x] T007 [US2] Bizonyíték: program-hívás az új példán → az `analyze_changes` lefut (trace), és a kimenete eljut a generálásba (SC-003)

## Phase 3: Validáció (US3)

- [x] T008 [US3] Baseline újramérés az új metrikával (`python -m eval.baseline --model local --output runs/baseline.json`, `cache=False`) → új referencia dokumentálva; a 2026-08-08/09-i számok elavultként jelölve
  - Preflight (2026-08-11): llama.cpp health `{"status":"ok"}` + smoke generálás OK → a futás engedélyezett volt
  - **ÚJ REFERENCIA (2026-08-11, spec 011 metrika, 5 train / 4 val dataset, lokális Qwen, `cache=False`):** átlag **0.755**; tengelyek: structure 0.917 / content 0.673 / template 0.750 / hallucination **1.000** / style 0.475 → `runs/baseline.json`
  - A kiterjesztett hallucination-tengely mind a 4 val példán 1.000 — a baseline-generálás nem fabrikált komponensnevet, és false positive sincs (a tengely nem zajos éles futásban sem)
  - ELAVULT: a 2026-08-08/09-i számok (0.773 / baseline_recheck, optimized 0.825-0.859) a régi metrikával készültek — a hallucination tengely scope-ja szigorodott (KB-számok + komponensnevek), az összevetés korlátozott. A régi baseline mentve: `runs/baseline_pre_spec011.json`
- [x] T009 [US3] Mini-GEPA döntés (rövid futás az új metrikával, pl. 60-100 call, VAGY elhalasztás) — indoklás a tasks.md-be
  - **DÖNTÉSI OPCIÓK (2026-08-11, az ágens NEM futtat GEPA-t — a döntés az emberé):**
  - **Opció A — Mini-GEPA most (60-100 call):** érvek MELLETTE: (1) az `analyze_changes` most már lefedett a trainsetben (Példa 5, STRY0010016) → a korábbi "No valid reflective examples" üresjáratok megszűnnének, a reflection az analyze_changes-re is tudna tanulni; (2) az új komponens-hallucináció tengely a GEPA-nak is láthatóvá tenné a T013-féle hibaosztályt; (3) a baseline-referencia friss (0.755), a compare gate futtatható. Érvek ELLENE: (1) a metrika frissen változott — egyetlen baseline-mérésből még nem ismert a zaj-sáv (a spec 010 tapasztalat: ±0.05-0.08), kockázatos optimalizálni olyan jel ellen, aminek a stabilitását nem mértük; (2) 5 train / 4 val dataseten a mini-GEPA erősen overfitting-hajlamos; (3) a spec Out of Scope szerint a GEPA-futás "külön jóváhagyott validációs futás" — emberi jóváhagyás kell hozzá.
  - **Opció B — Elhalasztás (az ágens JAVASLATA):** érvek: (1) előbb érdemes 1-2 baseline-recheck-kel kalibrálni az új metrika zaját (olcsó, ~10 perc/futás); (2) az update_set-lefedettség jelenleg 1 példa — a analyze_changes optimalizálásának statisztikai ereje így is gyenge lenne; (3) a produkciós pipeline (server.py, program.json) jelenleg JÓVÁHAGYOTT állapotban van (T013 hotfix után), az újraoptimalizálás kockázatot vinne be indokolatlanul. Feltétel, ami Opció A-t indokolttá teszi: ha az ember éles használatban újabb komponens-fabrikálást vagy analyze_changes-minőségproblémát tapasztal, vagy ha +1-2 update_set-es gold példa készül.
  - Ha az ember az Opció A-t választja: `max_metric_calls=60-100`, lokális task rollout + style judge, Kimi K3 reflection, `cache=False`, tiszta `gepa_logs` (régi checkpoint elavult metrikás!), preflight (llama.cpp health + Kimi ping + smoke) kötelező; a gate: `python -m eval.compare runs/baseline.json runs/optimized.json`.
- [x] T010 [US3] Agent.md + README.md frissítés, commit, push
