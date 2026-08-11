# snow-kb-generator

> DSPy pipeline that turns completed ServiceNow **Stories** into **Knowledge Base articles** — automatically, powered by a local Qwen3.6-35B (llama.cpp) and a ServiceNow UI Action button.

## Mi ez?

When the developers finish a ServiceNow Story (`STRY...`), a Knowledge Base (KB) article should be written by hand about the solution. This project **fully automates** that:
1. The developer clicks the **"Create KB Article"** button in the ServiceNow interface.
2. The Story data is sent to a FastAPI web server (running on a VPS).
3. An AI pipeline (DSPy + local Qwen3.6-35B) generates a structured KB article.
4. The article is created automatically in the ServiceNow KB, and its link is inserted into the Story `work_notes` field.

**Input:** closed ServiceNow Story — `short_description`, `description`, `acceptance_criteria`, `u_technical_specification`, `work_notes`, `comments`, `state`.
**Additional input:** The **Update Set** module request with the same name as the Story and the modified source code it contains (Script Include, Business Rule, UI Action XML payloads).
**Output:** KB Article (HTML) — `title`, `summary`, `problem`, `solution` (reproducible steps), `category`, `audience`.
**Features:**
- Duplicate prevention (with the `u_source_story` field) and Overwrite (Update) after user confirmation (confirm dialog).
- Team-specific KB Templates (recognition based on Assignment Group and Few-Shot generation).
- Update Set XML/code analysis (RLM / ChainOfThought).

## Tech stack

- **Python 3.12**
- **DSPy 3.3.x** — Signatures + Modules, GEPA optimization
- **LM:** local Qwen3.6-35B-A3B (llama.cpp, task model — `task_model: "local"`) + Kimi K3 (Pi Agent subscription, GEPA reflection/proposer). Clean measurement (2026-07-29, `cache=False`): K3 0.769 vs local 0.733 — alongside the local model, the zero marginal cost decided it
- **ServiceNow Table API** (`requests`) — Story fetch + KB creation (CRUD)
- **FastAPI + Uvicorn** — webhook server for the ServiceNow UI Action
- **Pydantic v2** — data model and validation
- **Docker** — deploy and containerization

## Architecture

```
ServiceNow (Developer UI)
    │
    │  [Create KB] UI Action gomb (Server-side script)
    │  → RESTMessageV2 (POST)
    ▼
FastAPI server (VPS - Hetzner, port 8000)
    │  1. ServiceNowClient.get_story() – requests the Story
    │  2. ServiceNowClient.get_update_set_changes() – fetches the modified code (XML)
    │  3. StoryToKBArticle (DSPy + Qwen3.6-35B) – code analysis and article generation
    │  4. ServiceNowClient.create_kb_article() – Pusholja a KB-be
    ▼
Response to ServiceNow:
    {"kb_sys_id", "kb_url", "title"}
    │
    ▼
The UI Action updates the Story work_notes field with the link.
```

## Installation and running

### 1. Requirements
- Python 3.12+
- ServiceNow instance (access to the Table API and UI Actions)
- A running llama.cpp server with the Qwen3.6-35B-A3B model (Windows machine, Tailscale endpoint) OR a Kimi Code subscription (`task_model: "kimi"`)

### 2. Configuration
```bash
git clone https://github.com/szocpaul/snow-kb-generator.git
cd snow-kb-generator

# Installing dependencies
pip install -e ".[deploy,pi-auth]"

# Configuration
cp .env.example .env
# Edit the .env file: SNOW_INSTANCE, SNOW_USERNAME, SNOW_PASSWORD, SNOW_WEBHOOK_API_KEY
# Edit the config.yaml file: models.main, knowledge_base_id, story_table
```

### 3. Running from the CLI (for testing)
```bash
# Generation only, no push (dry-run, with a local mock Story)
python -m snow_kb STRY0012345 --dry-run

# Production generation from ServiceNow, without KB push
python -m snow_kb STRY0010012 --no-push --json

# Full pipeline: fetch + generation + push to the KB
python -m snow_kb STRY0010012
```

### 4. Running as a web server (for a ServiceNow UI Action)

**With Docker (recommended for a VPS):**
```bash
docker-compose up -d
```

**Manually:**
```bash
uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000
```

The server will be available at `http://<VPS_IP>:8000`.
- `GET /health` — Health check
- `POST /generate-kb` — generates a KB article from a Story (API key required)

