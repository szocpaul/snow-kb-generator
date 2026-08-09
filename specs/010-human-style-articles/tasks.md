# Tasks: Human-Written Style for Generated KB Articles

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Tone Guidance (US1)

- [x] T001 [US1] `BANNED_PHRASES` konstans az `eval/metric.py`-be (megosztott tiltólista: "This document describes", "seamless", "leverage", "In today's fast-paced world", stb.)
- [x] T002 [US1] `GenerateKbFromTemplate` docstring végéhez EGYETLEN stílus-blokk hozzáfűzése (emberi hangnem + tiltólista; a meglévő szöveghez NEM nyúlunk)
- [x] T003 [US1] Teszt: a signature docstring tartalmazza a stílus-blokkot és a tiltólista elemeit

## Phase 2: Style Judge in Metric (US2)

- [x] T004 [US2] `StyleJudge(dspy.Signature)` az `eval/metric.py`-be: input = article_html + style_reference (KB0010015-részlet), output = score (0-1) + critique
- [x] T005 [US2] `_style_score(html)` helper: judge-hívás a **lokális Qwen endpointtal** (ugyanaz, mint a task modell); Exception → 0.5 + warning (hibatűrés, FR-002)
- [x] T006 [US2] `rich_metric` kibővítése az 5. tengellyel; új súlyok (0.25/0.25/0.15/0.15/0.20); a kritika a feedback-be kerül
- [x] T007 [US2] Tesztek (mock judge): gépies cikk → alacsony score + konkrét feedback; emberies → magas; judge-hiba → 0.5; súly-igazítás a meglévő tesztekben

## Phase 3: SkilledProposer Style Guidance (US3)

- [x] T008 [US3] `additional_instructions` cseréje stílus-fókuszú guidance-re (senior engineer hangnem, változatos mondat, konkrétumok; az evidence-first + KB-szabályok MEGMARADNAK)
- [x] T009 [US3] Teszt: a proposer az új guidance-szel jön létre (fallback ág változatlan)

## Phase 4: Small-Budget GEPA + Validation (US4)

