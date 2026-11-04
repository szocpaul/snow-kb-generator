# Tasks: Human-Written Style for Generated KB Articles

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Tone Guidance (US1)

- [x] T001 [US1] `BANNED_PHRASES` constant into `eval/metric.py` (shared ban list: "This document describes", "seamless", "leverage", "In today's fast-paced world", etc.)
- [x] T002 [US1] Appending a SINGLE style block to the end of the `GenerateKbFromTemplate` docstring (human tone + ban list; we do NOT touch the existing text)
- [x] T003 [US1] Test: the signature docstring contains the style block and the elements of the ban list

## Phase 2: Style Judge in Metric (US2)

- [x] T004 [US2] `StyleJudge(dspy.Signature)` in `eval/metric.py`: input = article_html + style_reference (an excerpt of the style reference), output = score (0-1) + critique
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
- [x] T011 [US4] GEPA run `max_metric_calls=200` (local task rollout + judge + Kimi K3 reflection; time limit ~1.5-2 hours, `-np 4` / `num_threads=4` — FR-004, 2026-08-08: slot expansion 2→4)
  - The baseline must also be re-measured with the code after T010c for the T012 gate (the existing `runs/baseline.json` has no per-axis data): `python -m eval.baseline --model local --output runs/baseline.json` (~10 minutes, 4 val × 2 calls) — this run is PART of it, before GEPA
  - Preflight BEFORE the deletion: llama.cpp endpoint health check + Kimi K3 availability (1 cheap test call) + a 1-call smoke generation — the clean run should only start if both backends are alive (otherwise after the `rm -rf` the old checkpoint is also lost, and the run fails immediately)
  - Then: `rm -rf gepa_logs` (clean run with the new metric — the checkpoint of the old, stopped run is built on the old metric)
  - Every measurement with `cache=False` (DSPy disk cache replay bug: it replays the answers without model identification — see the spec Background "Cache hygiene")
  - Kimi quota monitoring: only the reflection/proposer may go to Kimi; the task rollout and the judge are local. In case of a quota error the compile may stop with an exception — in that case the GEPA continues from the checkpoint when it is **restarted with the same `log_dir`** (DSPy 3.3.0b1, verified); in that case you must NOT run `rm -rf gepa_logs`
  - Result: `runs/optimized.json` + a fresh `artifacts/program.json`
- [x] T012 [US4] Check: the optimized style average ≥ the baseline style average **+ 0.05**; the other axes degrade by at most **−0.02** (per-axis data in runs/*.json, based on T010c; gate-able as a single-row assertion)
  - 2026-08-08 first gate: RED (style +0.150 ✅, but structure −0.042 / content −0.021 ❌) → because of the suspected noise, a double measurement (2026-08-09): baseline re-measurement + optimized re-measurement.
  - **2×2 result (ranges):** style: base 0.450-0.463 vs opt 0.600-0.650 (**improvement without overlap ✅**); template: 0.750 vs 1.000 ✅; hallucination: 1.000 ✅; structure: base 0.917 vs opt 0.875-1.000 (**overlapping — noise**); content: base 0.682-0.766 vs opt 0.715-0.745 (**overlapping — noise**); overall: base 0.755-0.773 vs opt 0.825-0.859 ✅
  - **DECISION (human, 2026-08-09): ACCEPTED.** The "degradation" of structure/content is within the measurement noise (the baseline content axis also scattered by 0.084 between two identical runs). The −0.02 threshold is narrower than the noise band (±0.05-0.08) on a 4-example valset — see the methodological note in SC-004. Evidence: `runs/baseline.json`, `runs/baseline_recheck.json`, `runs/optimized.json`, `runs/optimized_recheck.json`.
- [x] T013 [US4] The full test suite passes + production STRY0010010 generation + ban-list regex 0 hits (the automated part) → afterwards **MANUAL GATE**: human review — the agent cannot review its own article, this checkbox can only be ticked with human approval
  - Automated part (2026-08-09, with the optimized program): 265/265 tests pass ✅; production STRY0010010 generation successful (`runs/stry0010010_optimized.json`, 7.2k characters, "Outbound REST Integration: Automatic Jira Bug Creation from Escalated ServiceNow Incidents", correct Outbound section — no direction violation) ✅; SC-001 ban-list regex: **0 hits** (10 phrases) ✅
  - REMAINDER: human review — read the `html` field of `runs/stry0010010_optimized.json`, and if it looks human, tick this checkbox
  - **First review (2026-08-09): REJECTED — hallucination found.** The human review caught that the article mentioned a 'CHG Scheduled' Business Rule name that is NOT in the Story (0 occurrences; the model fabricated it from the `example.atlassian.net` URL + the example sentence in the base docstring). Root cause chain: (a) the example in the style block of the base `signatures.py` was itself a fabricated name; (b) the CLI did not load the optimized program (`program_path` was missing) — the production test measured the base program; (c) the hallucination axis of the metric only validates KB numbers, not component names (blind spot → flagged as spec 011).
  - **Hotfix chain (2026-08-09):** (1) `signatures.py`: the ALDI example is name-free + an explicit anti-fabrication ban; (2) `artifacts/program.json` hotfix: the same sentence appended to the end of the `generate_from_template` instruction (backup: `program_pre_hotfix_backup.json`) — NOTE: the next GEPA run regenerates the artifact and inherits the sentence from signatures.py; (3) `cli.py`: `program_path="artifacts/program.json"` passed (server pattern, graceful fallback); (4) regeneration with the optimized program.
  - **Second generation (`runs/stry0010010_hotfixed.json`):** 'ALDI' 0 occurrences, the Business Rule is referred to by function ("an After Update Business Rule"), SC-001 ban list 0 hits, 265/265 tests pass.
  - **Human review (2026-08-09): APPROVED** — "I really like the generated KB article".
- [x] T014 [US4] Update Agent.md + README.md, commit, push
