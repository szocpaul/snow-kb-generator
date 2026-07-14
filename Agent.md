# Agent.md — snow_kb_generator

> Ez a fájl az AI ágens (és a fejlesztő) számára rögzíti a project célját, határait és működési elveit. Olvasd el, mielőtt bármit módosítasz a projectben.

## 1. Project célja

ServiceNow-ban a fejlesztők **Story-k** (`STRY...`) megvalósításán dolgoznak. Amikor a munka elkészül és a Story lezárul, erről automatikusan **Knowledge Base Article (KB)** készüljön. Ezt az átalakítást egy **DSPy AI pipeline** végzi: a Story adataiból strukturált, célközönségnek szóló, ServiceNow-kompatibilis KB cikket generál.

**Bemenet:** lezárt ServiceNow Story mezői — `short_description`, `description`, `acceptance_criteria`, `u_technical_specification`, `work_notes`, `comments`, `state`, stb.
**Kimenet:** KB Article (HTML) — `title`, `summary`, `problem/symptoms`, `solution` (reprodukálható lépések), `category`, `audience`.

## 2. Technológiai verem

- **Nyelv:** Python 3.12
- **Keretrendszer:** DSPy 3.2.x (Signatures + Modules, GEPA optimalizáció)
- **ServiceNow integráció:** Table API (`requests`) — Story lekérés, KB létrehozás (CRUD)
- **Adatmodell:** Pydantic v2 + pydantic-settings
- **Konfiguráció:** `.env` (titkok) + `config.yaml` (beállítások)
- **LM hitelesítés:** Pi Agent GLM-5.2 a Z.ai API-n keresztül (`use_pi_auth: true`)
- **Deploy:** FastAPI webszerver (uvicorn) Docker konténerben, ServiceNow szerveroldali UI Action webhook fogadja.
- **Környezet:** a szülőkönyvtár `.venv`-je; telepíthető `pip install -e .` (pyproject.toml)

## 3. DSPy pipeline (a program magja)

Többlépcsős `dspy.Module`, minden predictor névvel ellátva (GEPA tudja célozni):

1. **`ExtractChange`** — Story szöveg → `change_summary`, `key_steps`, `audience`
2. **`DraftSections`** — kinyert információ → `title`, `problem`, `solution_steps`, `summary`
3. **`FormatKB`** — részek → ServiceNow-kompatibilis HTML

Ezeket a `StoryToKBArticle(dspy.Module)` láncolja össze. **Nincs hardcode-olt prompt** — minden utasítás a Signature docstring-ből jön.

## 4. Mappa-struktúra (jelenlegi)

```
snow_kb_generator/
├── Agent.md                    # ez a fájl
├── README.md                   # áttekintés, beállítás, használat
├── pyproject.toml              # csomag definíció (pip install -e .)
├── Dockerfile                  # FastAPI deploy konténer
├── docker-compose.yml          # Deploy konfiguráció
├── .gitignore
├── .env.example                # SNOW instance/user/password + LM API kulcsok
├── .env                        # TÉNYLEGES titkok (NEM verziókezelve)
├── requirements.txt
├── config.yaml                 # kb_knowledge_base, kategória, model nevek
├── src/snow_kb/
│   ├── __init__.py
│   ├── __main__.py             # python -m snow_kb belépési pont
│   ├── config.py               # .env + config.yaml betöltés (Settings, Secrets)
│   ├── servicenow_client.py    # ServiceNowClient (Table API + dry_run mock)
│   ├── schemas.py              # Pydantic: StoryData, ArticleSections, KBArticle
│   ├── signatures.py           # DSPy Signatures (ExtractChange, DraftSections, FormatKB)
│   ├── program.py              # StoryToKBArticle(dspy.Module)
│   ├── pipeline.py             # orchestrátor + assemble_story_text + configure_lm
│   ├── server.py               # FastAPI webszerver a ServiceNow webhook-nak
│   └── cli.py                  # argparse CLI (python -m snow_kb)
├── servicenow/                 # ServiceNow-ba másolandó scriptek
│   ├── README.md               # Telepítési útmutató
│   └── ui_action_script.js     # Szerveroldali UI Action script (REST hívás + work_notes update)
├── tests/                      # pytest tesztcsomag (171 teszt)
│   ├── conftest.py             # közös fixture-k
│   ├── test_config.py
│   ├── test_schemas.py
│   ├── test_signatures.py
│   ├── test_program.py
│   ├── test_pipeline.py
│   ├── test_servicenow_client.py
│   ├── test_server.py
│   └── test_cli.py
├── data/
│   ├── examples/               # gold (Story → KB) példapárok evalhez (MÉG ÜRES)
│   └── sample_stories/         # minta Story JSON (STRY0012345.json)
├── eval/                       # dataset + rich metric (MÉG CSAK TERV)
│   ├── dataset.py
│   └── metric.py
├── runs/                       # baseline.json, optimized.json (MÉG ÜRES)
├── artifacts/                  # lementett optimalizált program (MÉG ÜRES)
└── gepa_logs/                  # GEPA reflection logok (MÉG ÜRES)
```

## 5. Munkafolyamat (DSPy advanced workflow)

1. **Spec** — egy mondatban a feladat (lásd fent). ✅
2. **Program** — Signatures + Module a `dspy-fundamentals` szerint. ✅
3. **Data** — gold `Story → KB` példapárok, külön `trainset`/`valset`/`testset`. ⏳
4. **Rich metric** — `dspy.Prediction(score=.., feedback=..)`; a feedback "load-bearing" a GEPA számára. ⏳
5. **Baseline** — `dspy.Evaluate` a valset-en, eredmény `runs/baseline.json`. ⏳
6. **GEPA optimalizáció** — `auto="medium"`, `reflection_lm` külön, Pareto szelekció. ⏳
7. **Export & deploy** — `program.save(...)`, CLI/FastAPI burkolat, CI regressziós teszt. ✅

