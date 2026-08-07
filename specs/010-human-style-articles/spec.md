# Feature Specification: Human-Written Style for Generated KB Articles

**Feature Branch**: `010-human-style-articles`

**Created**: 2026-07-28

**Status**: In Progress (US1–US3 implemented and validated; US4 is in the T010c–T014 phase)

**Input**: User description: "The finished KB articles look very AI-written, not human enough. The structure and the facts are fine, but the tone is robotic: boilerplate phrases ('This document describes', 'seamless', 'leverage'), uniform sentence rhythm, generalizations instead of specifics. The goal: the articles should read as if a senior engineer had written them — the hand-written STYLE-REF is the style reference."

## Background (diagnosis)

- The `rich_metric` currently measures 4 axes (structure, content, template, hallucination) — **not style**. The basic law of GEPA: it only fixes what the metric sees. Therefore the robotic tone is invisible to the optimization.
- The STYLE-REF (hand-written SolMan article) downloaded from ServiceNow: **`data/examples/style_reference.html`** (16.5k characters) — this is the human style sample to compare against; the judge prompt gets a representative excerpt of it.
- **Gold dataset cleaned and extended (2026-07-29)**: the banned phrases ("This document describes/outlines", "seamless") were removed from the gold HTML files — previously the content axis rewarded what the style axis is going to penalize. The foreign (LDAP/auth) work_notes leftovers were deleted from the Example 5 story. New 8th example (SAP S/4HANA outbound OData) → the split is **4 train / 4 val**. Every earlier baseline number is outdated; the new reference is the fresh baseline from T010.
- **Model decision (clean measurements from 2026-07-29, `cache=False`)**: Kimi K3 **0.769** > local Qwen3.6-35B-A3B **0.733** (the old K3 number of 0.655 was contaminated by the cache). The task model nevertheless stays the **local Qwen** — against the 0.036 quality difference, the marginal cost of the GEPA rollouts (several hundred generations) is zero, and it is GEPA that must bring in the style improvement. The only remaining Kimi dependency is the GEPA reflection/proposer (K3, few calls).
- **Cache hygiene**: `cache=False` is mandatory in the measurement scripts — the first local baseline on 2026-07-29 replayed the Kimi answers from the DSPy disk cache (`~/.dspy_cache`) (false 0.655). The fix in `eval/baseline.py` has already been made.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tone Guidance in Signature (Priority: P1, "free" step)

The `GenerateKbFromTemplate` docstring is extended with a SINGLE style block (boilerplate ban list + human tone). IMPORTANT: we do NOT touch the existing instruction text — the consolidation/shortening of the docstring is the subject of a SEPARATE spec (the length increase is an accepted transitional state).

**Why this priority**: An immediate, zero-cost improvement — before measuring anything, the prompt should not ask for the robotic style in the first place.

**Independent Test**: One generation on STRY0010010, and a human review: the banned phrases do not appear.

**Acceptance Scenarios**:

1. **Given** the updated signature, **When** the pipeline generates an article, **Then** the output does not contain the elements of the ban list ("This document describes", "seamless", "leverage", "In today's fast-paced world").
2. **Given** the same Story, **When** we compare the old and the new article, **Then** the new one contains fewer generic phrases and more specifics (field name, endpoint, value).

---

### User Story 2 - Style Judge in Metric (Priority: P2)

The fifth axis of `rich_metric`: an **LLM-as-judge** (the same **local Qwen3.6-35B-A3B** as the task model) that evaluates on a 0-1 scale whether the article speaks in a human expert tone, and gives concrete criticism ("which phrase is robotic and why"). The judge prompt contains the STYLE-REF as a positive style sample.

**Deliberate trade-off**: the judge and the task use the same model (self-evaluation risk) — in exchange for zero cost. Mitigation: the judge prompt is organized around the ban list and the STYLE-REF reference (not free-form evaluation), and the SC-002 validation checks the bias on robotic/human test icons.

**Why this priority**: This makes style *measurable* — from this point on GEPA sees it and can optimize it.

**Independent Test**: Two mock articles — one robotic (full of boilerplate) and one human — the judge rates the robotic one significantly lower, and the feedback names the concrete problems.

**Acceptance Scenarios**:

1. **Given** a robotic article (full of banned phrases), **When** the style judge runs, **Then** the style score < 0.4 and the feedback contains a concrete example.
2. **Given** an article with a human tone, **When** the judge runs, **Then** the style score > 0.7.
3. **Given** the metric weights, **When** the style axis is added, **Then** the total score is updated with the weighting (structure 0.25 + content 0.25 + template 0.15 + hallucination 0.15 + style 0.20), and the existing tests are aligned and pass.

---

### User Story 3 - Style Guidance in SkilledProposer (Priority: P2)

