# snow-kb-generator

> DSPy pipeline that turns completed ServiceNow **Stories** into **Knowledge Base articles** — automatically, powered by GLM-5.2 and a ServiceNow UI Action button.

## Mi ez?

Amikor a fejlesztők befejeznek egy ServiceNow Story-t (`STRY...`), kézzel kellene Knowledge Base (KB) cikket írni a megoldásról. Ez a project **teljesen automatizálja** ezt:
1. A fejlesztő rákattint a **"Create KB Article"** gombra a ServiceNow felületen.
2. A Story adatai egy FastAPI webszerverre kerülnek (VPS-en fut).
3. Egy AI pipeline (DSPy + GLM-5.2) strukturált KB cikket generál.
4. A cikk automatikusan létrejön a ServiceNow KB-ben, a linkje pedig bekerül a Story `work_notes` mezőjébe.

**Bemenet:** lezárt ServiceNow Story — `short_description`, `description`, `acceptance_criteria`, `u_technical_specification`, `work_notes`, `comments`, `state`.
**Kiegészítő bemenet:** A Story nevével megegyező nevű **Update Set** modulekérés és a benne lévő módosított forráskódok (Script Include, Business Rule, UI Action XML payloadok).
**Kimenet:** KB Article (HTML) — `title`, `summary`, `problem`, `solution` (reprodukálható lépések), `category`, `audience`.
**Funkciók:**
- Duplikáció megakadályozása (`u_source_story` mezővel) és Felülírás (Update) felhasználói megerősítés (confirm dialog) után.
- Csapat-specifikus KB Template-ek (Assignment Group alapján történő felismerés és Few-Shot generálás).
- Update Set XML/kód elemzés (RLM / ChainOfThought).

## Technológiai verem

- **Python 3.12**
- **DSPy 3.2.x** — Signatures + Modules, GEPA optimalizáció
- **LM:** GLM-5.2 (Pi Agent előfizetés, GEPA reflectionhöz) + Lokális Qwen3.6-35B (llama.cpp, napi generáláshoz Tailscale-en keresztül)
- **ServiceNow Table API** (`requests`) — Story lekérés + KB létrehozás (CRUD)
- **FastAPI + Uvicorn** — Webhook szerver a ServiceNow UI Action-nek
- **Pydantic v2** — adatmodell és validáció
- **Docker** — deploy és konténerizáció

## Architektúra

```
ServiceNow (Fejlesztői UI)
    │
    │  [Create KB] UI Action gomb (Server-side script)
    │  → RESTMessageV2 (POST)
    ▼
FastAPI szerver (VPS - Hetzner, 8000-as port)
    │  1. ServiceNowClient.get_story() – Elkéri a Story-t
    │  2. ServiceNowClient.get_update_set_changes() – Lekéri a módosított kódokat (XML)
    │  3. StoryToKBArticle (DSPy + GLM-5.2) – Kódok elemzése és cikk generálása
    │  4. ServiceNowClient.create_kb_article() – Pusholja a KB-be
    ▼
Válasz a ServiceNow-nak:
    {"kb_sys_id", "kb_url", "title"}
    │
    ▼
UI Action frissíti a Story work_notes mezőjét a linkkel.
```

## Telepítés és futtatás

### 1. Követelmények
- Python 3.12+
- ServiceNow instance (hozzáférés a Table API-hoz és UI Action-ökhoz)
- GLM API kulcs (vagy más DSPy által támogatott LM)

### 2. Beállítás
```bash
git clone https://github.com/szocpaul/snow-kb-generator.git
cd snow-kb-generator

# Függőségek telepítése
pip install -e ".[deploy,pi-auth]"

# Konfiguráció
cp .env.example .env
# Szerkeszd a .env fájlt: SNOW_INSTANCE, SNOW_USERNAME, SNOW_PASSWORD, SNOW_WEBHOOK_API_KEY
# Szerkeszd a config.yaml fájlt: models.main, knowledge_base_id, story_table
```

### 3. Futtatás CLI-ből (teszteléshez)
```bash
# Csak generálás, push nélkül (dry-run, lokális mock Story-val)
python -m snow_kb STRY0012345 --dry-run

# Éles generálás ServiceNow-ból, KB push nélkül
python -m snow_kb STRY0010012 --no-push --json

# Teljes pipeline: lekérés + generálás + push a KB-be
python -m snow_kb STRY0010012
```

