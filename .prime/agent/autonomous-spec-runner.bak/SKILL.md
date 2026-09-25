---
name: autonomous-spec-runner
description: >-
  Launch, monitor, and close out dedicated autonomous Prime Agent workers for
  spec-kit spec implementation, long optimization runs (GEPA), and measurement
  tasks. Use when the user wants a spec implemented "autonomously", a
  long-running agent for a multi-hour task, a runner/worker agent, or asks to
  apply the long-running-agents workflow (tmux + prime-agent --autonomous +
  goal + gates + completion message).
---

# Autonomous Spec Runner

Battle-tested workflow for delegating a bounded, spec-backed task to a dedicated
autonomous Prime Agent worker. Built from real runs: spec 010 GEPA optimization
(200 call, 3.5h), spec 011 implementation (~35 min), calibration runs (~25 min).

## When to use

- "Implement spec NNN autonomously" / "futtasd autonóm agenttel"
- Multi-hour runs (GEPA, big refactors, migrations) that must survive detach
- Measurement/monitoring tasks with a clear file-artifact output

Do NOT use it for quick interactive edits, single commands, or exploratory work —
do those inline in the current session.

## The workflow

### 1. Preflight (BEFORE anything destructive or long)

- Verify every external backend the task needs, from THIS machine:
  `curl -s -m 10 -o /dev/null -w '%{http_code}' <endpoint>/health` + one real smoke call.
- Verify auth tokens are alive (refresh expired ones with a minimal `pi -p "Say OK"` call).
- Only then allow destructive steps (`rm -rf gepa_logs` etc.) — a failed preflight
  must abort BEFORE them, never after.

### 2. Launch in tmux (resident, daemon-backed)

```bash
tmux new-session -d -s <runner-name> 'cd <project> && prime-agent   --autonomous   --autonomous-gate "<verifiable command with exit code>"   --autonomous-gate-retries 5   --autonomous-max-turns 40   --autonomous-max-continuations 8   --autonomous-max-tokens 200000   --autonomous-timeout-ms 10800000   --goal "<durable objective, one sentence>"   "<short task prompt — see below>"'
prime-agent rename <new-id> <runner-name>
```

tmux + interactive client = the worker stays resident, appears in
`prime-agent list`, and is attachable. `-p`/print mode is one-shot; avoid for long runs.

### 3. Task prompt: short, spec-referencing, with explicit constraints

The durable task state lives in FILES (spec.md/plan.md/tasks.md), not in the prompt —
tasks.md checkboxes are compaction-proof memory. The prompt contains only:

1. WHAT: "Execute specs/<spec>/tasks.md T001-T0NN in order; tick checkboxes as you go"
2. Interpreter/environment traps, e.g. "use `../.venv/bin/python` — the project has NO own .venv"
3. Where to fetch data if external sources are needed, and what to do if unreachable (stop and report)
4. HARD CONSTRAINTS in caps where it matters:
   - "GEPA run FORBIDDEN — decision belongs to the human" (for prep/calibration tasks)
   - "Do NOT touch production pipeline files" (when out of scope)
   - "Do NOT tick checkboxes marked as HUMAN GATE"
5. Completion: "when done, send a summary to agent `main-session` via agent_message, then goal.complete()"

### 4. Gates: must be exit-code-verifiable

Good gates: `pytest -q`, a compare script with numeric thresholds (`eval/compare.py`),
a python one-liner asserting output artifacts exist and parse.
Bad gates: subjective checks, files that don't exist yet at gate time, thresholds
tighter than the measurement noise (on small valsets measure noise FIRST — see below).

### 5. Monitoring: pick ONE

- **Completion message** (preferred): instruct the runner to `agent_message` the
  parent session when done. Zero polling; the architecture delivers it.
- **Heartbeat** (`rlm_heartbeat`, 15m, `delivery_mode="follow_up"`): for long runs
  where mid-run anomalies matter. Instruction must say: report ONLY on meaningful
  change (new ticked checkbox, error, completion); stay silent otherwise. DELETE the
  heartbeat when the run ends.

### 6. Infra-watcher (only for multi-hour runs on fragile backends)

A second, cheap agent doing periodic `curl` health checks. Hard-won rules:

- Smoke timeout must exceed the backend's busy-queue time (30s was too short under
  4-slot GEPA load → false alarm). Use 90s.
- Alert ONLY if health fails AND an independent progress signal is stale
  (e.g. log mtime older than 10 min). Saturation ≠ dead server.
- Green = silent log line; red = message the runner (mode=auto) AND the human session.
- Always cancel its schedule + stop it at cleanup.

### 7. Cleanup checklist (always)

- [ ] Stop runner agents (`prime-agent stop <name>`), kill tmux sessions
- [ ] Cancel schedules (`prime-agent schedule cancel <id>`), delete heartbeats
- [ ] Verify the runner's claims independently: tests pass, artifacts exist, git log
- [ ] Human decision points stay with the human (review gates, tradeoff acceptance)
- [ ] Commit + push; document outcome in the project's journal file

## Measurement-noise lesson (GEPA/eval tasks)

On small validation sets (≤8 examples), a single metric run can swing ±0.05-0.08
(LLM temperature + LLM-judge variance). Before trusting ANY improvement claim or
setting gate thresholds, run a calibration: measure the SAME artifact 2-3 times and
use the observed noise band. A result is real only if the improvement range does not
overlap the baseline range. Defer optimization runs whose expected gain is smaller
than the noise band.

## Known traps (learned the expensive way)

- Project venv location: always verify the actual interpreter path; don't assume `.venv/`.
- A CLI may not load the optimized program the server loads — check what the
  production path actually executes before "production-testing" anything.
- `--host 0.0.0.0` binds IPv4 only; a hostname resolving to IPv6 yields HTTP 0.
- `nohup ... & disown` inside `bash -c` with captured output can hang the wrapper —
  verify the real server process separately; better: use a systemd unit for servers.
- GEPA resume: same `log_dir` resumes from checkpoint (DSPy ≥3.3); never `rm -rf`
  after an interrupted run you intend to resume.