The `run_gepa_optimization()` replaces the `additional_instructions` text of the SkilledProposer with style-focused guidance (senior engineer tone, varied sentence rhythm, specifics instead of generalisations) — the existing evidence-first and KB-hallucination rules REMAIN. The reflection/proposer model is still Kimi K3.

**Why this priority**: After the measured style (US2), this makes GEPA style-aware: based on the reflection feedback, the proposer can build generalizable style rules into the prompts.

**Independent Test**: Unit test: the proposer is created with the new guidance, the fallback branch is unchanged.

**Acceptance Scenarios**:

1. **Given** the GEPA run, **When** the proposer receives a reflection on the style axis, **Then** the suggested new instructions contain a style rule (avoiding boilerplate, specifics).
2. **Given** the creation of the proposer, **When** the code runs, **Then** the evidence-first and KB-hallucination rules are still present in the `additional_instructions`.

---

### User Story 4 - GEPA on Style (Priority: P3)

GEPA run with the **local task model** (the rollouts are free), Kimi K3 reflection, whose only goal is to prove the style improvement: the average of the style axis should improve on the valset.

**Why this priority**: It only makes sense after the measured style and the style-aware proposer. The budget is not quota-based but **time-limited**: because of the style judge every metric call is TWO local calls (article + scoring), measured ~60 sec/call. Based on measured data (T010 baseline) **`max_metric_calls=200` ≈ 2.5-3.5 hours** with the `-np 2` slots — the goal is only to prove the style improvement, that is enough; if it did not improve significantly, it could be escalated after a separate decision.

**Acceptance Scenarios**:

1. **Given** the GEPA run, **When** it completes, **Then** the style average of the optimized program ≥ baseline style average + 0.05, and the other axes degrade by at most −0.02 (per-axis data in runs/*.json, T010c).
2. **Given** the optimized program, **When** a production STRY0010010 generation happens, **Then** according to a human review the article is less robotic than the previous version.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The style rules of the signature do NOT degrade the existing behaviour (evidence-first, template conformance, the guardrails are untouched).
- **FR-002**: The style judge is deterministically fault-tolerant: if the judge call goes astray (e.g. the local server is not reachable — a VPS/server restart is a real scenario), the style axis is 0.5 (neutral) plus a warning — the metric never stops because of it.
- **FR-003**: The judge prompt contains the ban list and the STYLE-REF reference excerpt.
- **FR-004**: The GEPA run has a controlled time budget: `max_metric_calls = 200` (time limit, not quota protection — the rollouts are local; together with the judge calls ~2.5-3.5 hours with the `-np 2` slots). The reflection/proposer calls still go to Kimi K3, their number is small. `num_threads` is matched to the server slots (2).
- **FR-005**: `run_gepa_optimization()` creates the SkilledProposer with the style-focused `additional_instructions`; the existing evidence-first and KB-hallucination rules remain.
- **FR-006**: Every measurement script (baseline, GEPA, validation) runs with `cache=False` — the DSPy disk cache can replay earlier answers without model identification (lesson from the false baseline on 2026-07-29).
- **FR-007**: The measurement outputs (runs/*.json) also persist per-axis scores (`per_example` axes) — the style improvement should be verifiable automatically, not only readable from the textual feedback.
- **FR-008**: An interrupted GEPA run (e.g. a Kimi quota error in the reflection) restarted with the same `log_dir` continues from the checkpoint (DSPy 3.3.0b1); the `rm -rf gepa_logs` of a clean run is only allowed for an intentional, preflighted restart.

### Success Criteria

- **SC-001**: 0 banned phrases in the production articles (also measurable with an automatic regex check).
- **SC-002**: The style judge is validated (robotic < 0.4, human > 0.7 on the test fixtures). If it failed because of the tight thresholds: the fallback criterion is the relative gap (robotic < human − 0.3).
- **SC-003**: Human review: the final articles "look human" (subjective, but the spec records it as a goal too).
- **SC-004**: The baseline reference is the fresh measurement from T010 on the **cleaned, 8-example dataset** (4 train / 4 val, `cache=False`, new 5-axis metric) → `runs/baseline.json`. The style improvement is measured against the style-axis average there (the numbers 0.733/0.769 from 2026-07-29 refer to the old dataset and are not comparable). T010c persists the axis values into runs/*.json; the improvement threshold: **style ≥ baseline + 0.05**, the other axes degrade by at most **−0.02** — this can be checked automatically as a gate command.

## Out of Scope

- A full manual rewrite by a human (the goal is the quality of the generated articles, not the manual work).
- Fine-tuning the style judge with a separate LM (the local Qwen judge is enough for now; if the SC-002 validation shows a bias, a separate judge model should be considered).
