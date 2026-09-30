# Implementation Plan: Component Name Verification Against the Instance + Production Push Gate

**Branch**: `014-component-instance-verification` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-component-instance-verification/spec.md`

## Summary

We validate the named component names of the generated KB article against the
instance metadata BEFORE writing to ServiceNow: the clean cases with deterministic
exact-name matching, the ambiguous cases (spelling variants) with a calibrated,
typed decision — reusing the measurement infrastructure archived in 013 (recording,
replay, jev-metrics, ReAnchor wrapper, SC-gate pattern). Fail-open is mandatory;
the existing story-based protection (004/011) stays untouched alongside it.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: the existing stack (DSPy 3.x signatures untouched),
the `servicenow_client` table-API session for the metadata query,
`typesafe-sdk` + `dspy[typesafe]` for the calibrated layer (already in pyproject
since 013), vendored `src/snow_kb/vendor/jev_replay.py` + `eval/jev_metrics.py`

**Storage**: Update Set whitelist (from the story update set XMLs) + per-name
spot-check cache (JSON, part of the recording) + JSONL recording files (the 013 format)

**Testing**: pytest (the 309 suite stays green + new tests)

**Target Platform**: Linux VPS, systemd-managed FastAPI service

**Performance Goals**: the gate ≤ ~1 s p95 additional latency per article (works from the
snapshot cache; live metadata query only on cache miss/refresh)

**Constraints**: fail-open is mandatory (FR-002); 0 false positives on the gold articles
(SC-001); minimum 20-example labelled sample for SC-002 (the lesson of 013);
pinned decision model version

**Scale/Scope**: one new module (`verification.py`) + metric extension +
gate integration, ~4 affected files + tests

## Constitution Check

*GATE: there is still no formal constitution file in the repo — the check was made
against the implicit principles recorded in Agent.md.*

| Principle (implicit) | Check |
|---|---|
| "Measured, not claimed" | ✅ — the SCs are numeric, replay-based measurement, minimum sample size |
| Fail-open / error tolerance | ✅ — FR-002, on both layers (spec Edge Cases) |
| The pipeline's GEPA program stays untouched | ✅ — the gate is outside the program, before the write path |
| Baseline first | ✅ — Phase 0: the component names of the current articles + instance snapshot are recorded |
| Existing protection untouched | ✅ — the 004/011 story-based check is unchanged (FR-006) |

## Architecture

```text
Story fetch + Update Set fetch (unchanged)
        │
        ▼
┌─ pipeline.py ────────────────────────────────────────────────────┐
│  ExtractChange → GenerateKbFromTemplate (unchanged)              │
│                                                                  │
│  NEW: verify_component_names(article_html, update_set_text)              │
│    ┌─ deterministic core: candidate extraction (011 pattern)     │
│    │   → 1. Update Set whitelist (get_update_set_changes), 2. what is not in it: per-name spot-check in the instance (cached)               │
│    │   → exists / does not exist (clean cases)                   │
│    └─ ambiguous cases → calibrated decision (TypeSafe Noul,      │
│        pinned version): "does this name refer to this real            │
│        komponensre utal-e?"                                      │
│    → JSONL recording (013 format) + fail-open (FR-002)         │
│    → config.behavior: flag (default) / strip / block             │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
servicenow_client.create_kb_article — the gate runs BEFORE the _live path;
non-existent names → work_notes flag with the measured confidence
```

On the eval side: the metric gets an instance axis (US1) — alongside the existing
story-based hallucination axis, backwards compatible.

## Key Decisions

1. **The default behaviour of the gate: FLAG (work_notes), not strip and not block** —
   removing the component name from the article is a much bolder intervention than the KB-number strip
   was (it dismantles the meaning of the text); blocking, on the other hand, risks availability.
   (Alternative: strip following the 004 pattern — rejected, the names present in the sentence context
   strip gives an unreadable article; blocking — rejected, fail-closed.)
   *The config switch can be tightened at any time, if the measurement data supports it.*
2. **Two-layer check: deterministic core + calibrated layer only for the ambiguous
   cases** — it decides "exists/does not exist" by exact name match (fact, free);
   the Jev only kicks in for the writing variants. (Alternative: a Jev call for every name —
   rejected, unnecessary cost and calibration noise in the clean cases.)
3. **Hierarchical ground truth: Update Set first + per-name spot-check** — the
   primary whitelist is the content of the story's Update Set (the `get_update_set_changes`
   already brings; what is there is real AND the subject of the article). What is not in the update set,
   for that, no full instance snapshot is made, but a targeted per-name spot check
   ("is there a Script Include named X?"), cached. (Alternative: full
   instance snapshot — rejected, unnecessary data movement; "Update Set only" — rejected,
   false positives on the legitimate already-existing component references, e.g. `incident`
   table or affected existing script.) The cache is part of the recording → the replay
   stays byte-identical (SC-004). **Edge case**: if the story has no Update Set,
   the gate only goes up to the spot-check layer (because of the 011 dataset gap this is common
   can — the measurement will show how much).
4. **Per-component decision** (not per-article) — the suspicious ones can be named in the work_notes
   name; the 013 work_notes flag pattern asks for this. (Alternative: per-article bool —
   rejected, it does not localize the bug.)
5. **Reuse of the 013 infrastructure, without generalization** — the
   the jev_replay/jev_metrics/ReAnchor pattern is carried over into the verification context;
   we do NOT refactor it into a "general decision framework" (YAGNI; if 015 also becomes a decision
   there will be, then the abstraction is worth it).
6. **Pinned decision model** for the calibrated layer (for the reason known since 013:
   model swap = baseline re-measurement).
7. **The calibration tool is ReAnchor** following the 013 T012 pattern (evaluation-only
   DSPy wrapper; the production call remains a direct SDK call).

## Phases

1. **Phase 0 – Baseline + snapshot**: taking an instance metadata snapshot
   (table/field/script names, from the PDI, into the file); the existing gold + one freshly
   inventory of the component names of a generated article sample against the snapshot —
   how many "does not exist" candidates there are NOW (this is the first numerical
   is the proof).
2. **Phase 1 (US1)**: metric instance axis + tests (mock snapshot).
3. **Phase 2 (US2)**: `verification.py` deterministic core + gate integration in front of the
   in front of `servicenow_client._create_kb_article_live` + work_notes flag + tests.
4. **Phase 3 (US3)**: calibrated layer for the ambiguous cases + recording + tests.
5. **Phase 4 – Measurement**: labeled sample (≥20 examples: real names + intentional
   spelling variants + fabricated names), live capture + replay + ReAnchor +
   SC-001..SC-004 gates with exit codes.

## Complexity Tracking

There is no constitution violation — the table stays empty.
