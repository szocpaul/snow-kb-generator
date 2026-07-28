# Tasks: Human-Written Style for Generated KB Articles

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Tone Guidance (US1)

- [ ] T001 [US1] `BANNED_PHRASES` konstans az `eval/metric.py`-be (megosztott tiltólista: "This document describes", "seamless", "leverage", "In today's fast-paced world", stb.)
- [ ] T002 [US1] `GenerateKbFromTemplate` docstring végéhez EGYETLEN stílus-blokk hozzáfűzése (emberi hangnem + tiltólista; a meglévő szöveghez NEM nyúlunk)
- [ ] T003 [US1] Teszt: a signature docstring tartalmazza a stílus-blokkot és a tiltólista elemeit

## Phase 2: Style Judge in Metric (US2)

- [ ] T004 [US2] `StyleJudge(dspy.Signature)` az `eval/metric.py`-be: input = article_html + style_reference (KB0010015-részlet), output = score (0-1) + critique
- [ ] T005 [US2] `_style_score(html)` helper: judge-hívás `_RefreshingKimiLM`-mel; Exception → 0.5 + warning (hibatűrés, FR-002)
- [ ] T006 [US2] `rich_metric` kibővítése az 5. tengellyel; új súlyok (0.25/0.25/0.15/0.15/0.20); a kritika a feedback-be kerül
- [ ] T007 [US2] Tesztek (mock judge): gépies cikk → alacsony score + konkrét feedback; emberies → magas; judge-hiba → 0.5; súly-igazítás a meglévő tesztekben

## Phase 3: SkilledProposer Style Guidance (US3)

- [ ] T008 [US3] `additional_instructions` cseréje stílus-fókuszú guidance-re (senior engineer hangnem, változatos mondat, konkrétumok; az evidence-first + KB-szabályok MEGMARADNAK)
- [ ] T009 [US3] Teszt: a proposer az új guidance-szel jön létre (fallback ág változatlan)

## Phase 4: Small-Budget GEPA + Validation (US4)

- [ ] T010 [US4] Baseline mérés az új metric-kel (style axis látható) → `runs/baseline.json`
- [ ] T011 [US4] GEPA futás `--auto light`, `max_metric_calls=250` (Kimi task + reflection; kvótavédelem)
- [ ] T012 [US4] Ellenőrzés: optimized style-átlag > baseline style-átlag (`runs/optimized.json`); a többi tengely nem romlik
- [ ] T013 [US4] Teljes tesztcsomag zöld + éles STRY0010010 generálás + emberi review (tiltólista-regex 0 találat)
- [ ] T014 [US4] Agent.md + README.md frissítés, commit, push
