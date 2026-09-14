# snow-kb-generator

> A DSPy pipeline that turns completed ServiceNow **Stories** into **Knowledge Base articles** — automatically, powered by **Kimi K3** (default mode) or a local **Qwen3.8-27B** (Dev mode, llama.cpp), triggered by a ServiceNow UI Action button.

*(Magyar változat: [README.hu.md](README.hu.md))*

## What is this?

When developers finish a ServiceNow Story (`STRY...`), someone has to manually write a Knowledge Base article about the solution. This project **fully automates** that:

1. The developer clicks a **"Create KB Article"** button on the ServiceNow form.
2. The Story data is sent to a FastAPI server (running on a VPS, systemd-managed).
3. A DSPy pipeline (Kimi K3, or local Qwen3.8-27B in Dev mode) generates a structured KB article.
4. The article is automatically created in the ServiceNow KB, and its link is written back to the Story's `work_notes`.

**Input:** completed ServiceNow Story — `short_description`, `description`, `acceptance_criteria`, `u_technical_specification`, `work_notes`, `comments`, `state`.
**Additional input:** the Update Set matching the Story name, with the modified source codes (Script Include, Business Rule, UI Action XML payloads).
**Output:** KB Article (HTML) — `title`, `summary`, `problem`, `solution` (reproducible steps), `category`, `audience`.

**Features:**
- Duplicate prevention (`u_source_story` field) and overwrite with user confirmation
- Team-specific KB templates (assignment-group-based detection, few-shot generation)
- Update Set XML/code analysis (ChainOfThought)
- Hallucination guardrails: KB-number validation, component-name detection, HTML-nesting check

## Results (measured, not claimed)

| Metric | Value |
|---|---|
| End-to-end validation | Production: ServiceNow button → generation → KB update, human review approved (2026-08-20) |
| Overall score (5-axis rich metric) | **0.869** (Kimi K3) / **0.859** (local 27B), 9-example gold dataset |
| Measurement noise (3 identical runs) | **±0.018** overall, ±0.017 style (after multi-sample judge, was ±0.188) |
| Hallucination axis | 1.000 across all evals; every production article verified component-by-component |
| Test suite | **286/286 passing** |

Key engineering lessons baked in: LLM-judge variance calibration, GEPA prompt-transfer failure detection (a 35B-tuned program *degrades* on a 27B model), OAuth token auto-refresh under systemd, thread-safe DSPy configuration for web servers.

## Tech stack

- **Python 3.12**, **DSPy 3.3.x** (Signatures, Modules, GEPA optimization)
- **LM (since 2026-08-25):** DEFAULT = **Kimi K3** (Kimi Code subscription, `task_model: "kimi"`) | **Dev mode** = local Qwen3.8-27B (llama.cpp) — toggle via `SNOW_KB_DEV_MODE=1` env or CLI `--dev` flag
- **ServiceNow Table API** (`requests`) — Story fetch + KB CRUD
- **FastAPI + Uvicorn** — webhook server for the UI Action (systemd, `Restart=always`)
- **Pydantic v2** — data model & validation

## Architecture

```
ServiceNow (Developer UI)
    │
    │  [Create KB] UI Action (server-side script) → RESTMessageV2 (POST)
    ▼
FastAPI server (VPS, port 8000, systemd)
    │  1. ServiceNowClient.get_story()            – fetch Story
    │  2. ServiceNowClient.get_update_set_changes() – fetch modified code (XML)
    │  3. StoryToKBArticle (DSPy + Kimi K3 / Dev: Qwen3.8-27B) – analyze + generate
    │  4. ServiceNowClient.create_kb_article()    – push to KB
    ▼
Response to ServiceNow: {"kb_sys_id", "kb_url", "title"}
    │
    ▼
UI Action writes the KB link into the Story's work_notes.
```

## Setup & usage

### Requirements
- Python 3.12+, ServiceNow instance (Table API + UI Action access)
- Kimi Code subscription (default mode) AND/OR a running llama.cpp server with Qwen3.8-27B (Dev mode)

### Configuration
```bash
git clone https://github.com/szocpaul/snow-kb-generator.git
cd snow-kb-generator
pip install -e ".[deploy,pi-auth]"
cp .env.example .env
# Edit .env: SNOW_INSTANCE, SNOW_USERNAME, SNOW_PASSWORD, SNOW_WEBHOOK_API_KEY
# Edit config.yaml: models.main, knowledge_base_id, story_table
```

### CLI (testing)
```bash
python -m snow_kb STRY0012345 --dry-run          # mock story, no LM
python -m snow_kb STRY0010012 --no-push --json   # real story, no KB push
python -m snow_kb STRY0010012                    # full pipeline incl. push
python -m snow_kb STRY0010012 --dev              # Dev mode: local LLM instead of Kimi
```

### Server (production)
```bash
sudo cp deploy/snow-kb.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl enable --now snow-kb.service
```
Endpoints: `GET /health`, `POST /generate-kb` (API key required).
ServiceNow-side setup (UI Action): see `servicenow/README.md`. New PDI bootstrap: `scripts_pdi/bootstrap_pdi.py` (creates fields, template KB, UI Action, test story).

## Project structure

```
snow_kb_generator/
├── Agent.md                    # Decision log / project journal (HU)
├── config.yaml                 # Model, KB ID, table names
├── src/snow_kb/
│   ├── server.py               # FastAPI server
│   ├── pipeline.py             # Orchestrator (fetch → generate → push)
│   ├── servicenow_client.py    # ServiceNow Table API client
│   ├── signatures.py           # DSPy Signatures (AnalyzeChanges, ExtractChange, GenerateKbFromTemplate)
│   └── program.py              # StoryToKBArticle(dspy.Module)
├── eval/                       # GEPA eval harness (dataset, rich_metric, baseline, compare)
├── specs/                      # 12 feature specs (spec-kit, spec-driven development)
├── tests/                      # 286 pytest tests
├── deploy/                     # systemd unit + setup guide
├── scripts_pdi/                # bootstrap_pdi.py — new ServiceNow instance setup
├── servicenow/                 # UI Action script to install in ServiceNow
└── data/                       # Sample stories and gold example pairs
```

## DSPy workflow status

1. **Spec** — ✅ Done
2. **Program** — ✅ Done (Signatures + Module + Update Set code analyzer)
3. **Data** — ✅ Done (gold dataset: 9 example pairs, 5 train / 4 val, incl. Update Set payloads)
4. **Rich metric** — ✅ Done (5 axes: structure, content, template, hallucination, style; the hallucination axis validates both KB numbers and named components)
5. **Baseline** — ✅ Done (current references: local 27B **0.859**, Kimi K3 **0.869**)
6. **GEPA optimization** — ✅ Done (Kimi K3 reflection; 35B run: 0.773 → 0.859 — note: the 35B-tuned program does **not** transfer to the 27B model, so production uses the base program; a 27B GEPA run is in the backlog with a ready starter package)
7. **Export & deploy** — ✅ Done (systemd server, live end-to-end validation on two model generations)

**Spec-driven development:** the project actively uses the spec-kit methodology — 12 completed feature specs in `specs/` (duplicate prevention, team templates, GEPA quality, hallucination guardrails, direction-aware quality, human-style articles, component-hallucination metric, style-judge noise reduction, and more).

## License

Private project.