## 6. Működési elvek (álljunk ezekhez)

- **Nincs hardcode-olt prompt** — csak Signature docstring-ek.
- **Nincs `dspy.TypedPredictor`** — `dspy.Predict` Pydantic mezőkkel.
- **Globális LM** — `dspy.configure(lm=...)`, modulonként csak indokolt esetben override.
- **ServiceNow hívások mockolhatók** — `--dry-run` és mock Story-k, hogy kulcsok nélkül is lehessen fejleszteni.
- **Titkok sosem commitolódnak** — `.env` a `.gitignore`-ban, csak `.env.example` verziózik.
- **Baseline előtt nincs optimalizáció** — "no baseline, no claim".
- **Minden prediktor legyen elnevezve** — a GEPA tudja célozni.
- **Magyar kommentek** a kódban, docstring-ek angolul maradhatnak.
- **A kód önálló** — nincs külső projekt-függőség.

## 7. Állapot

- [x] Project mappa + `Agent.md` létrehozva
- [x] GitHub repo létrehozva (`szocpaul/snow-kb-generator`, private)
- [x] Skeleton fájlok + nem-kód fájlok (README, config.yaml, stb.)
- [x] `src/snow_kb/` implementálva (config, client, schemas, signatures, program, pipeline, cli, server)
- [x] Mock Story + `data/` mappa
- [x] Pytest tesztcsomag (171 teszt, mind zöld)
- [x] `pyproject.toml` (pip install -e . működik)
- [x] **Éles ServiceNow + LM (GLM-5.2) integráció tesztelve**
- [x] **Deploy: FastAPI webszerver + ServiceNow UI Action készen áll**
- [ ] Eval harness (dataset + rich metric) — **következő lépés**
- [ ] Baseline mérés
- [ ] GEPA optimalizáció
- [ ] Export optimalizált modell

## 8. Megjegyzések

- A `.venv` közös a szülőkönyvtárban; nincs saját virtuális környezet (amíg el nem térnek a függőségek).
- Éles ServiceNow PDI instance: `dev433980.service-now.com`.

## 9. Hol tartunk (utolsó frissítés: 2024-07-13)

- [x] **Core pipeline teljesen kész és működik élesben!**
- [x] ServiceNow kapcsolat beállítva (dev433980 instance).
- [x] LM hitelesítés beállítva: Pi Agent GLM-5.2 (via Z.ai endpoint).
- [x] CLI telepítve (`pip install -e .` megtörtént).
- [x] Éles teszt sikeres: Story feldolgozva, KB cikk létrehozva a ServiceNow IT KB-ben.
- [x] **FastAPI webszerver és ServiceNow UI Action integráció implementálva.**
- [x] A VPS szerver (Hetzner, publikus IP: 91.99.175.157) és a 8000-as port beállítva.
- [x] A ServiceNow Script Include REST hívással sikeresen eléri a szervert.
- [x] A szerver sikeresen generál és pushol KB cikket, majd a Table API-n keresztül frissíti a Story `work_notes` mezőjét.
- [x] UI Action gomb tesztelése a felületen (hiba elhárítva, szerveroldali scripttel működik).
- [x] A dupla `work_notes` bejegyzés javítva (a `current.update()` elhagyása megoldotta).

### Következő lépés: GEPA optimalizáció (DSPy 6-7. lépés)

1. `eval/dataset.py` implementálása:
   - `data/examples/` mappába kell gyűjteni 3-5 "arany" (gold) példapárt (Story szöveg -> várt KB cikk).
2. `eval/metric.py` implementálása:
   - Egy `rich_metric` függvény, ami `dspy.Prediction(score, feedback)`-ot ad vissza.
3. Baseline mérés:
   - `dspy.Evaluate` lefuttatása a jelenlegi (nem optimalizált) programon.
4. GEPA optimalizáció:
   - `dspy.GEPA(auto="medium")` lefuttatása a reflection modellel.
   - Optimalizált program elmentése az `artifacts/` mappába.

## 10. Hol tartunk a GEPA optimalizációban (utolsó frissítés: 2024-07-14)

- [x] **Update Set Code Analysis beépítve és élesben tesztelve!**
- [x] A pipeline sikeresen lekéri az Update Set módosításokat (XML payloadok), és a GLM-5.2 elemzi a tényleges forráskódot (Script Include, UI Action).
- [x] Az RLM (Deno sandbox) egy ismert bug (#9643) miatt stabil `dspy.ChainOfThought` lépésre lett cserélve, ami tökéletesen működik a GLM nagy kontextusablakával.

### Következő lépés: GEPA optimalizáció (Data + Metric)

A User megoldása: **Valós HTML KB Article template és legalább 5 meglévő cikk** lesz a Gold Set alapja.
1. **Adatgyűjtés (Holnap):** A User megkeresi és megadja a HTML formátumú sablonokat és a meglévő cikkeket.
2. **Feldolgozás:** Ezeket elmentjük a `data/examples/` mappába (template.html, article_1.html, stb.).
3. **`eval/metric.py` implementálása:** Egy rich_metric, ami összehasonlítja a generált HTML-t a User sablonjával és a Gold cikkekkel (struktúra, címsorok, stb.), és `dspy.Prediction(score, feedback)`-ot ad vissza.
4. **`eval/dataset.py`:** A cikkekből `dspy.Example` halmazt építünk train/val split-tel.
5. **Baseline mérés:** `dspy.Evaluate` a jelenlegi programon.
6. **GEPA futtatás:** `dspy.GEPA(auto="medium")` a reflection modellel.
7. **Mentés:** Optimalizált program elmentése az `artifacts/` mappába.
