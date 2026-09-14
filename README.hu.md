# snow-kb-generator

> DSPy pipeline that turns completed ServiceNow **Stories** into **Knowledge Base articles** — automatically, powered by **Kimi K3** (alap mód) vagy lokális **Qwen3.8-27B** (Dev mód, llama.cpp), and a ServiceNow UI Action button.

## Mi ez?

Amikor a fejlesztők befejeznek egy ServiceNow Story-t (`STRY...`), kézzel kellene Knowledge Base (KB) cikket írni a megoldásról. Ez a project **teljesen automatizálja** ezt:
1. A fejlesztő rákattint a **"Create KB Article"** gombra a ServiceNow felületen.
2. A Story adatai egy FastAPI webszerverre kerülnek (VPS-en fut).
3. Egy AI pipeline (DSPy + Kimi K3, Dev módban lokális Qwen3.8-27B) strukturált KB cikket generál.
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
- **DSPy 3.3.x** — Signatures + Modules, GEPA optimalizáció
- **LM (2026-08-25-től):** ALAP mód = **Kimi K3** (Kimi Code előfizetés, `task_model: "kimi"`) | **Dev mód** = lokális Qwen3.8-27B (llama.cpp) — ki/bekapcsolás: `SNOW_KB_DEV_MODE=1` env vagy CLI `--dev` flag. GEPA reflection/proposer továbbra is Kimi K3.
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
    │  3. StoryToKBArticle (DSPy + Kimi K3 / Dev módban Qwen3.8-27B) – Kódok elemzése és cikk generálása
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
- Kimi Code előfizetés (ALAP mód, `task_model: "kimi"` — alapértelmezett) ÉS/VAGY futó llama.cpp szerver a Qwen3.8-27B modellel (Dev mód, Windows gép, Tailscale endpoint; `SNOW_KB_DEV_MODE=1` vagy `--dev`)

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
│   ├── signatures.py           # DSPy Signatures (AnalyzeChanges, ExtractChange, GenerateKbFromTemplate)
│   ├── program.py              # StoryToKBArticle(dspy.Module)
│   └── ...                     # config, schemas, cli
├── servicenow/                 # ServiceNow-ba másolandó UI Action script
├── tests/                      # 286 pytest teszt (`../.venv` interpreterrel — NINCS saját .venv!)
├── eval/                       # GEPA eval harness (dataset, rich_metric, baseline, gepa_optimize)
├── artifacts/                  # Optimized programok (35B-re GEPA-zott: program_35b_optimized.json — élesben a BASE program fut, ld. Agent.md 33)
├── deploy/                     # systemd unit + telepítési útmutató (a szerver restart-tűrése)
├── scripts_pdi/                # bootstrap_pdi.py — új PDI felkészítése (mezők, template, UI Action, teszt-Story)
├── .prime/agent/skills/        # autonomous-spec-runner skill (a long-running agent workflow)
├── gepa_logs/                  # GEPA checkpointek
└── data/                       # Minta Story-k és Gold példapárok
```

## DSPy Workflow állapota

1. **Spec** — ✅ Kész
2. **Program** — ✅ Kész (Signatures + Module + Update Set Code Analyzer)
3. **Data** — ✅ Kész (Gold Dataset: 9 arany példapár a gold_dataset.md-ben — 5 train / 4 val; a Példa 5 Update Set XML payloadokkal is rendelkezik, spec 011)
4. **Rich metric** — ✅ Kész (rich_metric 5 tengely: structure + content + template + hallucination + style, spec 010; a hallucination tengely spec 011 óta KB-számokat ÉS nevesített komponensneveket is validál)
5. **Baseline** — ✅ Kész (per-axis formátum; a futásközi zaj a spec 012 multi-sample judge óta ±0.018). **Aktuális referenciák (2026-08-26, spec 012 metrika, 5 train/4 val):** lokális Qwen3.8-27B base **0.859** | **Kimi K3 base 0.869** (az első igazolt Kimi-mérés — a júliusi "kimi" számok a __main__ dupla-import bug miatt bizonytalanok, ld. Agent.md 38)
6. **GEPA optimalizáció** — ✅ Kész (Kimi K3 reflection; spec 010 futam a 35B-re 2026-08-08: 0.773 → 0.825-0.859). **FONTOS (2026-08-20): a 35B-re optimalizált program NEM transzferálódik a 27B-re** (0.768 vs 27B base 0.859) — az éles ezért a base programot futtatja; a 35B-s artifact megőrizve. GEPA a 27B-hez: backlog, indítócsomag kész (a zaj-mentesített metrikával értelmezhető)
7. **Export & deploy** — ✅ Kész: a FastAPI szerver **systemd-szolgáltatásként** fut (`deploy/snow-kb.service`, Restart=always, SIGKILL-tesztelve), a **base programmal** (az `artifacts/program.json` nincs jelen → automatikus fallback). **Éles end-to-end validáció**: 2026-08-09 (35B) és 2026-08-20 (27B, STRY0010014 bidirectional cikk, 8/8 komponens igazolt) — emberi review elfogadva. Új PDI-migráció: `scripts_pdi/bootstrap_pdi.py` (2026-08-20, dev437812)

**Hallucináció-védelem (spec 004):** 3 védelmi vonal — (1) megtisztított gold dataset (`KBXXXXXXX` placeholder), (2) hallucination axis a metrikában (GEPA feedback), (3) `strip_hallucinated_references()` guardrail a pipeline-ban push előtt. Éles validáció: a generált cikkek 0 hallucinált hivatkozást tartalmaznak.

**SDD (Spec-Driven Development):** A project aktívan használja a `spec-kit` módszertant.
- 1. Kész Feature: `001-kb-duplicate-prevention` (Duplikáció megakadályozása és felülírás).
- 2. Kész Feature: `002-team-based-templates` (Csapat-specifikus KB sablonok generálása).
- 3. Kész Feature: `003-gepa-kb-quality` (GEPA optimalizáció a KB cikk minőségének javítására).
- 4. Kész Feature: `004-no-hallucinated-references` (Hallucináció-mentes KB generálás: dataset sanitization + hallucination metric axis + pipeline guardrail).
- 5. Kész Feature: `005-real-related-kb-articles` (Valódi kapcsolódó KB cikkek ServiceNow kereséssel; nincs találat → N/A).
- 6. Kész Feature: `006-template-simplification` (Egyszerűsített sablon: nincs H1/Theme/Target Audience szekció; audience = stílusinstrukció).
- 7. Kész Feature: `007-direction-aware-quality` (Evidence-first generálás: irány-érzékeny metric + "no evidence, no section" signature + SkilledProposer + direction guardrail).
- 8. Kész Feature: `009-remove-legacy-draft-format` (Legacy draft/format ág kivezetve; 3 prediktor, template kötelező).
- 9. Kész Feature: `010-human-style-articles` (Emberi hangnem: tone guidance + style judge + SkilledProposer style guidance + GEPA 200-call; T013 emberi review jóváhagyva).
- 10. Kész Feature: `011-component-hallucination-metric` (Komponens-hallucináció detektálás a metrikában + Update Set dataset-lefedettség: a hallucination tengely nevesített komponenseket is validál; Példa 5 valódi, anonymizált Update Set XML-ekkel; baseline újramérve: 0.755).
- 11. Kész Feature: `012-style-judge-noise-reduction` (Multi-sample style judge: a `_style_score` N=3 minta átlagát adja, részleges hibatűréssel; a style futásközi szórás 0.188 → 0.017; judge-diszkrimináció változatlan; mini-GEPA számszerűen újraértékelve — a döntés az emberé).

## Licenc

Private project.
