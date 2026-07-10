# snow-kb-generator

> DSPy pipeline that turns completed ServiceNow **Stories** into **Knowledge Base articles** — automatically.

## Mi ez?

When the developers finish a ServiceNow Story (`STRY...`), a Knowledge Base (KB) article should be written manually about it. This project automates that: an AI pipeline (DSPy) generates a structured, audience-targeted, ServiceNow-compatible KB article from the Story fields and writes it back to the KB.

**Input:** closed ServiceNow Story — `short_description`, `description`, `acceptance_criteria`, `work_notes`, `comments`, `state`, …
**Output:** KB Article (HTML) — `title`, `summary`, `problem`, `solution` (reproducible steps), `category`, `audience`.

## Tech stack

- **Python 3.12**
- **DSPy 3.2.x** — Signatures + Modules, GEPA optimization
- **ServiceNow Table API** (`requests`) — Story fetch + KB creation (CRUD)
- **Pydantic v2** — adatmodell
- **python-dotenv + PyYAML** — configuration (`.env` secrets, `config.yaml` settings)

## Folder structure

```
snow_kb_generator/
├── Agent.md                    # the goal of the project, its boundaries, its operating principles
├── README.md                   # this file
├── .env.example                # template for the secrets
├── requirements.txt            # dependencies
├── config.yaml                 # settings (KB id, categories, models)
└── src/snow_kb/
    ├── __init__.py
    ├── config.py               # .env + config.yaml loading
    ├── servicenow_client.py    # ServiceNow Table API kliens
    ├── schemas.py              # Pydantic adatmodellek
    ├── signatures.py           # DSPy Signatures (the steps of the pipeline)
    ├── program.py              # StoryToKBArticle(dspy.Module)
    ├── pipeline.py             # orchestrator: fetch → generate → push
    └── cli.py                  # command-line interface
data/                           # sample / gold data
eval/                           # dataset + rich metric
runs/                           # baseline / optimized JSON results
artifacts/                      # saved optimized program
gepa_logs/                      # GEPA reflection logok
```

## Status

This project is currently in the **design phase**. The `src/snow_kb/*.py` files only
contain **comment-format plans** (no implemented code yet). The full
goal and the description of the 7-step DSPy workflow are in [`Agent.md`](Agent.md).

## Workflow (planned)

1. **Spec** → 2. **Program** → 3. **Data** → 4. **Rich metric** →
5. **Baseline** → 6. **GEPA optimization** → 7. **Export & deploy**

Details: see section 5 of `Agent.md`.

## Usage (planned)

```bash
# one-time setup
cp .env.example .env   # and fill it in
pip install -r requirements.txt

# one KB article from a Story
python -m snow_kb STRY0012345

# dry-run: only generates, does not write to ServiceNow
python -m snow_kb STRY0012345 --dry-run
```

## Licenc

Not specified yet (private project).
