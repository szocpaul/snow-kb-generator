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
  - **VÉGLEGES DÖNTÉS (emberi, 2026-08-11): Opció B — ELHALASZTVA.** Indok: a kalibráció szerint a mérési zaj (összesített ±0.03, style ±0.19) nagyobb, mint egy mini-GEPA reális várható nyeresége (+0.02-0.05) — a futás kimenetele értelmezhetetlen lenne ("mérleg-analógia": ±3 kg-ot tévedő mérlegen nem mérhető 1 kg fogyás). Feltétel az újrafuttatáshoz: a style judge zajcsökkentése (2 mintás átlagolás vagy determinisztikusabb judge) VAGY nagyobb valset → spec 012-jelölt, ld. Agent.md 32. szekció.
  - **DÖNTÉSI OPCIÓK (2026-08-11, az ágens NEM futtat GEPA-t — a döntés az emberé):**
  - **Opció A — Mini-GEPA most (60-100 call):** érvek MELLETTE: (1) az `analyze_changes` most már lefedett a trainsetben (Példa 5, STRY0010016) → a korábbi "No valid reflective examples" üresjáratok megszűnnének, a reflection az analyze_changes-re is tudna tanulni; (2) az új komponens-hallucináció tengely a GEPA-nak is láthatóvá tenné a T013-féle hibaosztályt; (3) a baseline-referencia friss (0.755), a compare gate futtatható. Érvek ELLENE: (1) a metrika frissen változott — egyetlen baseline-mérésből még nem ismert a zaj-sáv (a spec 010 tapasztalat: ±0.05-0.08), kockázatos optimalizálni olyan jel ellen, aminek a stabilitását nem mértük; (2) 5 train / 4 val dataseten a mini-GEPA erősen overfitting-hajlamos; (3) a spec Out of Scope szerint a GEPA-futás "külön jóváhagyott validációs futás" — emberi jóváhagyás kell hozzá.
  - **Opció B — Elhalasztás (az ágens JAVASLATA):** érvek: (1) előbb érdemes 1-2 baseline-recheck-kel kalibrálni az új metrika zaját (olcsó, ~10 perc/futás); (2) az update_set-lefedettség jelenleg 1 példa — a analyze_changes optimalizálásának statisztikai ereje így is gyenge lenne; (3) a produkciós pipeline (server.py, program.json) jelenleg JÓVÁHAGYOTT állapotban van (T013 hotfix után), az újraoptimalizálás kockázatot vinne be indokolatlanul. Feltétel, ami Opció A-t indokolttá teszi: ha az ember éles használatban újabb komponens-fabrikálást vagy analyze_changes-minőségproblémát tapasztal, vagy ha +1-2 update_set-es gold példa készül.
  - Ha az ember az Opció A-t választja: `max_metric_calls=60-100`, lokális task rollout + style judge, Kimi K3 reflection, `cache=False`, tiszta `gepa_logs` (régi checkpoint elavult metrikás!), preflight (llama.cpp health + Kimi ping + smoke) kötelező; a gate: `python -m eval.compare runs/baseline.json runs/optimized.json`.
  - **T009 kalibráció — baseline-recheck eredmények (2026-08-11, az ágens mérte, GEPA NEM futott):**
    - Három futás azonos kóddal / metrikával (llama.cpp lokális, health+smoke preflight OK): `runs/baseline.json` (ref, 10:14), `runs/baseline_recheck.json` (11:03), `runs/baseline_recheck2.json` (11:07).
    - Tengelyenkénti min–max (átlag a 9 példán):
      | tengely | baseline | recheck1 | recheck2 | min | max | szórás |
      |---|---|---|---|---|---|---|
      | structure | 0.917 | 0.958 | 0.958 | 0.917 | 0.958 | 0.042 |
      | content | 0.673 | 0.728 | 0.658 | 0.658 | 0.728 | 0.070 |
      | template | 0.750 | 0.750 | 0.750 | 0.750 | 0.750 | 0.000 |
      | hallucination | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 |
      | style | 0.475 | 0.562 | 0.375 | 0.375 | 0.562 | 0.188 |
    - Összesített átlag: 0.755 / 0.796 / 0.741 → zaj-sáv ≈ ±0.03 (összhangban a spec 010 tapasztalattal, ±0.05-0.08).
    - **Hallucination-stabilitás ítélete: STABIL** — mindhárom futásban 1.000, a komponens-detektálás false positive-jai NEM villognak futásonként. (A baseline példákban a modell nem fabrikált KB-számot/komponensnevet, így a tengely érzékenysége továbbra is csak gold + perturbált adaton igazolt — de a false-positive irány stabil.)
    - A legnagyobb zaj a style tengelyen van (0.188 range, LLM-judge variancia); content ±0.07, structure ±0.04, template determinisztikus.
    - **Következtetés — a mini-GEPA eredménye értelmezhető-e:** FELTÉTELESEN IGEN. A metrika-zaj (±0.03 összesítve) ismert és elfogadható; egy mini-GEPA javulás csak akkor értelmezhető valósnak, ha a compare gate szerint > ~+0.05-0.08 felett van (a zaj-sáv fölött). A style tengely zajossága miatt a style-javulások önmagukban NEM értelmezhetők; a hallucination/content/structure tengelyek megbízható jelnek tekinthetők. Opció B feltételei teljesültek (a kalibráció megtörtént); a GEPA-futás döntése továbbra is az emberé.
- [x] T010 [US3] Agent.md + README.md frissítés, commit, push
