# Runner handoff: 016-context-selection (Prime Agent / autonomous-spec-runner)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

Hand this prompt over to the Prime Agent started on the server from the repo root, AFTER the
repo root, AFTER the `specs/016-context-selection/` folder (spec.md, plan.md,
and committed.

---

## Starting Prompt (copy over unchanged)

```
Implement the specs/016-context-selection spec. Use the
`autonomous-spec-runner` skill (a skill installed on the server — load it
and follow its instructions); the prompt below is layered ON TOP of the skill rules.

RUN MODE: the whole job must run in DEV MODE — with the SNOW_KB_DEV_MODE=1
environment variable, so that the task model is the local llama.cpp Qwen3.8-27B
and no Kimi tokens are used.

FIRST: check out the `016-context-selection` branch
(git checkout 016-context-selection) — the spec files and all the work live on
this branch. Do NOT touch main.

Work from the spec FILES: specs/016-context-selection/spec.md, plan.md, tasks.md.
The tasks.md checkboxes are your external memory — pipe them as you progress.

PREFLIGHT (if any of these is missing, do NOT start, report what is missing):
0.  The `016-context-selection` branch is checked out, the spec files are there
0b. SNOW_KB_DEV_MODE=1 is valid: settings.pipeline.task_model == "local"
0c. The local LLM endpoint is reachable (http://llm-server.local:8033/v1)
    — a minimal completion call succeeds (per KD3 of the summarize this is what
    production uses too — here it is especially critical)
1.  TYPESAFE_API_KEY is set + a minimal system_one call succeeds
2.  typesafe-sdk and dspy[typesafe] are installed (part of the project since 013)
3.  The 013–015 measurement infrastructure is in place: vendor/jev_replay.py,
    eval/jev_metrics.py, eval/verification_reanchor*.py patterns
4.  pytest -q is green in the starting state (387 tests; run the suite WITHOUT
    SNOW_KB_DEV_MODE)

GATES: pytest -q at the end of every phase; the T013 gates are the exit codes
of SC-001..SC-006. The calibration with ReAnchor, on an eval-only wrapper; the
threshold may enter the config ONLY after human approval at T012.

PROHIBITIONS:
- GEPA IS FORBIDDEN (in dev mode there is no Kimi K3 reflection model)
- do NOT tick the MANUAL GATE checkboxes (T003, T009, T012)
- do NOT touch the DSPy program (program.py, program.json), the rich_metric, the
  004/011 axes, the 014/015 verification gate and the extractor
- the story core can NEVER be "hide" (FR-004)
- the fail-open direction is ALWAYS "show" (error/low confidence → the part is included)
- the safety floor (fail-open=show, flag-only basics) is NOT movable by calibration
- if the T002 baseline shows NO measurable noise → STOP and report at the T003
  gate (the spec may stop; do NOT "manufacture" noise)
- if the T007 measurement shows quality degradation or a recall drop → the
  report is RED, report it at the T009 gate — do NOT "make it look nice"
- external service unreachable → stop and report, do NOT improvise a
- the threshold sweep is exploratory — do NOT report it as confirmatory
- deploy is NOT the runner's job

If you get stuck at a MANUAL GATE, stop and say so. At completion send a
summary to the main session (per-phase results, SC-gate outputs,
commit hashes), then goal.complete().
```

---

## Human Tasks During the Run (the MANUAL GATEs)

| Task | When | What you have to do |
|---|---|---|
| T003 | after the baseline | Noise inventory review + **fixing the SC-001 token target** (or stopping the spec if there is no noise) |
| T009 | after T007/T008 | Review of the impact report: stop if the quality degrades / the recall drops |
| T012 | after T011 | Review of the calibration report; threshold approval + justification into Agent.md |

## Cleanup (after the run)

- runner stopped, tmux/heartbeat/schedule deleted
- log entry in the Agent.md (part of T013)
- backlog: closing TASK-3 (this spec was the 016 candidate)
