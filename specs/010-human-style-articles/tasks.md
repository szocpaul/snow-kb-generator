# Tasks: Human-Written Style for Generated KB Articles

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Tone Guidance (US1)

- [x] T001 [US1] `BANNED_PHRASES` constant into `eval/metric.py` (shared ban list: "This document describes", "seamless", "leverage", "In today's fast-paced world", etc.)
- [x] T002 [US1] Appending a SINGLE style block to the end of the `GenerateKbFromTemplate` docstring (human tone + ban list; we do NOT touch the existing text)
- [x] T003 [US1] Test: the signature docstring contains the style block and the elements of the ban list

## Phase 2: Style Judge in Metric (US2)

- [x] T004 [US2] `StyleJudge(dspy.Signature)` into `eval/metric.py`: input = article_html + style_reference (STYLE-REF excerpt), output = score (0-1) + critique
- [x] T005 [US2] `_style_score(html)` helper: judge call with the **local Qwen endpoint** (the same as the task model); Exception → 0.5 + warning (fault tolerance, FR-002)
- [x] T006 [US2] Extending `rich_metric` with the 5th axis; new weights (0.25/0.25/0.15/0.15/0.20); the critique goes into the feedback
- [x] T007 [US2] Tests (mock judge): robotic article → low score + concrete feedback; human-like → high; judge error → 0.5; weight alignment in the existing tests

## Phase 3: SkilledProposer Style Guidance (US3)

- [x] T008 [US3] Replacing `additional_instructions` with style-focused guidance (senior engineer tone, varied sentence, specifics; the evidence-first + KB rules REMAIN)
- [x] T009 [US3] Test: the proposer is created with the new guidance (the fallback branch is unchanged)

## Phase 4: Small-Budget GEPA + Validation (US4)

- [x] T009b [US4] Consolidating the ad-hoc measurement scripts `scripts/run_*_baseline.py`: the baseline run should be reachable via the CLI of `eval/baseline.py` (`python -m eval.baseline --model local|kimi --output ...`), the `scripts/` folder is to be deleted — needed before T010
- [x] T010 [US4] Baseline measurement with the new metric (style axis visible), with `cache=False`, on the cleaned 8-example dataset (4 train / 4 val) → `runs/baseline.json` — THIS is the new reference (SC-004); the old 0.733/0.769 numbers refer to the outdated dataset
- [ ] T011 [US4] GEPA run `max_metric_calls=200` (local task rollout + judge + Kimi K3 reflection; time limit ~2.5-3.5 hours, `-np 2` / `num_threads=2` — FR-004)
- [ ] T012 [US4] Check: optimized style average > baseline style average (`runs/optimized.json`); the other axes do not degrade
- [ ] T013 [US4] Full test suite green + production STRY0010010 generation + human review (ban list regex 0 matches)
- [ ] T014 [US4] Update Agent.md + README.md, commit, push
