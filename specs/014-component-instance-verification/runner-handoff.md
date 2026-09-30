# Runner handoff: 014-component-instance-verification (Prime Agent / autonomous-spec-runner)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

Hand this prompt over to the Prime Agent started on the server from the repo root, AFTER the
the `specs/014-component-instance-verification/` folder (spec.md, plan.md, tasks.md) has
been added to the repo and committed.

---

## Starting Prompt (copy over unchanged)

```
Implement the specs/014-component-instance-verification spec. Use the
`autonomous-spec-runner` skill (a skill installed on the server — load it
and follow its instructions); the prompt below is layered ON TOP of the skill rules.

RUN MODE: the whole job must run in DEV MODE — with the SNOW_KB_DEV_MODE=1
environment variable (or the --dev flag), so that the task model is the local
llama.cpp Qwen3.8-27B instead of Kimi K3, with NO Kimi token usage.
build_lm() then connects to the local api_base in config.yaml.

FIRST: check out the `014-component-instance-verification` branch
(git checkout 014-component-instance-verification) — the spec files and all the
work live on this branch. Do NOT touch main; the commits should go here.

Work from the spec FILES: specs/014-component-instance-verification/spec.md,
plan.md, tasks.md. The tasks.md checkboxes are your external memory — check them off as you progress.

PREFLIGHT (if any of these is missing, do NOT start, report what is missing):
0.  The `014-component-instance-verification` branch is checked out and the
    the spec files are in place
0b. SNOW_KB_DEV_MODE=1 is valid: settings.pipeline.task_model == "local"
0c. The local LLM endpoint is reachable from the server:
    http://llm-server.local:8033/v1 (llama.cpp is running,
    Qwen3.8-27B is loaded, Tailscale serve is active) — a minimal
    completion call succeeds
1.  TYPESAFE_API_KEY is set and a minimal system_one call succeeds
2.  typesafe-sdk and dspy[typesafe] installed in the project environment (since 013
    is part of pyproject — check it, do not reinstall needlessly)
3.  The ServiceNow instance is reachable from the server (the spot-check and the update-set
    because of the query) — a minimal table-API call is successful
4.  pytest -q is green in the starting state (309 tests; env-sensitive test:
    run the suite without SNOW_KB_DEV_MODE, the dev mode is the LLM-based
    is needed for the runs — a note from the 013 runner report)

GATEs: at the end of every phase pytest -q; the measurement gates of T013 are the
SC-001..SC-004 exit codes. In T013 the calibration is done with the ReAnchor
optimizer on an evaluation-only DSPy wrapper (the 013 T012 pattern); the resulting
threshold goes into the verification_gate.confidence_threshold field of config.yaml.
Use the project's own interpreter/environment (see pyproject.toml).

PROHIBITIONS:
- GEPA is FORBIDDEN (neither a baseline re-run nor an optimization — in dev mode
  there is no Kimi K3 reflection model)
- do NOT tick the MANUAL GATE checkboxes (T005, T014) — they wait for a human decision
  - do NOT touch the DSPy program (program.py, program.json), the EXISTING axes of the
eval metric, or the 004/011 story-based hallucination check
  (the instance axis is a NEW axis ALONGSIDE, not instead — FR-006)
  - do NOT turn the production decision call into a DSPy module (the ReAnchor wrapper
- do NOT turn the production decision call into a DSPy module (the ReAnchor wrapper
  - verification_gate.enabled stays false by default; turning the gate on is the
decision of the T014 MANUAL GATE
  - if an external service (ServiceNow / TypeSafe / local LLM) is unreachable →
stop and report, do NOT improvise a fallback
  - in T013 the threshold sweep is exploratory — do NOT report the best sweep run as
a confirmatory result; the confirmatory gate is the 0.7 designated in the spec
  confirmatory result; the confirmatory gate is the 0.7 designated in the spec
problem — report it as a fact and stop at the T005 gate (this is a legitimate
  outcome)

If you get stuck at a MANUAL GATE, stop and say so. At completion send a
summary to the main session (per-phase results, SC-gate outputs,
commit hashes), then goal.complete().
```

---

## What Is Deliberately NOT in the Prompt

- **No pasted-in task list** — the runner works from tasks.md (playbook: "the prompt
  falls away, the spec remains").
- **No API key** — the preflight checks the environment, the key never ends up in the prompt
  or in a file.
- **No mandatory scheduling** — the monitoring relies on the completion message.

## Human Tasks During the Run (the MANUAL GATEs)

| Task | When | What you have to do |
|---|---|---|
| T005 | after the baseline | Review the T003/T004 inventory — how many "does not exist" names there are today; if 0, the spec can stop here |
| T014 | after the measurement | Approve the gate default behaviour (KD1: flag) + the fail-open tradeoff; review the SC gates; if the threshold changes, write the justification into Agent.md |

## Cleanup (after the run, per point 9 of the playbook)

- runner stopped, tmux/heartbeat/schedule deleted
- Agent.md log entry (part of T015): facts, commit hashes, decisions, lessons
- backlog: close TASK-2 (this spec was the suggested 014)
