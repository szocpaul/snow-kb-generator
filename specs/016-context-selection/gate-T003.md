# T003 MANUAL GATE — spec 016 baseline + noise inventory review

**Date**: 2026-10-02 (runner)
**Status**: WAITING for a human decision — the runner STOPPED, it does not continue to T007.

## Gate subject (tasks.md T003)

1. Review of the baseline + noise inventory.
2. **The SC-001 token target is FIXED HERE** (plan.md KD6 — with a plan update).
3. If there is no measurable noise → the spec stops (the 014 "0 hits" pattern).

## There IS measurable noise — the spec can continue (runner finding)

There is no need to "manufacture noise": the deterministic inventory shows
**1825 / 8540 context tokens (21.4%)** are noise candidates on the 9 gold examples.

## Baseline summary (artifacts/context_baseline.json)

- **Model**: local Qwen3.8-27B (DEV mode, `cache=False`) — the T007 after-measurement
  runs with the SAME one (tasks.md T002/a).
- **Token method**: llama.cpp `/tokenize` (Qwen's real tokenizer) — the
  after-measurement uses the SAME one (tasks.md T002/b).
- **rich_metric baseline average**: **0.8417** (per example: 0.8467, 0.8817,
  0.7883, 0.7583, 0.8885, 0.8274, 0.7491, 0.9575, 0.8777) — measured together
  with the style judge, at capture time.
- **Total context tokens** (story + update set parts): **8540**.
- **Noise-candidate tokens** (deterministic heuristic: meta field + near-empty):
  **1825 (21.4%)**.

### Noise inventory structure (per example, the same pattern on all 9 gold examples)

| Part | Tokens/example | Nature |
|---|---|---|
| `story:number` | 14 | identifier meta |
| `story:state` | 7 | workflow meta |
| `story:assigned_to` | 8 | person meta |
| `story:assignment_group` | 8 | team meta |
| `story:work_notes` | 33–193 | dev log (hide OR summarize candidate) |
| `story:comments` | 30–82 | comment (hide OR summarize candidate) |

- **Obvious hide candidates** (number/state/assigned_to/assignment_group):
  37 tokens/example × 9 = **333 tokens (3.9%)**.
- **Summarize candidates** (work_notes/comments): ~1492 tokens; 60–70%
  With summarization, a further ~900–1000 token saving is expected.
- Update set payload is only in the gold-5 (of 3536 context tokens 2971 are
  US); the related-article noise is not measurable in the gold dataset (there is no
  related_articles_context) — this is the limit of the baseline, marked in the report.

## Proposed SC-001 target (the HUMAN fixes it)

**Proposal: ≥ 5% context-token reduction** on the gold examples, without quality
degradation (alongside SC-002).

Justification: the obvious hide candidates alone give 3.9% (recall risk
without it), the summarize band is expected to add 6–10% above this. The 5% is conservative,
available, and it is not a bombshell — it comes from the baseline inventory. The full prompt
(template + signature overhead) ~3200–8100 tokens/example, so the measurement ON CONTEXT
5% of the full prompt amounts to ~1–2% — the report shows both numbers.

**Alternatives**: 3% (taking only the sure admin hide) | 10% (using the summarize
band fully — riskier for SC-002).

## Decision options

- **APPROVE + target** (e.g. "5%") → the runner fixes the plan.md KD6 and the
  `artifacts/context_sc001_target.json`, then T007-T008 (measurement +
  recall gate) → T009 gate.
- **A DIFFERENT TARGET** → the same process with the given value.
- **STOP the spec** → it goes into the runner report with a justification, the
  T004-T006 code stays inactive with the `enabled=false` config.

## Evidence files

- `artifacts/context_baseline.json` (report, byte-identical from replay)
- `artifacts/context_baseline_generations.json` (raw generations + usage)
- `artifacts/context_baseline_tokens.json` (per-part token inventory)
- `artifacts/context_baseline_metrics.json` (rich_metric + style judge scores)
