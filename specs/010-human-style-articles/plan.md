# Implementation Plan: Human-Written Style for Generated KB Articles

**Branch**: `010-human-style-articles` | **Date**: 2026-07-28 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy **3.3.0** (updated from 3.3.0b1 on 2026-08-07, 258/258 tests pass; the GEPA `log_dir` checkpoint-resume is verified — an interrupted run can be continued with the same `log_dir`)
- **Interpreter: `../.venv`** (the shared venv of the parent directory — the project has NO `.venv` of its own, and it is NOT the system Python; see Agent.md) — every gate and measurement command runs with it
- **Task + judge LM: local Qwen3.6-35B-A3B** (llama.cpp, `http://llm-server.local:8033/v1`) — clean measurements from 2026-07-29 (`cache=False`, old dataset): K3 0.769 > local 0.733; the zero marginal cost was decisive (GEPA rollouts)
- **Dataset**: cleaned, 8 examples (4 train / 4 val, 2026-07-29) — the gold HTML files are boilerplate-free, the style reference is in `data/examples/`; the baseline must be re-measured on it (T010)
- **GEPA reflection/proposer: Kimi K3** (`_RefreshingKimiLM`) — the only remaining Kimi dependency, with few calls
- Judge and task use the same model — a deliberate trade-off (zero cost); the SC-002 validation (robotic/human test fixtures) checks the bias of the judge
- `cache=False` is mandatory in the measurement scripts (lesson from the false cache replay, 2026-07-29)
- Affected files: `src/snow_kb/signatures.py` (US1), `eval/metric.py` (US2), `eval/gepa_optimize.py` (US3), `tests/`

## Architecture

```
                        (US1) signature docstring + style block
                                    │
generated article ──► rich_metric ───┼── structure / content / template / hallucination
                    │               └── (US2) style_judge() [local Qwen, LLM-as-judge]
                    │                     score 0-1 + specific critique
                    ▼
              GEPA reflection sees the feedback
                    │
                    ▼
         (US3) SkilledProposer(additional_instructions = style guidance)
                    │  generalizable style rules into the prompts
                    ▼
         (US4) GEPA (max_metric_calls=200, local rollout + Kimi K3 reflection)
                    → proving the style axis improvement
```

## Key Decisions

1. **The judge is a `dspy.Signature` in metric.py** (`StyleJudge`: article_html + style_reference → score + critique), **with the local Qwen LM** (the same endpoint as the task model). Not a separate module — the metric is its place.
2. **Fault tolerance:** a judge exception (e.g. the local server is not reachable) → score=0.5 + warning log; the metric never stops.
3. **Weights:** 0.25 structure + 0.25 content + 0.15 template + 0.15 hallucination + 0.20 style. The thresholds of the existing tests must be aligned.
4. **The style reference is baked into the judge prompt**: a representative excerpt of the style reference article (not the full HTML — token economy).
5. **The boilerplate ban list is a shared constant** (`BANNED_PHRASES`): the signature block, the judge prompt and the SC-001 regex check use the same list.
6. **US3 only replaces the `additional_instructions` text** on the existing SkilledProposer instance — the fallback logic and the prompt_model (Kimi K3) stay unchanged.
7. **No docstring consolidation** (separate spec, backlog).
8. **Per-axis persistence (FR-007):** `run_baseline` also writes the axis values into runs/*.json (`per_example[].axes`) — otherwise the T012 style threshold cannot be automated (currently only `average_score` + textual feedback are written).
9. **Cache hygiene:** every measurement path (`run_baseline`, GEPA compile, validation) runs with a `cache=False` LM — the disk cache can replay the answers of another model (false baseline on 2026-07-29). The fix in `eval/baseline.py` has already been made.

## Phases

1. **Phase 1 (US1)**: signature style block + `BANNED_PHRASES` constant + tests.
2. **Phase 2 (US2)**: `StyleJudge` signature + `style_score()` in the metric + fault tolerance + tests (with a mock judge).
3. **Phase 3 (US3)**: SkilledProposer style guidance + test.
4. **Phase 4 (US4)**: per-axis persistence (T010c, done on 2026-08-08) → GEPA run (T011, with a preflight) (`max_metric_calls=200`, local task + judge + Kimi K3 reflection; ~1.5-2 hours, `-np 4` / `num_threads=4`) → proving the style axis improvement with the `eval/compare.py` gate (T012) + production validation + docs.
