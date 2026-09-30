# Runner Handoff: 013-audience-typed-decision (Prime Agent / autonomous-spec-runner)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

Hand this prompt over to the Prime Agent started on the server from the repo root, AFTER the
`specs/013-audience-typed-decision/` folder (spec.md, plan.md, tasks.md) has been added to the repo
and committed.

---

## Starting Prompt (copy over unchanged)

```
Implement the specs/013-audience-typed-decision spec. Use the
`autonomous-spec-runner` skill (a skill installed on the server — load it
and follow its instructions); the prompt below is layered ON TOP of the skill rules.

RUN MODE: the whole job must run in DEV MODE — with the SNOW_KB_DEV_MODE=1
environment variable (or the --dev flag), so that the task model is the local
llama.cpp Qwen3.8-27B instead of Kimi K3, with NO Kimi token usage.
build_lm() then connects to the local api_base in config.yaml.

FIRST: check out the `013-audience-typed-decision` branch
(git checkout 013-audience-typed-decision) — the spec files and all the work
live on this branch. Do NOT touch main; the commits must go here.

Work from the spec FILES: specs/013-audience-typed-decision/spec.md, plan.md,
tasks.md. The tasks.md checkboxes are your external memory — tick them as you go.

PREFLIGHT (if any of these is missing, do NOT start, report what is missing):
0.  The `013-audience-typed-decision` branch is checked out and the 4 spec files are there
0b. SNOW_KB_DEV_MODE=1 is valid: settings.pipeline.task_model == "local"
0c. The local LLM endpoint is reachable from the server:
    http://llm-server.local:8033/v1 (llama.cpp is running,
    Qwen3.8-27B is loaded, Tailscale serve is active) — a minimal
    completion call succeeds
1.  TYPESAFE_API_KEY is set and a minimal system_one call succeeds
2.  pip install typesafe-sdk and pip install "dspy[typesafe]" succeed in the
    project environment (public PyPI, extra index NOT needed)
3.  The gold dataset examples contain a runnable story input (not just the gold article)
4.  pytest -q is green in the initial state

GATEs: pytest -q at the end of every phase; the T012 measurement gates are the exit codes of
SC-001..SC-004. In T012 the calibration is done with the ReAnchor optimizer on an
evaluation-only DSPy wrapper; the resulting threshold goes into the
audience_decision.confidence_threshold field of config.yaml. Use the project's own
interpreter/environment (see pyproject.toml).

PROHIBITIONS:
- GEPA is FORBIDDEN (neither a baseline re-run nor optimization — in dev mode there is no
  Kimi K3 reflection model anyway, this prohibition is consistent with that)
- do NOT tick the MANUAL GATE checkboxes (T005, T011, T013) — they wait for a human
  decision
- do NOT touch the DSPy program (program.py, program.json) or the eval metric
- do NOT turn the production decision call into a DSPy module (the ReAnchor wrapper
  is for measurement only, see T012)
- external service unreachable → stop and report, do NOT improvise a
  fallback
- in T012 the threshold sweep is exploratory — do NOT report the best sweep as a
  confirmatory result; the confirmatory gate is the 0.7 designated in the spec

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
- **No mandatory schedule** — the monitoring relies on the completion message; a 15-minute
  heartbeat only if the run is expected to be long (it may be, due to the live recording in T012).

## Human Tasks During the Run (the MANUAL GATEs)

| Task | When | What you have to do |
|---|---|---|
| T005 | after the baseline | Review of the 9 gold audience labels and the baseline result |
| T011 | after the US2 implementation | Approval of the fail-open + developer-default tradeoff before the production run |
| T013 | after the T012 measurement | Review of the SC-gate results; if the threshold changes, the rationale goes into Agent.md |

## Cleanup (after the run, per point 9 of the playbook)

- runner stopped, tmux/heartbeat/schedule deleted
- Agent.md log entry (part of T014): facts, commit hashes, decisions, lessons learned
- backlog: status report on the restart condition of the verification-layer spec
