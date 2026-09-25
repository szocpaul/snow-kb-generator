# Overall structure — snow-kb-generator docs

## Audiences

**Primary:** Future-you / project maintainer
The solo developer returning to this project after weeks away. Needs to rebuild a working mental model fast: why the pipeline is shaped this way, how the GEPA quality loop runs, and where the spec history left its marks. Brings full project context but fading recall.

**Secondary:**
- Developer extending the pipeline — someone adding a signature, guardrail, or metric axis; needs the DSPy mental model and how the pieces connect, less ops detail.

**Language:** English (repo prose is Hungarian; docs are English by user decision).

## Selected use case (Getting Started)

**Full story: generate, measure, improve.** One narrative that starts with CLI generation of a single article, then layers the eval/GEPA quality loop on top. Longest option, accepted deliberately; the two halves are kept clearly sequenced so the reader can stop after the generation half and still have a usable model.

## Getting Started outline (`getting-started.md`)

1. **Setting up** — install (`pip install -e ".[deploy]"`), `.env` secrets, `config.yaml` anatomy, choosing the task model (local Qwen vs. Kimi). Components: `config.py`, `config.yaml`, `.env.example`.
2. **Generating your first article from the CLI** — `--dry-run` against a mock story, then `--no-push`, then a real push. What the output looks like. Components: `cli.py`, `pipeline.generate_kb_article`, `servicenow_client.py`.
3. **Following the pipeline** — what happens inside one call: fetch story + update set XML → assemble story text → AnalyzeChanges → ExtractChange → GenerateKbFromTemplate → guardrails → create KB article. Components: `pipeline.py`, `signatures.py`, `program.py`, `schemas.py`.
4. **Measuring quality against gold examples** — the gold dataset, the rich metric's axes, running the baseline, reading the score. Components: `eval/dataset.py`, `eval/metric.py`, `eval/baseline.py`, `runs/baseline.json`.
5. **Improving the program with GEPA** — running the optimizer with the Kimi reflection model, inspecting `gepa_logs/`, exporting `artifacts/program.json`. Components: `eval/gepa_optimize.py`, `artifacts/`, `gepa_logs/`.
6. **Going live with the webhook** — starting the FastAPI server, how the optimized program loads at startup with fallback, pointer to the ServiceNow UI Action setup. Components: `server.py`, `servicenow/`.

## Diving Deeper topics (`diving-deeper/`)

1. **Understanding the generation pipeline** — intent of each of the three predictors; why ChainOfThought for analyze/extract but Predict for generation; the evidence-first "no evidence, no section" rule; why the template is mandatory and the legacy draft/format path was removed (specs 006, 009).
2. **Guarding the output before push** — the four HTML guardrails (`strip_hallucinated_references`, direction stripping, N/A-only stripping, code-tag normalization) and the three lines of hallucination defense; why each exists (specs 004, 007) and when they fire.
3. **Configuring models and connections** — the full config surface: `config.yaml` sections, `.env` secrets, local llama.cpp vs. Kimi task model, pi-auth, the separate GEPA reflection model, validation at load time.
4. **Working with team templates and duplicates** — assignment-group-based template selection and few-shot use; duplicate prevention via `u_source_story`, the 409/confirm/force_update flow, missing-group 422 (specs 001, 002).
5. **Defining quality with the rich metric** — the metric axes (structure, content accuracy, template adherence, hallucination, direction, style judge); why rich feedback is what GEPA consumes; maintaining and sanitizing the gold dataset.
6. **Running GEPA and shipping the result** — optimizer knobs (`auto`, candidate selection, threads, seed), SkilledProposer, the refreshing Kimi reflection LM, checkpoints in `gepa_logs/`, export to `artifacts/program.json`, and the server's load-with-fallback.
7. **Serving the webhook to ServiceNow** — endpoints, API-key auth, error-to-HTTP mapping (409/422/502), sync-call timeout implications, Docker deployment, wiring the UI Action script.

## Reference (`reference/`)

One file per module, pure API spec:

- `reference/config.md` — Settings, Secrets, sub-configs, `load_settings()`
- `reference/schemas.md` — StoryData, ArticleSections, KBArticle
- `reference/signatures.md` — AnalyzeChanges, ExtractChange, GenerateKbFromTemplate
- `reference/program.md` — StoryToKBArticle, forward() contract
- `reference/pipeline.md` — generate_kb_article, guardrail functions, DuplicateKBError
- `reference/servicenow-client.md` — ServiceNowClient methods, error hierarchy
- `reference/server.md` — endpoints, request/response models
- `reference/cli.md` — flags and exit codes
- `reference/eval.md` — dataset, metric, baseline, gepa_optimize entry points
- `reference/servicenow-scripts.md` — UI Action + Script Include payloads
