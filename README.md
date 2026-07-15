# snow-kb-generator

> DSPy pipeline that turns completed ServiceNow **Stories** into **Knowledge Base articles** — automatically, powered by GLM-5.2 and a ServiceNow UI Action button.

## Mi ez?

When the developers finish a ServiceNow Story (`STRY...`), a Knowledge Base (KB) article should be written by hand about the solution. This project **fully automates** that:
1. The developer clicks the **"Create KB Article"** button in the ServiceNow interface.
2. The Story data is sent to a FastAPI web server (running on a VPS).
3. An AI pipeline (DSPy + GLM-5.2) generates a structured KB article.
4. The article is created automatically in the ServiceNow KB, and its link is inserted into the Story `work_notes` field.

**Input:** closed ServiceNow Story — `short_description`, `description`, `acceptance_criteria`, `u_technical_specification`, `work_notes`, `comments`, `state`.
**Additional input:** The **Update Set** module request with the same name as the Story and the modified source code it contains (Script Include, Business Rule, UI Action XML payloads).
**Output:** KB Article (HTML) — `title`, `summary`, `problem`, `solution` (reproducible steps), `category`, `audience`.
**Features:** Duplicate prevention (with the `u_source_story` field) and Overwrite (Update) after user confirmation (confirm dialog).

## Tech stack

- **Python 3.12**
- **DSPy 3.2.x** — Signatures + Modules, GEPA optimization
- **LM:** GLM-5.2 (Pi Agent subscription, via the Z.ai API)
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
    │  3. StoryToKBArticle (DSPy + GLM-5.2) – code analysis and article generation
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
- GLM API key (or another LM supported by DSPy)

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
├── tests/                      # 173 pytest tests
├── eval/                       # GEPA metric and dataset (in development)
└── data/                       # Sample Stories and Gold example pairs
```

## DSPy workflow status

1. **Spec** — ✅ Done
2. **Program** — ✅ Done (Signatures + Module + Update Set Code Analyzer)
3. **Data** — ⏳ Collecting gold example pairs
4. **Rich metric** — ⏳ Next step
5. **Baseline** — ⏳
6. **GEPA optimization** — ⏳
7. **Export & deploy** — ✅ Done (FastAPI + Docker + ServiceNow UI Action)

**SDD (Spec-Driven Development):** The project actively uses the `spec-kit` methodology.
- 1. Done Feature: `001-kb-duplicate-prevention` (duplicate prevention and overwrite).

## Licenc

Private project.
