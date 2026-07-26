# Tasks: Real Related KB Articles from ServiceNow

**Spec**: [spec.md](spec.md)

## Phase 1: Client + Pipeline (US1, US2)

- [ ] T001 [US1] `ServiceNowClient.search_kb_articles(query, limit=5)` implementálása + mock teszt
- [ ] T002 [US2] Pipeline: KB keresés a Story short_description alapján, `related_articles_context` felépítése, hibatűrő (warning + üres)
- [ ] T003 [US2] Program/Signature: `related_articles_context` input a template-generáló lépésbe; üres → "N/A" instrukció

## Phase 2: Guardrail + Metric (US3)

- [ ] T004 [US3] `strip_hallucinated_references(..., known_refs="")` kiterjesztés + tesztek (false positive = 0)
- [ ] T005 [US3] Metric hallucination axis: gold `related_articles_context` figyelembevétele + teszt

## Phase 3: Re-optimization & Validation (US4)

- [ ] T006 [US4] Baseline + GEPA újrafuttatás (tiszta `gepa_logs/`) → új `artifacts/program.json`
- [ ] T007 [US4] Teljes tesztcsomag + éles STRY0010010 validáció (valódi KB számok vagy N/A a cikkben)
- [ ] T008 [US4] Agent.md + README.md frissítés, commit
