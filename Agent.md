# Agent.md — snow_kb_generator

> Ez a fájl az AI ágens (és a fejlesztő) számára rögzíti a project célját, határait és működési elveit. Olvasd el, mielőtt bármit módosítasz a projectben.

## 1. Project célja

ServiceNow-ban a fejlesztők **Story-k** (`STRY...`) megvalósításán dolgoznak. Amikor a munka elkészül és a Story lezárul, erről automatikusan **Knowledge Base Article (KB)** készüljön. Ezt az átalakítást egy **DSPy AI pipeline** végzi: a Story adataiból strukturált, célközönségnek szóló, ServiceNow-kompatibilis KB cikket generál.

**Bemenet:** lezárt ServiceNow Story mezői — `short_description`, `description`, `acceptance_criteria`, `work_notes`, `comments`, `state`, stb.
**Kimenet:** KB Article (HTML) — `title`, `summary`, `problem/symptoms`, `solution` (reprodukálható lépések), `category`, `audience`.

## 2. Technológiai verem

- **Nyelv:** Python 3.12
- ** keretrendszer:** DSPy 3.2.x (Signatures + Modules, GEPA optimalizáció)
- **ServiceNow integráció:** Table API (`requests`) — Story lekérés, KB létrehozás (CRUD)
- **Adatmodell:** Pydantic v2
- **Konfiguráció:** `.env` (titkok) + `config.yaml` (beállítások)
- **Környezet:** a szülőkönyvtár `.venv`-je (dspy, pydantic, requests, python-dotenv, pyyaml elérhető)

## 3. DSPy pipeline (a program magja)

Többlépcsős `dspy.Module`, minden predictor névvel ellátva (GEPA tudja célozni):

1. **`ExtractChange`** — Story szöveg → `change_summary`, `key_steps`, `audience`
2. **`DraftSections`** — kinyert információ → `title`, `problem`, `solution_steps`, `summary`
3. **`FormatKB`** — részek → ServiceNow-kompatibilis HTML

Ezeket a `StoryToKBArticle(dspy.Module)` láncolja össze. **Nincs hardcode-olt prompt** — minden utasítás a Signature docstring-ből jön.

## 4. Mappa-struktúra (tervezett)

```
snow_kb_generator/
├── Agent.md                    # ez a fájl
├── README.md                   # áttekintés, beállítás, használat
├── .gitignore
├── .env.example                # SNOW instance/user/password + LM API kulcsok
├── requirements.txt
├── config.yaml                 # kb_knowledge_base, kategória, model nevek
├── src/snow_kb/
│   ├── config.py               # .env + config.yaml betöltés
│   ├── servicenow_client.py    # Table API: Story lekérés + KB létrehozás
│   ├── schemas.py              # Pydantic: StoryData, KBArticle, ArticleSections
│   ├── signatures.py           # dspy.Signature részek
│   ├── program.py              # StoryToKBArticle(dspy.Module)
│   ├── pipeline.py             # orchestrátor: fetch → generate → push
│   └── cli.py                  # `python -m snow_kb <story_id>`
├── data/
│   ├── examples/               # gold (Story → KB) példapárok evalhez
│   └── sample_stories/         # minta Story JSON mock adatokkal
├── eval/
│   ├── dataset.py              # train/val/test split (dspy.Example)
│   └── metric.py               # rich_metric (score + feedback) GEPA-hoz
├── runs/                       # baseline.json, optimized.json
├── artifacts/                  # lementett optimalizált program
└── gepa_logs/                  # GEPA reflection logok
```

## 5. Munkafolyamat (DSPy advanced workflow)

1. **Spec** — egy mondatban a feladat (lásd fent).
2. **Program** — Signatures + Module a `dspy-fundamentals` szerint.
3. **Data** — gold `Story → KB` példapárok, külön `trainset`/`valset`/`testset`.
4. **Rich metric** — `dspy.Prediction(score=.., feedback=..)`; a feedback "load-bearing" a GEPA számára.
5. **Baseline** — `dspy.Evaluate` a valset-en, eredmény `runs/baseline.json`.
6. **GEPA optimalizáció** — `auto="medium"`, `reflection_lm` külön, Pareto szelekció.
7. **Export & deploy** — `program.save(...)`, CLI/FastAPI burkolat, CI regressziós teszt.

## 6. Működési elvek (álljunk ezekhez)

- **Nincs hardcode-olt prompt** — csak Signature docstring-ek.
- **Nincs `dspy.TypedPredictor`** — `dspy.Predict` Pydantic mezőkkel.
- **Globális LM** — `dspy.configure(lm=...)`, modulonként csak indokolt esetben override.
- **ServiceNow hívások mockolhatók** — `--dry-run` és mock Story-k, hogy kulcsok nélkül is lehessen fejleszteni.
- **Titkok sosem commitolódnak** — `.env` a `.gitignore`-ban, csak `.env.example` verziózik.
- **Baseline előtt nincs optimalizáció** — "no baseline, no claim".
- **Minden prediktor legyen elnevezve** — a GEPA tudja célozni.
- **Magyar kommentek** a kódban (a `snow_rag` project konvenciója), docstring-ek angolul maradhatnak.

## 7. Állapot

- [x] Project mappa + `Agent.md` létrehozva
- [ ] Skeleton fájlok (`README`, `.gitignore`, `.env.example`, `config.yaml`, `requirements.txt`)
- [ ] `src/snow_kb/` csontváz (config, client, schemas, signatures, program, pipeline, cli)
- [ ] Mock Story + `data/`
- [ ] Eval harness (dataset + rich metric)
- [ ] Baseline mérés
- [ ] GEPA optimalizáció
- [ ] Export + CLI

## 8. Megjegyzések

- A szülőkönyvtárban lévő `snow_rag` project minta a ServiceNow integrációra és a `.gitignore`/`.env` konvenciókra.
- A `.venv` közös a szülőkönyvtárban; nincs saját virtuális környezet (amíg el nem térnek a függőségek).

## 9. Hol tartunk (utolsó frissítés: 2024-07-10)

- [x] **Core pipeline teljesen kész és működik élesben!**
- [x] ServiceNow kapcsolat beállítva (dev300344 instance).
- [x] LM hitelesítés beállítva: Pi Agent GLM-5.2 (via Z.ai endpoint).
- [x] CLI telepítve (`pip install -e .` megtörtént).
- [x] Éles teszt sikeres: STRY0010012 feldolgozva, KB cikk létrehozva a ServiceNow IT KB-ben.

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
