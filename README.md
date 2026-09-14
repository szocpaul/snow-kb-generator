# snow-kb-generator

> DSPy pipeline that turns completed ServiceNow **Stories** into **Knowledge Base articles** — automatically, powered by **Kimi K3** (basic mode) or local **Qwen3.8-27B** (Dev mode, llama.cpp), and a ServiceNow UI Action button.

## Mi ez?

When the developers finish a ServiceNow Story (`STRY...`), a Knowledge Base (KB) article should be written by hand about the solution. This project **fully automates** that:
1. The developer clicks the **"Create KB Article"** button in the ServiceNow interface.
2. The Story data is sent to a FastAPI web server (running on a VPS).
3. An AI pipeline (DSPy + Kimi K3, local Qwen3.8-27B in Dev mode) generates a structured KB article.
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
- **LM (from 2026-08-25):** BASIC mode = **Kimi K3** (Kimi Code subscription, `task_model: "kimi"`) | **Dev mode** = local Qwen3.8-27B (llama.cpp) — toggle: `SNOW_KB_DEV_MODE=1` env or CLI `--dev` flag. GEPA reflection/proposer stays Kimi K3.
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
    │  3. StoryToKBArticle (DSPy + Kimi K3 / Qwen3.8-27B in Dev mode) – code analysis and article generation
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
- Kimi Code subscription (BASIC mode, `task_model: "kimi"` — default) AND/OR a running llama.cpp server with the Qwen3.8-27B model (Dev mode, Windows machine, Tailscale endpoint; `SNOW_KB_DEV_MODE=1` or `--dev`)

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
│   ├── signatures.py           # DSPy Signatures (AnalyzeChanges, ExtractChange, GenerateKbFromTemplate)
│   ├── program.py              # StoryToKBArticle(dspy.Module)
│   └── ...                     # config, schemas, cli
├── servicenow/                 # UI Action script to copy into ServiceNow
├── tests/                      # 286 pytest tests (with the `../.venv` interpreter — there is NO own .venv!)
├── eval/                       # GEPA eval harness (dataset, rich_metric, baseline, gepa_optimize)
├── artifacts/                  # Optimized programs (GEPA-optimized for the 35B: program_35b_optimized.json — in production the BASE program runs, see Agent.md 33)
├── deploy/                     # systemd unit + installation guide (server restart tolerance)
├── scripts_pdi/                # bootstrap_pdi.py — preparing a new PDI (fields, template, UI Action, test Story)
├── .prime/agent/skills/        # autonomous-spec-runner skill (a long-running agent workflow)
├── gepa_logs/                  # GEPA checkpointek
└── data/                       # Sample Stories and Gold example pairs
```

## DSPy workflow status

1. **Spec** — ✅ Done
2. **Program** — ✅ Done (Signatures + Module + Update Set Code Analyzer)
3. **Data** — ✅ Done (Gold Dataset: 9 gold example pairs in gold_dataset.md — 5 train / 4 val; Example 5 also has Update Set XML payloads, spec 011)
4. **Rich metric** — ✅ Done (rich_metric 5 axes: structure + content + template + hallucination + style, spec 010; since spec 011 the hallucination axis also validates KB numbers AND named component names)
5. **Baseline** — ✅ Done (per-axis format; the run-to-run noise is ±0.018 since the spec 012 multi-sample judge). **Current references (2026-08-26, spec 012 metric, 5 train/4 val):** local Qwen3.8-27B base **0.859** | **Kimi K3 base 0.869** (the first verified Kimi measurement — the July "kimi" numbers are uncertain due to the __main__ double-import bug, see Agent.md 38)
6. **GEPA optimization** — ✅ Done (Kimi K3 reflection; spec 010 run for the 35B on 2026-08-08: 0.773 → 0.825-0.859). **IMPORTANT (2026-08-20): the program optimized for the 35B does NOT transfer to the 27B** (0.768 vs 27B base 0.859) — so production runs the base program; the 35B artifact is kept. GEPA for the 27B: backlog, starter package ready (meaningful with the noise-reduced metric)
7. **Export & deploy** — ✅ Done: the FastAPI server runs **as a systemd service** (`deploy/snow-kb.service`, Restart=always, tested with SIGKILL), with the **base program** (the `artifacts/program.json` is not present → automatic fallback). **Production end-to-end validation**: 2026-08-09 (35B) and 2026-08-20 (27B, STRY0010014 bidirectional article, 8/8 components verified) — human review approved. New PDI migration: `scripts_pdi/bootstrap_pdi.py` (2026-08-20, legacy-instance)

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
- 11. Done Feature: `012-style-judge-noise-reduction` (multi-sample style judge: it returns the average of the N=3 samples of `_style_score`, with partial error tolerance; the style run-to-run deviation is 0.188 → 0.017; judge discrimination unchanged; re-evaluated numerically with mini-GEPA — the decision is the human's).

## Licenc

Private project.