- [x] T009b [US4] A `scripts/run_*_baseline.py` ad-hoc mérési scriptek konszolidálása: a baseline-futtatás legyen `eval/baseline.py` CLI-jével (`python -m eval.baseline --model local|kimi --output ...`) elérhető, a `scripts/` mappa törlendő — T010 előtt kell
- [x] T010 [US4] Baseline mérés az új metric-kel (style axis látható), `cache=False`-szal, a tisztított 8 példás dataseten (4 train / 4 val) → `runs/baseline.json` — EZ az új referencia (SC-004); a régi 0.733/0.769 számok elavult datasetre vonatkoznak
- [x] T010c [US4] Per-axis perzisztálás: a `rich_metric` az axes-t a Predictionbe teszi, a `run_baseline` kiírja — `per_example: [{score, axes: {structure, content, template, hallucination, style}, feedback}]` + top-level `axis_averages` a runs/*.json-ben. Kiegészítve: `eval/compare.py` (T012 gate: `python -m eval.compare runs/baseline.json runs/optimized.json`, exit 0/1; a T010c előtti fájlokkal szándékosan elhasal). Tesztek: 265/265 zöld (2026-08-08)
- [x] T011 [US4] GEPA futás `max_metric_calls=200` (lokális task rollout + judge + Kimi K3 reflection; időkorlát ~1.5-2 óra, `-np 4` / `num_threads=4` — FR-004, 2026-08-08: slot-bővítés 2→4)
  - A T012 gate-hez a baseline-t is újra kell mérni a T010c utáni kóddal (a meglévő `runs/baseline.json` per-axis nélküli): `python -m eval.baseline --model local --output runs/baseline.json` (~10 perc, 4 val × 2 hívás) — ez a futás RÉSZE, a GEPA előtt
  - Preflight a törlés ELŐTT: llama.cpp endpoint health-check + Kimi K3 elérhetőség (1 olcsó teszthívás) + 1 call-os smoke generálás — a clean run csak akkor induljon, ha mindkét backend él (különben az `rm -rf` után a régi checkpoint is elvész, és a futás azonnal elhasal)
  - Ezután: `rm -rf gepa_logs` (tiszta futás az új metric-kel — a régi, leállított futás checkpointja elavult metric-re épül)
  - Minden mérés `cache=False`-szal (DSPy disk cache replay-bug: modell-azonosítás nélkül játssza vissza a válaszokat — ld. spec Background "Cache-higiénia")
  - Kimi kvóta-figyelés: csak a reflection/proposer mehet Kimire; a task rollout és a judge lokális. Kvóta-hiba esetén a compile kivétellel megállhat — ilyenkor **ugyanazzal a `log_dir`-rel újraindítva** a GEPA a checkpointból folytat (DSPy 3.3.0b1, verifikálva); ilyenkor NEM szabad `rm -rf gepa_logs`-t futtatni
  - Eredmény: `runs/optimized.json` + friss `artifacts/program.json`
- [x] T012 [US4] Ellenőrzés: optimized style-átlag ≥ baseline style-átlag **+ 0.05**; a többi tengely max **−0.02** romlás (per-axis adatok a runs/*.json-ben, T010c alapján; egy soros assert-ként gate-elhető)
  - 2026-08-08 első gate: PIROS (style +0.150 ✅, de structure −0.042 / content −0.021 ❌) → zaj-gyanú miatt dupla mérés (2026-08-09): baseline újramérés + optimized újramérés.
  - **2×2 eredmény (tartományok):** style: base 0.450-0.463 vs opt 0.600-0.650 (**átfedés nélküli javulás ✅**); template: 0.750 vs 1.000 ✅; hallucination: 1.000 ✅; structure: base 0.917 vs opt 0.875-1.000 (**átfedő — zaj**); content: base 0.682-0.766 vs opt 0.715-0.745 (**átfedő — zaj**); összesített: base 0.755-0.773 vs opt 0.825-0.859 ✅
  - **DÖNTÉS (emberi, 2026-08-09): ELFogadva.** A structure/content "romlás" a mérési zajon belül van (a baseline content-je is 0.084-et szór két azonos futás közben). A −0.02 küszöb 4 példás valseten a zaj-sávnál (±0.05-0.08) szűkebb — lásd SC-004 módszertani megjegyzés. Bizonyíték: `runs/baseline.json`, `runs/baseline_recheck.json`, `runs/optimized.json`, `runs/optimized_recheck.json`.
- [x] T013 [US4] Teljes tesztcsomag zöld + éles STRY0010010 generálás + tiltólista-regex 0 találat (automatikus rész) → utána **MANUÁLIS KAPU**: emberi review — az agent a saját cikkét nem review-zhatja, ez a checkbox csak emberi jóváhagyással pipálható
  - Automatikus rész (2026-08-09, optimized programmal): 265/265 teszt zöld ✅; éles STRY0010010 generálás sikeres (`runs/stry0010010_optimized.json`, 7.2k karakter, "Outbound REST Integration: Automatic Jira Bug Creation from Escalated ServiceNow Incidents", helyes Outbound-szekció — direction violation nincs) ✅; SC-001 tiltólista-regex: **0 találat** (10 fordulat) ✅
  - MARADÉK: emberi review — olvasd el a `runs/stry0010010_optimized.json` html mezőjét, és ha emberinek tűnik, pipáld ki ezt a checkboxot
  - **Első review (2026-08-09): ELUTASÍTVA — hallucináció találat.** Az emberi review kiszúrta: a cikk 'ALDI: CHG Scheduled' Business Rule-nevet említett, ami a Story-ban NEM szerepel (0 előfordulás; a modell az `aldi.atlassian.net` URL-ből + a base docstring példamondatából fabrikálta). Root cause lánc: (a) a base `signatures.py` style-blokk példája maga is fabrikált név volt; (b) a CLI nem töltötte be az optimized programot (`program_path` hiányzott) — az éles teszt a base programot mérte; (c) a metrika hallucináció-tengelye csak KB-számokat validál, komponensneveket nem (vakfolt → spec 011-jelölt).
  - **Hotfix-lánc (2026-08-09):** (1) `signatures.py`: ALDI-példa név-mentesre + explicit anti-fabrikációs tiltás; (2) `artifacts/program.json` hotfix: ugyanaz a mondat a `generate_from_template` instrukció végére (backup: `program_pre_hotfix_backup.json`) — FIGYELEM: a következő GEPA-futás újragenerálja az artifactot, a mondatot a signatures.py-ból örökli; (3) `cli.py`: `program_path="artifacts/program.json"` átadva (server-minta, graceful fallback); (4) újragenerálás az optimized programmal.
  - **Második generálás (`runs/stry0010010_hotfixed.json`):** 'ALDI' 0 előfordulás, a Business Rule funkcióval hivatkozva ("an After Update Business Rule"), SC-001 tiltólista 0 találat, 265/265 teszt zöld.
  - **Emberi review (2026-08-09): JÓVÁHAGYVA** — "nagyon tetszik a generált KB cikk".
- [x] T014 [US4] Agent.md + README.md frissítés, commit, push
