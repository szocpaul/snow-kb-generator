# Tasks: Component Hallucination Detection + Update Set Dataset Coverage

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Component Name Detection (US1)

- [x] T001 [US1] `_find_hallucinated_components(html, story_text, related_articles_context)` into `eval/metric.py` — based on the prototype in Agent.md section 30: extraction of quoted names + CamelCase + dotted identifiers, whitelist filtering, story_text check
- [x] T002 [US1] `COMPONENT_NAME_WHITELIST` constant (generic terms: "Business Rule", "Script Include", "Incident", "ServiceNow", etc.) — following the `BANNED_PHRASES` pattern, in a shared place
- [x] T003 [US1] Integration into `rich_metric`: the hallucination axis is 0 if there is a fabricated component; the feedback must name them; the KB number check (spec 004) stays untouched; fault tolerance (FR-002)
- [x] T004 [US1] Tests: (a) fabricated name → 0 + feedback (SC-001); (b) real names → 1.0; (c) **all 8 gold HTMLs pass** (SC-002, false-positive test); (d) whitelist test; (e) the hallucination is still present among the axes

## Phase 2: Gold Example with Update Set (US2)

- [x] T005 [US2] Creating the gold example with update_set_payloads: real (anonymised) Update Set XMLs for an existing or new Story + alignment of the gold article (FR-005); updating the split (decision: 5 train / 4 val or 4/5)
- [x] T006 [US2] Dataset loader check/alignment: the `update_set_payloads` field enters the examples; the existing 8 examples stay backward compatible (empty payload)
- [x] T007 [US2] Evidence: program call on the new example → the `analyze_changes` runs (trace), and its output reaches the generation (SC-003)

## Phase 3: Validation (US3)

- [x] T008 [US3] Baseline re-measurement with the new metric (`python -m eval.baseline --model local --output runs/baseline.json`, `cache=False`) → new reference documented; the 2026-08-08/09 numbers are marked as obsolete
  - Preflight (2026-08-11): llama.cpp health `{"status":"ok"}` + smoke generation OK → the run was allowed
  - **NEW REFERENCE (2026-08-11, spec 011 metric, 5 train / 4 val dataset, local Qwen, `cache=False`):** average **0.755**; axes: structure 0.917 / content 0.673 / template 0.750 / hallucination **1.000** / style 0.475 → `runs/baseline.json`
  - The extended hallucination axis is 1.000 on all 4 val examples — the baseline generation did not fabricate component names, and there are no false positives either (the axis is not noisy in a live run)
  - OBSOLETE: the 2026-08-08/09 numbers (0.773 / baseline_recheck, optimized 0.825-0.859) were produced with the old metric — the scope of the hallucination axis got stricter (KB numbers + component names), so the comparison is limited. The old baseline is saved: `runs/baseline_pre_spec011.json`
- [x] T009 [US3] Mini-GEPA decision (short run with the new metric, e.g. 60-100 calls, OR postponing) — justification in tasks.md
  - **DECISION OPTIONS (2026-08-11, the agent does NOT run GEPA — the decision is the human's):**
  - **Option A — Mini-GEPA now (60-100 calls):** arguments FOR: (1) the `analyze_changes` is now covered in the trainset (Example 5, STRY0010016) → the previous "No valid reflective examples" no-ops would disappear, and the reflection could also learn from analyze_changes; (2) the new component hallucination axis would make the T013-style error class visible to GEPA too; (3) the baseline reference is fresh (0.755), the compare gate can be run. Arguments AGAINST: (1) the metric has just changed — the noise band is not yet known from a single baseline measurement (spec 010 experience: ±0.05-0.08), it is risky to optimise a signal whose stability we have not measured; (2) the mini-GEPA on a 5 train / 4 val dataset is strongly prone to overfitting; (3) according to the Out of Scope of the spec, the GEPA run is a "separately approved validation run" — it requires human approval.
  - **Option B — Postponing (the agent's RECOMMENDATION):** arguments: (1) it is worth calibrating the noise of the new metric first with 1-2 baseline rechecks (cheap, ~10 min/run); (2) the update_set coverage is currently 1 example — so the statistical power of the analyze_changes optimisation would be weak anyway; (3) the production pipeline (server.py, program.json) is currently in an APPROVED state (after the T013 hotfix), and re-optimising would introduce risk without justification. The condition that makes Option A justified: if the human observes more component fabrication or analyze_changes quality problems in live use, or if 1-2 more update_set gold examples are created.
  - If the human chooses Option A: `max_metric_calls=60-100`, local task rollout + style judge, Kimi K3 reflection, `cache=False`, clean `gepa_logs` (the old checkpoint has an obsolete metric!), preflight (llama.cpp health + Kimi ping + smoke) mandatory; the gate: `python -m eval.compare runs/baseline.json runs/optimized.json`.
- [x] T010 [US3] Agent.md + README.md update, commit, push
