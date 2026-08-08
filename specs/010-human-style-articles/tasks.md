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
- [x] T010c [US4] Per-axis persistence: `rich_metric` puts the axes into the Prediction, `run_baseline` writes them out — `per_example: [{score, axes: {structure, content, template, hallucination, style}, feedback}]` + top-level `axis_averages` in runs/*.json. Supplementary: `eval/compare.py` (T012 gate: `python -m eval.compare runs/baseline.json runs/optimized.json`, exit 0/1; it intentionally fails with the files from before T010c). Tests: 265/265 pass (2026-08-08)
- [ ] T011 [US4] GEPA run `max_metric_calls=200` (local task rollout + judge + Kimi K3 reflection; time limit ~1.5-2 hours, `-np 4` / `num_threads=4` — FR-004, 2026-08-08: slot expansion 2→4)
  - The baseline must also be re-measured with the code after T010c for the T012 gate (the existing `runs/baseline.json` has no per-axis data): `python -m eval.baseline --model local --output runs/baseline.json` (~10 minutes, 4 val × 2 calls) — this run is PART of it, before GEPA
  - Preflight BEFORE the deletion: llama.cpp endpoint health check + Kimi K3 availability (1 cheap test call) + a 1-call smoke generation — the clean run should only start if both backends are alive (otherwise after the `rm -rf` the old checkpoint is also lost, and the run fails immediately)
  - Then: `rm -rf gepa_logs` (clean run with the new metric — the checkpoint of the old, stopped run is built on the old metric)
  - Every measurement with `cache=False` (DSPy disk cache replay bug: it replays the answers without model identification — see the spec Background "Cache hygiene")
  - Kimi quota monitoring: only the reflection/proposer may go to Kimi; the task rollout and the judge are local. In case of a quota error the compile may stop with an exception — in that case the GEPA continues from the checkpoint when it is **restarted with the same `log_dir`** (DSPy 3.3.0b1, verified); in that case you must NOT run `rm -rf gepa_logs`
  - Result: `runs/optimized.json` + a fresh `artifacts/program.json`
- [ ] T012 [US4] Check: optimized style average ≥ baseline style average **+ 0.05**; max **−0.02** degradation on the other axes (per-axis data in runs/*.json, based on T010c; can be gated as a one-line assert)
- [ ] T013 [US4] Full test suite green + production STRY0010010 generation + ban list regex 0 matches (automatic part) → then **MANUAL GATE**: human review — the agent cannot review its own article, this checkbox can only be ticked with human approval
- [ ] T014 [US4] Update Agent.md + README.md, commit, push
