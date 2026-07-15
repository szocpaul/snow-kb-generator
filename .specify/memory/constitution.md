<!--
=== Sync Impact Report ===
Version change: 0.0.0 (empty template) → 1.0.0
Modified principles:
  - (none — initial ratification)
Added sections:
  - I. Spec-Driven Pipeline Architecture
  - II. DSPy-First (No Hardcoded Prompts)
  - III. Test-First (NON-NEGOTIABLE)
  - IV. Secrets & Configuration Hygiene
  - V. ServiceNow API Isolation
  - Additional Constraints (Technology Stack)
  - Development Workflow (Spec-Driven / SDD)
  - Governance
Removed sections:
  - (none)
Templates requiring updates:
  - .specify/templates/plan-template.md        ✅ aligned (Constitution Check implicit)
  - .specify/templates/spec-template.md         ✅ aligned (scope derived from stack)
  - .specify/templates/tasks-template.md        ✅ aligned (test tasks mandatory)
Follow-up TODOs:
  - (none)
===
-->

# snow-kb-generator Constitution

## Core Principles

### I. Spec-Driven Pipeline Architecture

The system is an orchestrated pipeline. Each stage (fetch, assemble, analyze,
generate, format, push) is a distinct, replaceable module. The DSPy `Module`
is the single source of truth for generation logic; orchestration (`pipeline.py`)
and transport (`cli.py`, `server.py`) MUST NOT contain LLM prompting logic.

Rationale: Separation of concerns allows the GEPA optimizer to tune generation
without touching ServiceNow I/O or HTTP transport.

### II. DSPy-First (No Hardcoded Prompts)

All instructions to the LLM MUST be declared as typed `dspy.Signature`
docstrings or composed via named predictors (`dspy.Predict`,
`dspy.ChainOfThought`). Hardcoded prompt strings, ad-hoc string templates, and
inlined few-shot demos are FORBIDDEN. Global LM is configured via
`dspy.configure(lm=...)`; per-module overrides require explicit justification.

Rationale: Only declarative Signatures can be optimized by GEPA and audited.

### III. Test-First (NON-NEGOTIABLE)

Every new module, Signature, or ServiceNow client method MUST ship with pytest
coverage. The Red-Green-Refactor cycle applies: tests are written (and fail)
before the implementation is accepted. External LM and ServiceNow HTTP calls
MUST be mocked in tests; no test may require live network or secret material.
The suite MUST stay green (current baseline: 173 tests) before any merge.

Rationale: Live LM/HTTP tests are flaky and non-reproducible; a deterministic
suite is the only acceptable quality gate.

### IV. Secrets & Configuration Hygiene

Secrets (ServiceNow credentials, API keys) MUST live exclusively in `.env`
and be loaded via `pydantic-settings` `SecretStr`. Secrets MUST NEVER be
printed, logged in plaintext, or committed. `.env` is `.gitignore`d; only
`.env.example` is version-controlled. Structured settings come from
`config.yaml`; both are unified through the single `Settings` object.

Rationale: A single leak of `SNOW_PASSWORD` or an API key invalidates the trust
model of the whole integration.

### V. ServiceNow API Isolation

All ServiceNow Table API access MUST flow through `servicenow_client.py`.
No other module may import `requests` or construct ServiceNow URLs directly.
The client raises typed exceptions (`StoryNotFound`, `AuthError`,
`ServiceNowError`) and MUST support a `dry_run` mode that reads mock JSON from
`data/sample_stories/` so the pipeline runs without network or credentials.

Rationale: Centralized HTTP enables uniform retry, timeout, and error mapping;
`dry_run` keeps development and CI decoupled from the ServiceNow instance.

## Additional Constraints

**Technology stack requirements (fixed):**

- Language: Python 3.12+
- Framework: DSPy 3.2.x (Signatures + Modules; GEPA for optimization)
- Data model: Pydantic v2 + pydantic-settings
- ServiceNow integration: Table API via `requests`
- Web transport: FastAPI + Uvicorn (sync endpoints, to keep DSPy's global
  thread-local config safe)
- LM: GLM-5.2 via the Pi Agent `zai-glm` credential (OpenAI-compatible endpoint)
- Packaging: `pyproject.toml` (src/ layout), installable via `pip install -e .`
- Deployment: Docker (`Dockerfile` + `docker-compose.yml`) on the Hetzner VPS

**Non-functional standards:**

- Hungarian comments are permitted in code; docstrings stay English.
- The repository is self-contained: no dependency on sibling local projects.

## Development Workflow

Spec-Driven Development (SDD) via `spec-kit` governs new features:

1. **Constitution** (this document) defines non-negotiable rules.
2. **Spec** (`speckit.specify`) declares scenarios and EARS-form requirements.
3. **Plan / Tasks** (`speckit.plan`, `speckit.tasks`) break the spec into
   auditable implementation steps.
4. **Implement** (`speckit.implement`) writes code + tests per the tasks.
5. **Baseline before optimization**: "no baseline, no claim" — GEPA runs only
   against a measured baseline saved to `runs/`.

Review process: every change is validated by the green pytest suite; breaking
changes to Signatures or the Settings schema require a MINOR/MAJOR constitution
version bump.

## Governance

This Constitution supersedes ad-hoc practices and informal conventions in the
repository. Amendments MUST be documented, approved by the repository owner,
and accompanied by a migration plan if a Core Principle is altered. All
reviews MUST verify compliance with Sections I–V. Versioning follows semantic
versioning (MAJOR for principle removal/redefinition, MINOR for additions,
PATCH for clarifications). Runtime development guidance is captured in
`Agent.md` and this file.

**Version**: 1.0.0 | **Ratified**: 2026-07-15 | **Last Amended**: 2026-07-15
