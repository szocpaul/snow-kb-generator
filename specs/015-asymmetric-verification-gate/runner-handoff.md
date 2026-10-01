# Runner handoff: 015-asymmetric-verification-gate (Prime Agent / autonomous-spec-runner)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

Hand this prompt over to the Prime Agent started on the server from the repo root, AFTER the
the repo, AFTER the `specs/015-asymmetric-verification-gate/` folder (spec.md, plan.md,
been added to the repo and committed.

---

## Starting Prompt (copy over unchanged)

```
Implement the specs/015-asymmetric-verification-gate spec. Use the
`autonomous-spec-runner` skill (a skill installed on the server — load it
and follow its instructions); the prompt below is layered ON TOP of the skill rules.

RUN MODE: the whole job must run in DEV MODE — with the SNOW_KB_DEV_MODE=1
environment variable (or the --dev flag), so that the task model is the local
llama.cpp Qwen3.8-27B instead of Kimi K3, with NO Kimi token usage.
build_lm() then connects to the local api_base in config.yaml.

FIRST: check out the `015-asymmetric-verification-gate` branch
(git checkout 015-asymmetric-verification-gate) — the spec files and all the
work live on this branch. Do NOT touch main; the commits should go here.

Work from the spec FILES: specs/015-asymmetric-verification-gate/spec.md,
plan.md, tasks.md. The tasks.md checkboxes are your external memory — check them off as you progress.

PREFLIGHT (if any of these is missing, do NOT start, report what is missing):
0.  The `015-asymmetric-verification-gate` branch is checked out and the
    the spec files are in place
0b. SNOW_KB_DEV_MODE=1 is valid: settings.pipeline.task_model == "local"
0c. The local LLM endpoint is reachable from the server:
    http://llm-server.local:8033/v1 (llama.cpp is running,
    Qwen3.8-27B is loaded, Tailscale serve is active) — a minimal
    completion call succeeds
1.  TYPESAFE_API_KEY is set and a minimal system_one call succeeds
2.  typesafe-sdk and dspy[typesafe] installed (part of the project since 013/014 —
    check it, do not reinstall)
3.  The ServiceNow PDI is reachable from the server AND the user has admin rights (the metadata
    to query tables) — one minimal table-API call on the sys_script_include
    successful
4.  The 014 measurement infrastructure is in place and works: eval/verification_measure.py,
    eval/verification_reanchor.py, eval/verification_sc_gates.py,
    data/examples/verification_labeled.json, artifacts/verification_spotcheck_cache.json
5.  pytest -q is green in the initial state (349 tests; run the suite
    WITHOUT SNOW_KB_DEV_MODE — the note in the 013 runner-report)

GATEs: pytest -q at the end of every phase; the gates of T012 are the SC-001..SC-005
exit codes. The calibration is done with the ReAnchor optimizer using an evaluation-only
on the DSPy wrapper (014 sample); the resulting threshold ONLY T009 human approval
and it can go into config.yaml afterwards. Use the project's own interpreter.

PROHIBITIONS:
- GEPA IS FORBIDDEN (in dev mode there is no Kimi K3 reflection model)
- do NOT tick the MANUAL GATE checkboxes (T003, T009) — those are for a human decision
  - do NOT touch the DSPy program (program.py, program.json), the EXISTING axes of the
eval metric, or the 004/011 story-based hallucination check
  its axes and the 004/011 story-based verification
- do NOT turn the production decision call into a DSPy module (ReAnchor is measurement only)
- the fixture script should capture ONLY the components that ALREADY EXIST on the PDI —
  Creating a NEW component is FORBIDDEN (in T001 „capture, NOT creation")
- T005 minimum: if the approved set of names has < 8 names, STOP and report —
  the sample must NOT be diluted with correlated variants
- the calibration ONLY tunes the confidence_threshold: the fail-open and the
  flag-only default behavior with a manually set safety floor, not movable
- the threshold sweep is exploratory — do NOT report the best sweep result as confirmatory
  as a result
- SC-003: if the new threshold WORSENS on the existing 24-example sample, the config does NOT
  mode changes, the report is RED — do NOT „work around" this gate
stop and report, do NOT improvise a fallback
  - in T013 the threshold sweep is exploratory — do NOT report the best sweep run as
- during the gate raise (T011) the deploy is NOT done by the runner — only the code and the
  deploy/README note; the actual restart is a human step

If you get stuck at a MANUAL GATE, stop and say so. At completion send a
summary to the main session (per-phase results, SC-gate outputs,
commit hashes), then goal.complete().
```

---

## What Is Deliberately NOT in the Prompt

- **No pasted-in task list** — the runner works from tasks.md.
- **No API key** — the preflight checks the environment.
- **No deployment instruction** — T011 is only code + a deploy/README note; the
  actual go-live is a human step (following the 014 deploy-checklist pattern).

## Human Tasks During the Run (the MANUAL GATEs)

| Task | When | What you have to do |
|---|---|---|
| T003 | after T002 | Review the dumped component list (filtering out the odd/unstable names) — the sample is only built after that |
| T009 | after T008 | Review the calibration report; approve the threshold change + the rationale into the Agent.md |

## Cleanup (after the run)

- runner stopped, tmux/heartbeat/schedule deleted
- log entry in the Agent.md (part of T013)
- backlog: review of the status of TASK-3 (the 016 candidate)
