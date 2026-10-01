# Implementation Plan: Asymmetric Calibration + Moving the Gate into the Writing Component

**Branch**: `015-asymmetric-verification-gate` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-asymmetric-verification-gate/spec.md`

## Summary

Two focused changes on the 014 verification gate: (1) the calibration switches to a
metric with asymmetric costs (the false "exists" is multiple times more expensive), on
a PDI-native fixture sample; (2) the gate moves into the write path of
`servicenow_client`, so that every call path goes through a single, unavoidable gate.
The 013/014 measurement infrastructure is reused unchanged.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: unchanged (typesafe-sdk + dspy[typesafe] already in the project);
the fixture creation runs on the existing `servicenow_client` table API + the `scripts_pdi/` sample

**Storage**: PDI fixture (Story + Update Set, on the instance side), labelled sample under
`data/examples/`, spot-check cache + JSONL recording (existing)

**Testing**: pytest (the 349-test suite stays green + new tests)

**Target Platform**: Linux VPS, systemd-managed FastAPI service + PDI

**Performance Goals**: the gate move adds no extra latency (the call is the same, it just
lives elsewhere); the calibration is offline, one trainset run (ReAnchor)

**Constraints**: fail-open unchanged (FR-005); the safety floor (fail-open + flag-only
base behaviour) is NOT movable by calibration (spec Edge Cases); SC-003 regression gate
on the existing 24-example sample

**Scale/Scope**: ~3 affected files (`verification.py`, `servicenow_client.py`,
`pipeline.py`) + eval extension + tests + fixture script

## Constitution Check

*GATE: there is still no formal constitution — the check is based on the implicit
principles of Agent.md.*

| Principle (implicit) | Check |
|---|---|
| "Measured, not claimed" | ✅ — SC-002/SC-003 are numeric, the report goes into a file |
| Fail-open | ✅ — FR-005 unchanged, tested (the SC-004 pattern) |
| Baseline first | ✅ — Phase 0: fixture + the asymmetric cost of the current threshold recorded |
| The existing protection stays untouched | ✅ — FR-006 |
| Backward compatibility | ✅ — SC-003: in case of degradation the threshold does not go live |

## Architecture

```text
CURRENT (014)                           TARGET (015)
─────────────                           ─────────
pipeline.py                             pipeline.py
  └ _apply_verification_gate()            └ (the gate call disappears)
  └ create_kb_article()                   └ create_kb_article()
       └ _live: the write                      └ _live: THE GATE IS HERE (inside)
                                                       → flag/strip/block
                                                       → 1 decision, 1 recording
Other (future) path → WITHOUT the gate   Other call path → through the same gate
```

Calibration (offline, part of the measurement — separated from production):

```text
PDI fixture (Story + Update Set, real components)
   → labelled sample (real / spelling variant / fabricated)
   → ReAnchor with the ASYMMETRIC metric (FALSE_POS_EXISTS_COST : FALSE_NEG_COST)
   → threshold report (before/after, symmetric comparison, rationale into a file)
   → config.confidence_threshold (or stays + rationale)
   → regression: the existing 24-example sample re-measured (SC-003)
