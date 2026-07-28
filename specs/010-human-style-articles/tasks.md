# Tasks: Human-Written Style for Generated KB Articles

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Tone Guidance (US1)

- [ ] T001 [US1] `BANNED_PHRASES` constant into `eval/metric.py` (shared ban list: "This document describes", "seamless", "leverage", "In today's fast-paced world", etc.)
- [ ] T002 [US1] appending a SINGLE style block to the end of the `GenerateKbFromTemplate` docstring (human tone + ban list; we do NOT touch the existing text)
- [ ] T003 [US1] Test: the signature docstring contains the style block and the elements of the ban list

## Phase 2: Style Judge in Metric (US2)

- [ ] T004 [US2] `StyleJudge(dspy.Signature)` into `eval/metric.py`: input = article_html + style_reference (STYLE-REF excerpt), output = score (0-1) + critique
- [ ] T005 [US2] `_style_score(html)` helper: judge call with `_RefreshingKimiLM`; Exception → 0.5 + warning (error tolerance, FR-002)
- [ ] T006 [US2] extending `rich_metric` with the 5th axis; new weights (0.25/0.25/0.15/0.15/0.20); the critique goes into the feedback
- [ ] T007 [US2] Tests (mock judge): robotic article → low score + concrete feedback; human-like → high; judge error → 0.5; weight adjustment in the existing tests

## Phase 3: SkilledProposer Style Guidance (US3)

- [ ] T008 [US3] replacing `additional_instructions` with style-focused guidance (senior engineer tone, varied sentences, specifics; the evidence-first + KB rules REMAIN)
- [ ] T009 [US3] Test: the proposer is created with the new guidance (fallback branch unchanged)

## Phase 4: Small-Budget GEPA + Validation (US4)

- [ ] T010 [US4] Baseline measurement with the new metrics (style axis visible) → `runs/baseline.json`
- [ ] T011 [US4] GEPA run `--auto light`, `max_metric_calls=250` (Kimi task + reflection; quota protection)
- [ ] T012 [US4] Check: optimized style average > baseline style average (`runs/optimized.json`); the other axes do not degrade
- [ ] T013 [US4] Full test suite green + production STRY0010010 generation + human review (ban list regex 0 matches)
- [ ] T014 [US4] Update Agent.md + README.md, commit, push
