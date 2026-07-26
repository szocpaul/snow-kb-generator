# Tasks: Real Related KB Articles from ServiceNow

**Spec**: [spec.md](spec.md)

## Phase 1: Client + Pipeline (US1, US2)

- [ ] T001 [US1] Implement `ServiceNowClient.search_kb_articles(query, limit=5)` + mock test
- [ ] T002 [US2] Pipeline: KB search based on the Story short_description, building `related_articles_context`, error-tolerant (warning + empty)
- [ ] T003 [US2] Program/Signature: `related_articles_context` input into the template-generating step; empty → "N/A" instruction

## Phase 2: Guardrail + Metric (US3)

- [ ] T004 [US3] Extend `strip_hallucinated_references(..., known_refs="")` + tests (false positive = 0)
- [ ] T005 [US3] Metric hallucination axis: take the gold `related_articles_context` into account + test

## Phase 3: Re-optimization & Validation (US4)

- [ ] T006 [US4] Re-run baseline + GEPA (clean `gepa_logs/`) → new `artifacts/program.json`
- [ ] T007 [US4] Full test suite + production STRY0010010 validation (real KB numbers or N/A in the article)
- [ ] T008 [US4] Update Agent.md + README.md, commit