### 4. Futtatás Webszerverként (ServiceNow UI Action-höz)

**Dockerrel (ajánlott VPS-re):**
```bash
docker-compose up -d
```

**Manuálisan:**
```bash
uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000
```

A szerver elérhető lesz a `http://<VPS_IP>:8000` címen.
- `GET /health` — Egészségügyi ellenőrzés
- `POST /generate-kb` — Story-ból KB cikket generál (API kulcs szükséges)

### 5. ServiceNow beállítása
A `servicenow/` mappában található `README.md` lépésről lépésre leírja, hogyan kell beállítani az UI Action gombot és a scriptet a ServiceNow rendszerben.

## Mappa-struktúra

```
snow_kb_generator/
├── Agent.md                    # AI ágens számára: cél, elvek, státusz
├── pyproject.toml              # Csomag definíció
├── Dockerfile                  # Deploy konténer
├── docker-compose.yml          # Deploy konfiguráció
├── config.yaml                 # Modell, KB ID, táblanevek
├── src/snow_kb/
│   ├── server.py               # FastAPI webszerver
│   ├── pipeline.py             # Orchestrátor (fetch → generate → push)
│   ├── servicenow_client.py    # ServiceNow Table API kliens
│   ├── signatures.py           # DSPy Signatures (ExtractChange, DraftSections, FormatKB)
│   ├── program.py              # StoryToKBArticle(dspy.Module)
│   └── ...                     # config, schemas, cli
├── servicenow/                 # ServiceNow-ba másolandó UI Action script
├── tests/                      # 232 pytest teszt
├── eval/                       # GEPA eval harness (dataset, rich_metric, baseline, gepa_optimize)
├── artifacts/                  # GEPA-optimalizált program (program.json)
├── gepa_logs/                  # GEPA checkpointek
└── data/                       # Minta Story-k és Gold példapárok
```

## DSPy Workflow állapota

1. **Spec** — ✅ Kész
2. **Program** — ✅ Kész (Signatures + Module + Update Set Code Analyzer)
3. **Data** — ✅ Kész (Gold Dataset: 5 arany példapár a gold_dataset.md-ben)
4. **Rich metric** — ✅ Kész (rich_metric: structure_match + content_accuracy + template_adherence + hallucination)
5. **Baseline** — ✅ Kész (runs/baseline.json: 0.386)
6. **GEPA optimalizáció** — ✅ Kész (Kimi K3 reflection; aktuális futam a spec 006-os sablonon: 0.300 → 0.850)
7. **Export & deploy** — ✅ Kész (artifacts/program.json; a FastAPI szerver startup-kor betölti, fallback az alap program)

**Hallucináció-védelem (spec 004):** 3 védelmi vonal — (1) megtisztított gold dataset (`KBXXXXXXX` placeholder), (2) hallucination axis a metrikában (GEPA feedback), (3) `strip_hallucinated_references()` guardrail a pipeline-ban push előtt. Éles validáció: a generált cikkek 0 hallucinált hivatkozást tartalmaznak.

**SDD (Spec-Driven Development):** A project aktívan használja a `spec-kit` módszertant.
- 1. Kész Feature: `001-kb-duplicate-prevention` (Duplikáció megakadályozása és felülírás).
- 2. Kész Feature: `002-team-based-templates` (Csapat-specifikus KB sablonok generálása).
- 3. Kész Feature: `003-gepa-kb-quality` (GEPA optimalizáció a KB cikk minőségének javítására).
- 4. Kész Feature: `004-no-hallucinated-references` (Hallucináció-mentes KB generálás: dataset sanitization + hallucination metric axis + pipeline guardrail).
- 5. Kész Feature: `005-real-related-kb-articles` (Valódi kapcsolódó KB cikkek ServiceNow kereséssel; nincs találat → N/A).
- 6. Kész Feature: `006-template-simplification` (Egyszerűsített sablon: nincs H1/Theme/Target Audience szekció; audience = stílusinstrukció).
- 7. Kész Feature: `007-direction-aware-quality` (Evidence-first generálás: irány-érzékeny metric + "no evidence, no section" signature + SkilledProposer + direction guardrail).

## Licenc

Private project.