```

## Key Decisions

1. **The cost ratio: 10:1** (false „exists" : false „does not exist") — the reference sample
   (fit_thresholds.py) value, and it also protects us in our domain: the hallucination that slips through
   misleads the reader, the unnecessary signal is noise. (Alternative: 5:1 or 20:1 —
   the exact ratio must be supported by a sensitivity analysis in the calibration report;
   if the threshold is insensitive to the ratio, the simplest 10:1 remains.)
2. **The fixture is built on the PDI, with a script** (following `scripts_pdi/`): Story + Update Set
   + registration of the components that exist on the PDI — reproducible, in case of a PDI rebuild
   re-runnable. (Alternative: manual fixture — rejected, not reproducible.)
3. **The gate moves into the inside of `_create_kb_article_live`** (not a wrapper, not a decorator):
   the call contains a single entry point. The pipeline-level call is removed.
   (Alternative: decorator on the client — rejected, magic beyond the signature;
   the purest form of the v1 sample according to the „inside the tool" principle is the internal call.)
4. **The calibration only tunes `confidence_threshold`** — the fail-open and the
   flag-only default behavior with a manually set safety floor (spec Edge Cases).
   (The reference sample works the same way: DENY_BELOW stays manual.)
5. **Regression gate on the existing sample (SC-003)** — the new threshold only takes effect if
   into effect, if it does not worsen on the 24-example sample. (Alternative: measure only on the new sample —
   rejected, the old sample is the single longer-standing witness of the production behavior.)
6. **The calibration runs on the combined sample of the 24 + fixture examples**, but the dev-origin
   „exists" labels excluded from the PDI measurement (FR-002) — the instance facts do not
   support it. (This is the deliberate closing of the 014 SC-001 RED.)

## Fixture content (KD2 details — based on the 2026-10-01 discussion)

**The Story topic**: the snow-kb-generator project itself, as an integration project —
„Wiring up the ServiceNow-side webhook reception and KB draft generation". The story text
with a structure similar to the real project (problem, change summary, affected components).

**The content of the Update Set**: components that **ALREADY EXIST** on the PDI go into it
(update set capture of existing records — we do not create anything new). The fixture
script selects 4–6 existing components per type following the `scripts_pdi/` pattern
(e.g. one Script Include, one Business Rule, one System Property, one table field),
captures them into an Update Set, and the Story text is written for these real names.
(Alternative: creating new, project-like components — REJECTED, the scripted
Scripted REST/Business Rule manufacturing carries unnecessary risk; the "project look" of
the names is cosmetics, not measurement value.)

**The component names are not hard-coded**: the fixture script dumps the selected names
into an artifact file on the first run → a human glance (the MANUAL GATE in tasks.md)
before the sample construction relies on them. On a PDI rebuild the stock components are
present on every fresh PDI → the fixture is re-runnable.

**The mechanism of the component discovery** (no guessing): the fixture script queries the
metadata tables of the PDI through the existing table-API client (`sys_script_include`,
`sys_script`, `sys_properties`, `sys_dictionary` — `active=true`, `global` scope,
name filtering, `sys_updated_on` preference). Selection criteria: active, global scope,
a "proper" identifier-name, type diversity. **The logic is inverted**: the script first
fetches the real names, and the Story text is written for THESE — this guarantees that
every name in the story exists on the PDI (this is the point of the fixture).

**The derivation of the labelled sample** from the dumped name set:
- **real**: the exact form of the selected component names
- **spelling variant**: mechanical variants (space-separated/hyphenated/different
  lower-case-upper-case forms) — to test the 2nd mechanism
- **fabricated**: plausible-looking but non-existent names — the hallucination class
- **type mismatch**: a real name searched in the wrong table (e.g. the Script Include name
  searched as a Business Rule) — to test the 3rd mechanism

## Phases

1. **Phase 0 – Fixture + baseline**: the creation of the PDI-native Story + Update Set
   with a script; the fixture-integrity gate (SC-001); the asymmetric cost of the current
   threshold (0.7) recorded on the existing 24 examples (baseline first).
2. **Phase 1 (US1)**: building the labelled sample from the fixture (real / spelling
   variant / fabricated, mechanically derived), the labels committed.
3. **Phase 2 (US2)**: asymmetric metric + ReAnchor run + report
   (threshold decision + rationale + regression on the old sample).
4. **Phase 3 (US3)**: gate move into the client + tests (the direct call is gated too; no
   double decision/recording) + deployment note into deploy/README.
5. **Phase 4 – Closure**: the SC-001..SC-005 gates with exit codes, Agent.md, backlog.

## Complexity Tracking

There is no constitution violation — the table stays empty.
