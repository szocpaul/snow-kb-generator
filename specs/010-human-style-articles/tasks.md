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
- [ ] T011 [US4] GEPA futás `max_metric_calls=200` (lokális task rollout + judge + Kimi K3 reflection; időkorlát ~2.5-3.5 óra, `-np 2` / `num_threads=2` — FR-004)
- [ ] T012 [US4] Ellenőrzés: optimized style-átlag > baseline style-átlag (`runs/optimized.json`); a többi tengely nem romlik
- [ ] T013 [US4] Teljes tesztcsomag zöld + éles STRY0010010 generálás + emberi review (tiltólista-regex 0 találat)
- [ ] T014 [US4] Agent.md + README.md frissítés, commit, push
