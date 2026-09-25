# Getting Started

## Setting up the project

Learn:

- Which dependencies to install for CLI use vs. server deployment vs. GEPA optimization
- Which secrets live in `.env` and which structured settings live in `config.yaml`
- How to choose the task model: local Qwen via llama.cpp vs. Kimi

```bash
git clone https://github.com/szocpaul/snow-kb-generator.git
cd snow-kb-generator
pip install -e ".[deploy,gepa]"
```

```bash
cp .env.example .env
# edit .env: SNOW_INSTANCE, SNOW_USERNAME, SNOW_PASSWORD, SNOW_WEBHOOK_API_KEY
```

```yaml
# config.yaml — the settings you touch first
servicenow:
  knowledge_base_id: "a7e8a78bff0221009b20ffffffffff17"
  story_table: "rm_story"
pipeline:
  task_model: "local"          # "local" (llama.cpp Qwen) or "kimi"
  api_base: "http://<your-llama.cpp-host>:8033/v1"
models:
  main: "openai/Qwen3.6-35B-A3B-...gguf"
  reflection: "openai/kimi-k3"  # GEPA-only
```

## Generating your first article from the CLI

Learn:

- The three run modes: `--dry-run`, `--no-push`, and full push
- Where the generated HTML goes (stdout, `--output`, or ServiceNow KB)
- How duplicate detection surfaces on the CLI

```bash
# 1. No ServiceNow, no LM — mock article from a local sample story
python -m snow_kb STRY0012345 --dry-run
```

```bash
# 2. Real story, real model, nothing written back to ServiceNow
python -m snow_kb STRY0010012 --no-push --json -o article.json
```

```bash
# 3. Full run: fetch, generate, guard, and create the KB article
python -m snow_kb STRY0010012
```

## Following the pipeline end to end

Learn:

- The six stages one call passes through: fetch story, fetch update set XML, assemble text, generate, guard, push
- The three named predictors and what each produces (AnalyzeChanges → ExtractChange → GenerateKbFromTemplate)
- Which guardrails rewrite the HTML before anything reaches ServiceNow

```python
from snow_kb.config import load_settings
from snow_kb.servicenow_client import ServiceNowClient
from snow_kb.pipeline import generate_kb_article

settings = load_settings("config.yaml")
client = ServiceNowClient(settings)

article = generate_kb_article(
    "STRY0010012",
    client=client,
    settings=settings,
    push=False,
)
print(article.title)
print(article.html[:500])
```

## Measuring quality against gold examples

Learn:

- What the gold dataset is and how it splits into trainset/valset
- What the rich metric scores (structure, content, template adherence, hallucination, direction, style)
- How to run the baseline and read the resulting score

```bash
python -m eval.baseline --model local --output runs/baseline.json
```

```bash
cat runs/baseline.json
# → per-example axis scores + aggregate (e.g. 0.386 on the val set)
```

## Improving the program with GEPA

Learn:

- Why the reflection model is separate from the task model
- How to launch a GEPA run and what a metric-call budget means
- Where checkpoints land and what `artifacts/program.json` contains

```bash
python -m eval.gepa_optimize --max-metric-calls 200 --output artifacts/program.json
```

```bash
ls gepa_logs/          # candidates.json, run_log.json, candidate_tree.html
ls artifacts/          # program.json — the optimized program, loadable at runtime
```

## Going live with the webhook

Learn:

- How the server loads the optimized program at startup, with fallback to the base program
- How to call `/generate-kb` and what the 409 duplicate response means
- Where the ServiceNow-side UI Action script lives

```bash
uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000
```

```bash
curl -X POST http://localhost:8000/generate-kb \
  -H "X-API-Key: $SNOW_WEBHOOK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"story_id": "STRY0010012", "push": true}'
# → {"success": true, "kb_sys_id": "...", "kb_url": "...", "title": "..."}
# → 409 Conflict if the story already has an article (retry with "force_update": true)
```