### 5. ServiceNow setup
The `README.md` in the `servicenow/` folder describes step by step how to set up the UI Action button and the script in the ServiceNow system.

## Folder structure

```
snow_kb_generator/
├── Agent.md                    # for the AI agent: goal, principles, status
├── pyproject.toml              # Package definition
├── Dockerfile                  # Deploy container
├── docker-compose.yml          # deploy configuration
├── config.yaml                 # Model, KB ID, table names
├── src/snow_kb/
│   ├── server.py               # FastAPI webszerver
│   ├── pipeline.py             # Orchestrator (fetch → generate → push)
│   ├── servicenow_client.py    # ServiceNow Table API kliens
│   ├── signatures.py           # DSPy Signatures (ExtractChange, DraftSections, FormatKB)
│   ├── program.py              # StoryToKBArticle(dspy.Module)
│   └── ...                     # config, schemas, cli
├── servicenow/                 # UI Action script to copy into ServiceNow
├── tests/                      # 258 pytest tests (with the .venv interpreter!)
├── eval/                       # GEPA eval harness (dataset, rich_metric, baseline, gepa_optimize)
├── artifacts/                  # GEPA-optimized program (program.json)
├── gepa_logs/                  # GEPA checkpointek
└── data/                       # Sample Stories and Gold example pairs
```

## DSPy workflow status

1. **Spec** — ✅ Done
2. **Program** — ✅ Done (Signatures + Module + Update Set Code Analyzer)
3. **Data** — ✅ Done (Gold Dataset: 9 gold example pairs in gold_dataset.md — 5 train / 4 val; Example 5 also has Update Set XML payloads, spec 011)
4. **Rich metric** — ✅ Done (rich_metric 5 axes: structure + content + template + hallucination + style, spec 010; since spec 011 the hallucination axis also validates KB numbers AND named component names)
5. **Baseline** — ✅ Done (per-axis format, T010c; reference: 0.755 aggregate, hallucination 1.000, style 0.475, 2026-08-11 spec 011 metric — the earlier 0.773 (2026-08-08) is OUTDATED)
6. **GEPA optimization** — ✅ Done (Kimi K3 reflection; spec 010 run 2026-08-08: aggregate 0.773 → 0.825-0.859, style 0.450 → 0.600-0.650 on the cleaned 8-example dataset)
7. **Export & deploy** — ✅ Done (artifacts/program.json; the FastAPI server AND the CLI also load it at startup, fallback to the base program). **Production end-to-end validation (2026-08-09)**: ServiceNow button → generation → KB update successful, human review approved

**Hallucination protection (spec 004):** 3 defense lines — (1) sanitized gold dataset (`KBXXXXXXX` placeholder), (2) hallucination axis in the metric (GEPA feedback), (3) `strip_hallucinated_references()` guardrail in the pipeline before push. Production validation: the generated articles contain 0 hallucinated references.

**SDD (Spec-Driven Development):** The project actively uses the `spec-kit` methodology.
- 1. Done Feature: `001-kb-duplicate-prevention` (duplicate prevention and overwrite).
- 2. Done Feature: `002-team-based-templates` (generation of team-specific KB templates).
- 3. Done Feature: `003-gepa-kb-quality` (GEPA optimization to improve the quality of the KB article).
- 4. Done Feature: `004-no-hallucinated-references` (hallucination-free KB generation: dataset sanitization + hallucination metric axis + pipeline guardrail).
- 5. Done Feature: `005-real-related-kb-articles` (real related KB articles via ServiceNow search; no result → N/A).
- 6. Done Feature: `006-template-simplification` (simplified template: no H1/Theme/Target Audience section; audience = style instruction).
- 7. Done Feature: `007-direction-aware-quality` (evidence-first generation: direction-sensitive metric + "no evidence, no section" signature + SkilledProposer + direction guardrail).
- 8. Done Feature: `009-remove-legacy-draft-format` (legacy draft/format branch removed; 3 predictors, template mandatory).
- 9. Done Feature: `010-human-style-articles` (human tone: tone guidance + style judge + SkilledProposer style guidance + GEPA 200-call; T013 human review approved).
- 10. Done Feature: `011-component-hallucination-metric` (component hallucination detection in the metric + Update Set dataset coverage: the hallucination axis also validates named components; Example 5 with real, anonymized Update Set XMLs; baseline re-measured: 0.755).

## Licenc

Private project.
