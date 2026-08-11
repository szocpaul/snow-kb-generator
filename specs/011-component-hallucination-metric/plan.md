# Implementation Plan: Component Hallucination Detection + Update Set Dataset Coverage

**Branch**: `011-component-hallucination-metric` | **Date**: 2026-08-11 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.3.0, local Qwen3.6-35B-A3B (llama.cpp, `-np 4`) + Kimi K3 reflection
- **Interpreter: `../.venv`** (the shared venv of the parent directory — see the spec 010 plan)
- Affected files: `eval/metric.py` (US1), `eval/dataset.py` + `data/examples/gold_dataset.md` (US2), `eval/baseline.py` run (US3), `tests/`
- Starting prototype: Agent.md section 30 (the spot-check code of 2026-08-09, validated with 4/4 confirmed names on the approved article)
- Precedent decisions that we do NOT change: hallucination axis weight 0.15; KB number detection (spec 004) stays untouched; cache hygiene (every measurement runs with `cache=False`)

## Architecture

```
generated article (HTML)
      │
      ▼
_find_hallucinated_components()          ← NEW (US1)
  1. candidate extraction: 'quoted names' + CamelCase + dotted identifiers
  2. filtering with a whitelist (generic terms, product names)
  3. every candidate: is it present in story_text + related_articles_context?
      │
      ├── fabricated name found → hallucination = 0, the feedback names it
      └── all good → the spec 004 KB number check continues (untouched)

gold_dataset.md + update_set_payloads     ← NEW example (US2)
      │
      ▼
program.forward() → if update_set_payloads: analyze_changes RUNS
      │
      ▼
GEPA reflection now sees the analyze_changes traces
```

## Key Decisions

1. **The existing hallucination axis is extended**, no new axis is added — the weights (0.25/0.25/0.15/0.15/0.20) and the metric structure stay unchanged, so comparability with the spec 010 results is only partially preserved (the axis semantics get stricter: KB numbers + component names).
2. **False positive-first approach**: the detection is tuned so that gold articles pass cleanly (SC-002) — it is better to let a borderline case through than to feed noise to GEPA. The whitelist is the main tool.
3. **Candidate extraction is conservative**: only strong-signal candidates (quoted names, CamelCase, dotted identifiers); plain English words are not candidates.
4. **The update_set example is 1 for now** (not 2) — the goal is to prove coverage and to stop the GEPA no-ops, not statistical power. The split 4 train / 4 val → 5 train / 4 val or 4/5 — tasks.md decides once the example is ready.
5. **Re-measuring the baseline is part of the spec** (not optional) — the metric change makes the 2026-08-08/09 numbers obsolete; the new reference is needed for every future comparison.
6. **Mini-GEPA only as a separate decision** — the spec documents the decision point, it does not automate it.

## Phases

1. **Phase 1 (US1)**: `_find_hallucinated_components()` + whitelist + metric integration + tests (fabricated name → 0; gold HTMLs → 0 false positives).
2. **Phase 2 (US2)**: gold example with update_set (real XMLs, anonymised) + dataset loader alignment + analyze_changes run evidence.
3. **Phase 3 (US3)**: baseline re-measurement + documentation + mini-GEPA decision.
