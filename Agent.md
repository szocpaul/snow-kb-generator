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

## 11. Feature: KB Duplicate Prevention & Update (SDD - spec-kit)

**Status**: ✅ Implementálva és élesben tesztelve (SDD)

A spec-kit (Spec-Driven Development) módszertan szerint került implementálásra.
- **Spec**: `specs/001-kb-duplicate-prevention/spec.md`
- **Plan**: `specs/001-kb-duplicate-prevention/plan.md`
- **Tasks**: `specs/001-kb-duplicate-prevention/tasks.md`

**Mit csinál?**
Megakadályozza, hogy egy Story-hoz többször létrejöjjön KB cikk.
1. Létrehoz egy `u_source_story` custom mezőt a KB cikken.
2. Generálás előtt a pipeline lekérdezi, van-e már cikk a Story-hoz.
3. Ha VAN és a felhasználó nem erősíti meg a frissítést: HTTP 409 (Abort).
4. Ha a felhasználó megerősíti (`force_update=true`): a meglévő cikk tartalmát FRISSÍTI (PATCH) ahelyett, hogy újat hozna létre.

**Szükséges ServiceNow konfiguráció (Manual Action - T018 - TÖRTÉNT)**:
A `kb_knowledge` táblához hozzá lett adva egy új String mező: `u_source_story`.
A ServiceNow UI Action script támogatja a felugró ablakos (confirm) megerősítést, és a `gsftSubmit` használatával hívja meg a szervert.

## 12. Holnap kezdjük: GEPA Optimalizáció (DSPy 3-6. lépés)

**Dátum**: 2026-07-16
**Cél**: A GLM-5.2 modell promptjainak (Signature docstring-ek) finomhangolása a te valós vállalati KB formátumod alapján.

### A teendőm holnap reggel (User):
- Megkeresni és átadni **1 db KB Article template**-et (HTML formátumban).
- Megkeresni és átadni **legalább 5 db meglévő, jól megírt KB Article**-t (HTML formátumban).
- Ezeket el kell menteni a `data/examples/` mappába (pl. `template.html`, `article_1.html`, stb.), vagy be kell másolni a chatbe.

### Az ágens teendője (Miután megvannak az adatok):
1. Feldolgozni a HTML sablont és kinyerni belőle a struktúrát (Title, Issue, Solution, stb.).
2. Megírni az `eval/metric.py`-t: Egy `rich_metric` függvény, ami `dspy.Prediction(score, feedback)`-ot ad vissza. Összehasonlítja majd a generált cikket a te sablonoddal.
3. Lefuttatni az `eval/dataset.py`-t a megadott 5 cikkből (trainset/valset).
4. Futtatni egy Baseline mérést a jelenlegi programmal.
5. Elindítani a `dspy.GEPA(auto="medium")` optimalizációt.
6. Elmenteni az optimalizált programot az `artifacts/` mappába.

## 13. Hol tartunk (utolsó frissítés: 2026-07-16 - Esti Zárás)

### Befejezett Feature: Team-Based KB Templates (SDD 002)
- **Státusz:** ✅ Élesben tesztelve és működik! A rendszer sikeresen felismeri az `assignment_group` mezőt, és a csapathoz tartozó KB sablon alapján generálja a cikket.
- **Modelek:** A GLM-5.2 usage limit miatt a rendszer áttért a **lokális Qwen3.6-35B** modellre (llama.cpp). A GEPA reflectionhöz a GLM-5.2 maradt konfigurálva (használjuk majd).
- **GeneratKbFromTemplate Signature:** Bevezetésre került egy új prediktor, ami képes a HTML sablont egy-az-egyben kitölteni, kikerülve a régi 4-mezős architektúra korlátait.

### Technikai Gospekák (Gyökérproblémák amiket megoldottunk):
1. `kb_knowledge_base` táblán nincs `text` mező, csak a `kb_knowledge` cikkeken. A sablon keresését ide állítottuk át.
2. `max_tokens=2000` túl kevés volt a 7-szekciós HTML-hez, átálltunk 8000-re.
3. A modellek gondolkodási fázisa (`reasoning_content`) tokeneket pazarolt, a `--reasoning off` (llama.cpp) és a `Predict` használata megoldotta.
4. A Tailscale hálózatot a `tailscale serve` oldotta meg a Qwen endpoint publikálására.

### Holnap Hol Tartunk: GEPA Optimalizáció
**Cél:** A Qwen modell promptjainak (DraftSections, FormatKB) finomhangolása a te valós vállalati KB formátumod alapján.
1. User átad 1 KB template-et + 5 meglévő cikket.
2. Metrika (`eval/metric.py`) implementálása.
3. Baseline mérés.
4. GEPA futtatás (reflection: GLM-5.2).

## 14. Szerkesztési Szabály (Anti-Loop)

**Ha egy edit kétszer egymás után elbukik vagy no-op, ÁLLJ LE.**
- Olvasd el újra a fájlt és a teljes teszt-hibaüzenetet.
- Fogalmazd újra a hipotézist (mi a valódi probléma?).
- Csak utána editelj.
- **Soha ne próbáld ugyanazt az editet harmadszor.**

## 15. Hol tartunk a GEPA optimalizációban (utolsó frissítés: 2026-07-24)

### Befejezett munka (T001-T010)
- **SDD Specifikáció, Terv, Feladatlista (T001-T003):** A GEPA optimalizáció specifikációja (`specs/003-gepa-kb-quality/spec.md`), terve (`plan.md`), és feladatlistája (`tasks.md`) kész van. A gold dataset (`data/examples/gold_dataset.md`) 5 arany példapárt tartalmaz (Story → KB cikk), amelyek a te Integration Team Template sablonod (KBA1-KBA11) szerint épülnek fel.
- **Gold Dataset Loader (T003):** A `eval/dataset.py` implementálva (betölti a gold_dataset.md-t, szeparált trainset 3 / valset 2 felosztás, dspy.Example objektumok). A dataset tesztek mind zöldek (11/11).
- **Rich Metric (T005):** A `eval/metric.py` implementálva (multi-axis score: structure_match, content_accuracy, template_adherence; natural-language feedback). A metric tesztek mind zöldek (5/5).
- **Baseline (T009):** A `eval/baseline.py` implementálva (dspy.Evaluate(devset=valset, metric=rich_metric, num_threads=1)). A baseline tesztek mind zöldek (5/5).

### Hol tartunk (T011-T019)
- **GEPA Optimizer (T011):** A `eval/gepa_optimize.py` implementálva (dspy.GEPA(metric, auto="light", reflection_lm=Kimi K3, candidate_selection_strategy="pareto", track_stats=True, log_dir="./gepa_logs")). A GEPA tesztek elbuknak, mert a `run_gepa_optimization()` függvény a `optimizer.compile()` hívást végzi, ami a `optimized_program`-ot adja vissza, nem az `optimizer`-t. Ezért a tesztek nem tudják ellenőrizni az `optimizer` attribútumait (metric, reflection_lm, candidate_selection_strategy, log_dir).

### Következő lépés (T012-T019)
- **T012-T013:** A GEPA compile lefuttatása és az alkalmazott reflection javaslatok kinyerése.
- **T014-T016:** Az optimalizált program mentése, a FastAPI szerver frissítése, és a pipeline frissítése az optimalizált program használatához.
- **T017-T019:** A teljes tesztcsomag futtatása, a dokumentáció frissítése, és az éles end-to-end validáció.

### Technikai Probléma (T011)
A `run_gepa_optimization()` függvény a `optimizer.compile()` hívást végzi, ami a `optimized_program`-ot adja vissza, nem az `optimizer`-t. Ezért a tesztek nem tudják ellenőrizni az `optimizer` attribútumait. A megoldás: a `run_gepa_optimization()` függvényt úgy kell módosítani, hogy az `optimizer`-t is visszaadja, nem csak az `optimized_program`-ot.

## 16. GEPA optimalizáció BEFEJEZVE (utolsó frissítés: 2026-07-26)

### Eredmények (T011-T018)
- **T011:** GEPA optimizer javítva — `run_gepa_optimization()` csak az optimizert adja vissza; a compile a `compile_with_gepa()`-be került. Tesztek a DSPy 3.2.x API-hoz igazítva (`metric_fn`, `lm.kwargs["temperature"]`).
- **T012-T013:** GEPA compile lefutva (`python -m eval.gepa_optimize --auto light`, ~42 perc, 589 iteráció). **Baseline: 0.100 → Optimized: 0.600** (6x javulás a valset-en).
- **T014:** Optimalizált program mentve: `artifacts/program.json` (betöltés verifikálva).
- **T015:** `server.py` startup-kor betölti az optimalizált programot (fallback: alap StoryToKBArticle).
- **T016:** `pipeline.py` `program_path` paraméter + `_load_program()` helper.
- **T017:** Teljes tesztcsomag zöld (208/208).

### Elhárított buktatók
- A metric `pred.html`-t várt, de a program `Prediction(article=KBArticle)`-ot ad vissza → a metric mostantól mindkettőt támogatja.
- A Kimi K3 reflection LM rosszul volt konfigurálva: a helyes beállítás `openai/k3` + `https://api.kimi.com/coding/v1` + OAuth `access` token (NEM `kimi-k3` OpenRouteren).
- A `gepa_logs/` checkpoint a hibás (0-s score-os) futást őrizte → tiszta újrafuttatás kellett.
- A Kimi OAuth token a futás vége felé lejárt (~589. iteráció), de a run így is érvényes eredménnyel zárult.

### Hátralévő (T019)
- Éles end-to-end validáció: szerver újraindítás az optimalizált programmal + valós Story generálás a ServiceNow-ból.

## 17. T019 Éles end-to-end validáció BEFEJEZVE (2026-07-26)

- FastAPI szerver újraindítva; az optimalizált program (`artifacts/program.json`) startup-kor betöltődött.
- STRY0010010 generálás `push=false`: ✅ sikeres (az optimalizált programmal).
- Éles push `force_update=true`: ✅ a KB cikk létrejött/frissült: https://dev433980.service-now.com/kb_view.do?sys_kb_id=bbe5d9b62fce0b10698771ba6fa4e3b8
- **A specs/003-gepa-kb-quality összes taszkja (T001-T019) kész.** A GEPA-optimalizált program élesben szolgálja ki a ServiceNow UI Action webhookot.

## 18. Spec 004: Hallucination-Free KB Generation BEFEJEZVE (2026-07-26)

### Probléma
A gold dataset fiktív KB cikkszámai (KB0012345-KB0012349) hallucinált hivatkozásokként jelentek meg a generált cikkekben.

### Megoldás (spec-kit: specs/004-no-hallucinated-references)
- **T001-T002:** Gold dataset sanitizálva (5 fiktív KB szám → `KBXXXXXXX` placeholder) + dataset teszt.
- **T003-T005:** `rich_metric` hallucination axis (új súlyok: 0.3/0.3/0.2/0.2) + 3 új teszt.
- **T006-T008:** `strip_hallucinated_references()` guardrail a pipeline-ban (push előtt stripeli a story_text-ben nem szereplő KB számokat) + 4 új teszt.
- **T009:** Új baseline az új metric-kel: **0.386**.
- **T010:** GEPA újrafuttatva tiszta adaton: **optimized 0.962** (vs baseline 0.386; korábbi futam: 0.600).
- **T011:** Valset validáció: **0/2 hallucináció**.
- **T012:** Teljes tesztcsomag: **216/216 zöld**.
- **T013:** Szerver restart + éles STRY0010010 validáció: a KB cikk hallucináció-mentes (ServiceNow API-val verifikálva).

### Tanulság
A hallucináció ellen 3 védelmi vonal épült: (1) tiszta tanítóadat, (2) metric-büntetés (GEPA feedback), (3) produkciós guardrail. A helyes KB endpoint: `openai/k3` @ `https://api.kimi.com/coding/v1` (OAuth).

## 19. Spec 005: Real Related KB Articles BEFEJEZVE (2026-07-26)

### Probléma
A "Table of related KB articles" szekció (a csapat-sablon kötelező eleme) hallucinált short descriptionöket tartalmazott placeholder számokkal — valódi adatforrás híján.

### Megoldás (specs/005-real-related-kb-articles)
- **T001:** `ServiceNowClient.search_kb_articles(query, limit)` — szöveges keresés a published kb_knowledge cikkekben.
- **T002-T003:** A pipeline generálás előtt KB-t keres a Story short_description-jére; a találatok `related_articles_context`-ként a program új inputjára kerülnek (üres → "N/A" instrukció a signature-ben).
- **T004-T005:** Guardrail + metric kiterjesztve: a keresési találatok "ismert" hivatkozások (0 false positive).
- **T006:** GEPA újrafuttatva az új signature-szel: baseline 0.300 → **optimized 0.962**.
- **T007:** 221/221 teszt zöld; éles STRY0010010 validáció: a dev instance-on nincs tematikus cikk → a szekció helyesen **"N/A"** (a "Spam" keresés bizonyítja, hogy találat esetén valódi számok kerülnének be).

### Spec 005 kiegészítés — valódi e2e bizonyíték (2026-07-26 este)
- Teszt cikk létrehozva: **KB0010010** (Jira REST Integration Guide, a felhasználó kérésére megtartva).
- A keresés javítva: kulcsszó-kinyerés (rövidítések/tulajdonnevek elől), OR query, published∪összes unió, kliens-oldali overlap-rangsorolás.
- Éles STRY0010010 újragenerálás: a "Related articles" tábla **3 valódi cikket** tartalmaz (KB0010009, KB0010010, KB0010001) — mind a hármat ServiceNow API-val verifikáltuk. A spec 005 e2e bizonyítva.

## 20. Spec 006: Template Simplification BEFEJEZVE (2026-07-26)

### Változás
A sablonból kikerült: a "Knowledge Base Structure for Interface Documentation" H1, a "Theme:" sorok, és minden "Target Audience" szekció (+ a related articles tábla 3. oszlopa). A célközönség stílusként megmaradt: az ExtractChange.audience a template-generálás instrukciójába kerül ("style only, do NOT create a section").

### Lépések
- Lokális sablon (md+html) lecsupaszítva: KBA1-KBA11 címsor + Content only.
- Gold dataset: 35 Theme sor, 35 Target Audience szekció, 5 target audience oszlop törölve.
- Élő ServiceNow sabloncikk (KB0010008) Table API-val frissítve.
- GEPA újrafuttatva: baseline 0.300 → **optimized 0.850**.
- Éles validáció (STRY0010010): nincs Theme/Target Audience/Structure főcím; a related tábla 2 oszlopos, 3 valódi cikk (KB0010009, KB0010010, KB0010001).
- 221/221 teszt zöld.

## 21. Esti zárás (2026-07-26) — Holnap: spec 007 implementáció

### Ma készült el (spec 004 + 005 + 006)
- **Spec 004 (hallucináció-védelem):** dataset sanitization, hallucination metric axis, `strip_hallucinated_references()` guardrail. 3 védelmi vonal.
- **Spec 005 (valódi related cikkek):** `search_kb_articles()` kulcsszavas OR query + overlap-rangsorolással; `related_articles_context` input; guardrail/metric known_refs kiterjesztés. Éles bizonyíték: 3 valódi cikk a related táblában (KB0010009, KB0010010, KB0010001). Teszt cikk KB0010010 megtartva.
- **Spec 006 (sablon-egyszerűsítés):** H1/Theme/Target Audience szekciók kivéve (lokális + élő KB0010008 sablon); az audience "style only" instrukció; gold dataset megtisztítva; GEPA újrafutva: 0.300 → 0.850.
- **Tesztek:** 221/221 zöld. Éles demo cikk: KB0010009 (STRY0010010 alapján).

### Ismert nyitott probléma (holnapi téma)
Outbound Story (STRY0010010) esetén az **Inbound szekció tartalommal töltődik** "N/A" helyett. Diagnózis: a metric irány-vak (nem bünteti) → a Kimi K3 reflection nem kap jelet → a Qwen 35B a "fill every section" utasítást követi. Nem tudásbeli hiba, hanem visszajelzési lánc szakadás.

### HOLNAP ITT FOLYTATJUK: spec 007 implementáció
- **Spec:** `specs/007-direction-aware-quality/` (spec.md + plan.md + tasks.md, commit 38ca370) — ELKÉSZÜLT, user review alatt, implementáció MÉG NEM kezdődött.
- **Taszkok:** T001-T011 — detect_direction() a metric-ben, kategorikus irányszabály a signature-ben, SkilledProposer integráció (pip install skilled-proposer, extra_guidance), GEPA újrafutás, éles validáció.
- **Környezet:** a Qwen LM a desktop gépen fut (Tailscale :8033) — holnap ellenőrizni kell, hogy él-e, mielőtt a GEPA futna.
- **Kimarad (out of scope):** pipeline-guardrail N/A-kényszer — csak ha a metric+GEPA útvonal nem elég.

### Fontos technikai emlékeztetők
- Helyes venv: `../.venv` (szülőkönyvtár), NEM rendszer-Python.
- Kimi K3 reflection: `openai/k3` @ `https://api.kimi.com/coding/v1` (OAuth access token; a token ~1 óra után lejárhat futás közben — a run így is befejeződik, de a végén "invalid API key" warning normális).
- GEPA futtatás előtt MINDIG töröld a `gepa_logs/`-ot (a checkpoint a régi, esetleg hibás állapotot őrzi).
- Szerver restart: `pkill -f "uvicorn snow_kb"` után `nohup ../.venv/bin/uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000 >> server.log 2>&1 & disown` (setsid néha elveszti a processt).

## 22. Spec 007+008: Evidence-First KB Generation BEFEJEZVE (2026-07-27)

### Megvalósult (T001-T014)
- **Metric:** `detect_direction()` + Direction violation + Unsupported section tengelyek, explicit feedback a reflection modellnek.
- **Signature:** evidence-first ("The template is a MENU, not a mandate; no evidence, no section").
- **Gold dataset:** 5 N/A-only blokk + 5 fiktív related sor törölve; dataset teszt irány-érzékeny.
- **SkilledProposer:** anti-overfitting proposer + `additional_instructions` (evidence-first + KB-hallucináció tiltás). FONTOS: `prompt_model=Kimi K3` kell — nélküle a lokális Qwennel generálna (lassú/gyenge).
- **Kimi token fix:** `_RefreshingKimiLM` — a ~20 perces OAuth token miatt minden hívás előtt auth.json újraolvasás + proaktív pi-CLI refresh (<120 mp). A `dspy-lm-auth` NEM kezeli a kimi-coding OAuth refresh-t (openai-codex fókusz).
- **GEPA:** 0.300 → 0.600 (szigorúbb metric mellett; az irányszabály bekerült az instrukciókba).
- **Guardrail (out-of-scope-ból behozva, mert kellett):** `strip_direction_violating_sections()` — a 35B az explicit szabály ellenére 1/2 valset példánál mégis kitöltötte az Inbound szekciót → determinisztikus post-process törli.
- **Validáció:** valset 0/2 violation (guardraillal); éles STRY0010010: csak támogatott szekciók (Overview, Outbound, Usage, Testing), nincs Inbound, 3 valódi KB ref. 232/232 teszt zöld.

### Tanulság
Gyenge task modellnél (35B) a prompt-szabály önmagában nem garancia — a metric+GEPA jelentősen javít, de a kritikus tiltásokhoz kell a determinisztikus guardrail is.

## 23. Spec 009 + Code Review BEFEJEZVE (2026-07-27)

### Code review javítások (dspy-fundamentals best practice)
- `related_articles_context` desc N/A-ellentmondás javítva; `audience: Literal[...]`; `title` OutputField (cím-hack megszűnt); `ANALYZE_CHANGES_QUERY` konstans; comment rot takarítás.

### Spec 009: Legacy draft/format ág kivezetve
- Prediktorok 5 → 3 (`analyze_changes`, `extract`, `generate_from_template`); `template_context` kötelező.
- **Kritikus felfedezés:** az összes korábbi GEPA futás a legacy ágat optimalizálta (a gold datasetben nem volt template_context) — a mostani az ELSŐ valós, produkciós útvonalon mért optimalizáció.
- Dataset: `template_context` input hozzáadva (integration_team_template.html).
- llama.cpp `-np 4` + GEPA `num_threads=4`: 25s → 8s/rollout; a futás ~25 perc.
- **Eredmény: baseline 0.300 → optimized 0.600** (valós template úton); valset 0/0 violation.
- Direction guardrail kiterjesztve: az N/A-s irány-szekciót is törli (evidence-first: omit, ne N/A).
- Éles validáció (STRY0010010): tiszta fejlécek, valódi cím, 233/233 teszt zöld.

## 24. Esti zárás (2026-07-27) — Holnap: N/A-only szekciók kezelése

### Nyitott probléma (holnapi téma)
A modell az "omit" helyett "N/A"-t ír a támogatatlan szekciókba (az éles cikkben: "Known Issues / Content / N/A"). Az irány-szekciókra (Inbound/Outbound) már van guardrail, de az általános eset nincs lefedve.

### HOLNAP ITT FOLYTATJUK (4 lépés, ~40 perc összesen)
1. **Metric-bővítés:** az N/A-only szekció büntetése, ha a goldban hiányzik ("N/A-only section '<h2>' present but absent in gold — omit it"). Jelenleg a metric VAK rá: a `_section_has_content()` az N/A-t "nincs tartalom"-ként értékeli → nincs büntetés → a GEPA nem tanulja.
2. **Guardrail:** `strip_na_only_sections()` a pipeline-ban — minden olyan <h2> szekció törlése, aminek tartalma csak "N/A" (determinisztikus biztosíték, a metric+GEPA mellett).
3. **GEPA újrafutás** az új metric-kel (~25-30 perc az -np 4 slotokkal + num_threads=4).
4. **Éles validáció** STRY0010010 → a Known Issues N/A-nak el kell tűnnie.

### Miért kell mindkettő? (a tegnapi tanulság ismételve)
A metric-büntetés a GYAKORISÁGOT csökkenti (GEPA megtanulja), a guardrail a KOCKÁZATOT nullázza (35B gyenge instruction-following miatt a prompt-szabály nem 100%-os garancia).

### Környezet holnap
- llama.cpp a desktopon: `.\llama-server.exe -m "Qwen3.6-35B-A3B-NSC-ACE-SABER-Q4_K_M.gguf" --fit on --fit-ctx 131072 --fit-target 256 -np 4 -fa on --no-mmap -b 2048 -ub 2048 -ctk q8_0 -ctv q8_0 --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0 --presence-penalty 0.0 --repeat-penalty 1.0 --reasoning off --jinja --host 0.0.0.0 --port 8033`
- LM-élteszt GEPA előtt: a `chat/completions` endpoint 200-at adjon (ha 502 → llama-server nem fut).
- GEPA futtatás: `rm -rf gepa_logs && nohup ../.venv/bin/python -m eval.gepa_optimize --auto light > runs/gepa_run.log 2>&1 & disown`
- Szerver restart: `pkill -f "uvicorn snow_kb"; sleep 2; setsid nohup ../.venv/bin/uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000 >> server.log 2>&1 < /dev/null & disown`

### Mai állapot (mind commitolva és pusholva)
- Spec 009 kész: 3 prediktor, template kötelező, első VALÓS template-úton mért GEPA (0.300→0.600), 233/233 teszt.
- Éles demo cikk: KB0010009 (STRY0010010).

### 24. szekció BEFEJEZVE (2026-07-28)
- **Metric:** `_find_na_only_sections()` — N/A-only szekció büntetve, ha a gold kihagyja + feedback. False-positive fix: az N/A-jelölés jelenléte kötelező (rövid valódi szekciók védve).
- **Guardrail:** `strip_na_only_sections()` a pipeline láncban (direction → N/A-only → hallucination).
- **GEPA újrafutás** az új metric-kel: baseline 0.300 → optimized 0.450 (szigorúbb metric; ~40 perc).
- **Valset:** 0/0/0 (direction, unsupported, N/A-only).
- **Éles validáció:** STRY0010010 cikk N/A-mentes (Overview + Outbound); a modell a Testing/Usage szekciókat is kihagyta — az evidence-first korrekt, de figyelendő, hogy a modell ne essen át a ló túloldalára (alul-generálás).
- 239/239 teszt zöld.

## 25. Metric-tisztítás + GEPA medium BEFEJEZVE (2026-07-28)

- **A:** Régi N/A-check (`_check_template_adherence`) kivezetve a metricből — az evidence-first óta zaj volt.
- **B:** GEPA újrafutás tiszta metric-kel: **baseline 0.400 → optimized 0.600** (~27 perc). A 16000-es max_tokens a rolloutokat lassítja, de a vége felismerhetően felgyorsul.
- **Valset:** 0/0/0 (direction, unsupported, N/A-only).
- **Éles validáció (STRY0010010):** mind a 7 támogatott szekció visszatért (az alul-generálás megoldódott!), nincs N/A, nincs Inbound, tiszta befejezés.
- **Kimi Code kvóta:** a futás alatt merült ki (99.97%, reset 07-28 20:55) — a következő GEPA futásokig várjunk a resetre; a Qwen-alapú generálás (éles pipeline) kvóta-mentes.
- 239/239 teszt zöld.

## 26. ARCHITEKTÚRA-VÁLTÁS: Kimi-direct task modell (2026-07-28)

### Mérés, ami eldöntötte
- Qwen 35B base: 0.300 | Qwen+GEPA (órák optimalizálás): 0.600 | **Kimi K3 base, GEPA NÉLKÜL: 0.655**
- Az erős modell nyersen is felülmúlja a gyenge modell optimalizáltját → a lokális+GEPA architektúra megtérülése megszűnt.

### Változás
- `config.yaml`: `pipeline.task_model: "kimi"` (új opció; `"local"` = régi Qwen fallback).
- `pipeline.configure_lm()`: kimi ág a `_RefreshingKimiLM`-mel (auto OAuth refresh); temperature=1.0 kötelező (K3 csak azt fogadja).
- Éles validáció (STRY0010010): tiszta cikk Kimi K3-mal — minden guardrail változatlanul aktív.
- A GEPA nem kuka: Kimi task modellel is futtatható (kisebb megtérülés), és a checkpoint megőrzve.
- 243/243 teszt zöld.

### Backlog: külön spec-ek várakoznak
- **Docstring-konszolidáció:** a `GenerateKbFromTemplate` instrukció rövidítése/átstrukturálása (spec 010-ből kiválasztva).
- **Valset bővítés prod példákkal** (a 3 régi sablonú cikk — LDAP, Jira bidir, KB Generator — kézi gold-minőségűvé tétele után).

## 27. Esti zárás (2026-07-28) — Holnap: spec 010 implementáció (T001)

### Ma történt (nagy nap!)
- **Architektúra-váltás:** Kimi-direct task modell (`task_model: "kimi"` a config.yaml-ben). A döntő mérés: Kimi K3 base **0.655** vs Qwen+GEPA 0.600. Éles validáció mindkét Story-n sikeres (STRY0010010 + UI Action-nel STRY0010014 → KB0010012, a korábban csonkított cikk meggyógyult).
- **Gold dataset:** példa 6 (SolMan bidirectional, 1-5. példa stílusában kézzel írva) + példa 7 (ALMEX SOAP). Jelenleg 7 példa, 4 train / 3 val.
- **Pipeline javítás:** `sanitize_html_field()` — a Story HTML mezők most plain textként érkeznek (gold ↔ produkció konzisztencia).
- **Spec 010 megírva (NINCS implementálva):** `specs/010-human-style-articles/` (spec.md + plan.md + tasks.md) — emberi hangnem a cikkekben.

### HOLNAP ITT FOLYTATJUK: spec 010 T001-T014
1. **T001-T003:** `BANNED_PHRASES` konstans + signature stílus-blokk (docstring végéhez, a meglévő szöveg érintetlen)
2. **T004-T007:** StyleJudge (LLM-as-judge, Kimi K3) a metric-be, 5. tengely, új súlyok (0.25/0.25/0.15/0.15/0.20), hibatűrés 0.5
3. **T008-T009:** SkilledProposer style guidance
4. **T010-T014:** baseline → GEPA (≤250 call, Kimi task+reflection) → style javulás igazolása → éles validáció → docs

### Fontos emlékeztetők holnapra
- A Kimi Code kvóta figyelendő (a rolloutok most Kimi-hívások!); a T011 GEPA max 250 call.
- A K3 csak `temperature=1.0`-t fogad el (már be van építve).
- A GEPA checkpoint a tegnapi leállított futásból megvan, de a spec 010 új metric-kel tiszta futás kell (`rm -rf gepa_logs` a futás előtt).
- Backlog: docstring-konszolidáció (külön spec), valset bővítés prod példákkal.

## 28. Spec 010 implementáció + metrika-javítás (2026-07-29) — RÉSZBEN KÉSZ, style-GEPA kérdés nyitott

### Modell-döntés (tiszta mérések, `cache=False`!)
- Kimi K3: **0.769** | lokális Qwen3.6-35B-A3B: **0.733** (régi dataset, 3 val) — a K3 jobb, de a task modell a **lokális Qwen marad** (GEPA-rolloutok marginális költsége nulla). Reflection/proposer: **Kimi K3** marad.
- K2.7 Coding kimérve: 0.519 (thinking-overhead, kiesett).
- **FONtos:** a DSPy disk cache (`~/.dspy_cache`) modell-azonosítás nélkül visszajátssza a válaszokat — a mérési scriptekben `cache=False` KÖTELEZŐ (`eval/baseline.py`, `eval/gepa_optimize.py` már így fut).

### Dataset-tisztítás + bővítés
- Gold HTML-ekből a tiltólistás fordulatok kiszedve ("This document describes/outlines", "seamless") — a content tengely korábban azt jutalmazta, amit a style axis büntet.
- Példa 5 story work_notes tisztítva (LDAP/auth maradvány törölve).
- Új 8. példa (SAP S/4HANA outbound OData, szintetikus) → **4 train / 4 val**.
- **KB0010015 stílus-referencia letöltve:** `data/examples/kb0010015_style_reference.html` (a style judge pozitív mintája).

### Spec 010 implementáció (T001-T009b, T010-T011 kész)
- `BANNED_PHRASES` (eval/metric.py) + signature WRITING STYLE blokk (US1) — éles STRY0010013 cikkben **0 találat a tiltólistára** ✅
- `StyleJudge` + `_style_score()` az 5. tengelyhez (US2), hibatűrés 0.5 (FR-002); új súlyok 0.25/0.25/0.15/0.15/0.20
- Judge validálva (SC-002): gépies teszt-ikon **0.00**, KB0010015 **1.00**
- SkilledProposer guidance kiegészülve stílus-szabályokkal (US3); evidence-first szabályok megmaradtak
- `eval/baseline.py` CLI: `python -m eval.baseline --model local|kimi --output ...` (T009b; `scripts/` törölve)

### Metrika-javítás (a nap legfontosabb tanulsága)
- A `_extract_facts` korábban a gold <p> mondatok **első 50 karakterét** illesztette → a GEPA a gold-megfogalmazás utánzását jutalmazta, és a "This document describes..." sémát KÖTELEZŐVÉ kódolta az instrukcióba (pareto-nyertes cand 2!).
- Javítva: **stílus-semleges tény-illesztés** (idézett nevek, snake_case/camelCase azonosítók, ALLCAPS, URL-ek, rekordszámok, domain whitelist) — a TÉNYEKET jutalmazza, nem a fogalmazást.

### Mérési eredmények (új dataset, új metric, cache=False)
- Baseline (lokális Qwen): **0.699** (`runs/baseline.json`) — EZ a referencia
- Első GEPA (régi metric): style 0.425 → 0.425 (nem javult — a metrika-bug miatt)
- Próba-GEPA 60 call (új metric): a tiltó jelöltek 0.77-0.78-ra javultak, de a minibatch-zaj miatt a kiválasztás zajos; a teljes 200 call-os futás elnapolva
- Éles STRY0010013: SC-001 ✅ (0 tiltólista-találat), judge 0.45 (kritika: monoton "Label: Description" bullet-ritmus), SC-003 emberi review folyamatban

### KÖVETKEZŐ ALKALOM ITT FOLYTATJUK
1. Döntés: teljes 200 call-os GEPA a javított metrikával (~1.5-2 óra) — a style axis (0.425) javulásáért, VAGY a mostani szint elfogadása
2. Nyitott: a lokális Qwen formai ritmus-változatossága gyenge — lehet, hogy a style-plafon 0.5-0.55
3. T012-T014 utána: optimized vs baseline tengelyenként (`runs/t012_style_compare.json` minta-script a /tmp-ben — érdemes `eval/`-be emelni), éles validáció, docs

### Egyéb
- Tesztek: **258/258 zöld** a `.venv` interpreterrel (a rendszer-pythonban nincs fastapi/skilled_proposer!)
- `skilled-proposer` telepítve a `.venv`-be
- `config.yaml`: `task_model: "local"` (az éles pipeline is lokális Qwennel fut most)

## 29. DSPy 3.3.0 frissítés + spec 010 review-javítások (2026-08-07)

- **DSPy 3.3.0b1 → 3.3.0 stabil** a közös `../.venv`-ben (a 3.3.0 aug. 3-án jelent meg; `gepa` 0.1.1 maradt). **258/258 teszt zöld** az új verzióval.
- A 3.3.0 GEPA API-változásai (`detailed_results` alakzatok) NEM érintik a kódot: a `val_aggregate_scores` mező megmaradt, az `extract_applied_suggestions` `hasattr`-védett; a `best_outputs_valset` most dict, de a kód csak `len()`-t hív rá.
- **Spec 010 review utáni javítások** (spec.md/plan.md/tasks.md): új **T010c** (per-axis perzisztálás — eddig csak `average_score` íródott, a T012 mérhetetlen volt), T011 preflight + checkpoint-resume szabály (DSPy 3.3.0 `log_dir`-resume verifikálva), T012 számszerűsítve (style ≥ baseline + 0.05, többi tengely max −0.02), T013 emberi review = MANUÁLIS KAPU, FR-007/FR-008, plan.md interpreter (`../.venv`) rögzítve.
- A T010c-hez: a `runs/t012_style_compare.json` minta-scriptet (még /tmp-ben) érdemes `eval/`-be emelni — ez a per-axis összevetés alapja.

## 30. Spec 010 LEZÁRVA: GEPA 200-call + T012-T013 (2026-08-08/09)

### T011 GEPA futás (dedikált autonóm agenttel, prime-agent long-running arch)
- 200/200 call, ~3.5 óra, lokális Qwen (`-np 4`, `num_threads=4`) + Kimi K3 reflection; infra-watcher agent figyelte a llama.cpp endpointot (egy hamis riasztás volt: a 4 slot telítettsége ≠ halott szerver — a watcher kritériumai utána pontosítva: smoke 90s + log-mtime stagnálás-ellenőrzés)
- Eredmény: best valset 0.873 (baseline 0.773)

### T012 — dupla mérés után ELFOGADVA (emberi döntés)
- Első gate PIROS volt (structure −0.042 / content −0.021), de a baseline ÉS optimized újramérés kimutatta: a 4 példás valseten a zaj ±0.05-0.08 (a baseline content-je is 0.766→0.682-öt szór két azonos futás közben!)
- **2×2 tartomány-elemzés:** style base 0.450-0.463 vs opt 0.600-0.650 (**átfedésmentes, valós javulás**); template 0.750→1.000; structure/content átfedő tartományok (zaj); összesített 0.755-0.773 → 0.825-0.859
- Módszertani tanulság a spec SC-004-ben rögzítve: egyetlen mérés nem dönt, ±0.05 zaj-sáv vagy dupla mérés kell

### T013 — az emberi review hallucinációt fogott! (a metrika nem)
- A cikk 'ALDI: CHG Scheduled' Business Rule-nevet említett — a Story-ban 0 előfordulás. A modell az `aldi.atlassian.net` URL-ből + a base docstring 'ALDI: CHG Scheduled' PÉLDAMONDATÁBÓL fabrikálta (a saját példánk volt a méreg!)
- Root cause lánc: (a) fabrikált név a style-blokk példájában; (b) **a CLI nem töltötte be az optimized programot** (program_path hiányzott a cli.py-ból — a server betölti, a CLI nem); (c) a hallucináció-tengely csak KB-számokat validál → **metrika-vakfolt**
- Hotfix-lánc: signatures.py példacsere + anti-fabrikációs tiltás | program.json artifact-hotfix (backup megvan) | cli.py program_path | újragenerálás optimized programmal → 'ALDI' 0 találat, BR funkcióval hivatkozva, SC-001 ✅, 265/265 teszt ✅
- Emberi review: **JÓVÁHAGYVA** ("nagyon tetszik a generált KB cikk")

### Backlog (spec 011-jelöltek)
1. **Metrika-vakfolt**: a hallucináció-ellenőrzés terjedjen ki nevesített komponensekre (minden idézett/CamelCase komponensnév a story_text-ben legyen benne)
2. **Dataset-hézag**: a gold dataset nem gyakorolja az `analyze_changes` ágat (0 update_set példa → a GEPA reflection-iterációk ~fele üresjárat volt); 1-2 update set-es példa kell
3. Ha a dataset nem bővül: az `analyze_changes` kivétele a GEPA célpontok közül
4. A `runs/t012_style_compare` minta-script még /tmp-ben — a T010c óta `eval/compare.py` végzi; a /tmp-s script törölhető

### Backlog-kiegészítés (2026-08-09): komponens-hallucináció prototípus + tengely-átkeresztelés

**Spot-check eredmény:** a jóváhagyott `stry0010010_hotfixed.json` cikk komponensnevei 4/4 igazolhatók a story-ból (`JiraIntegrationUtils`, `aldi.atlassian.net`, `Escalated`, `ServiceNow`) — a hotfixelt cikk tiszta.

**A vakfolt pontosítása:** a hallucináció-tengely NEM hamis, hanem szűk — a spec 004-es `kb_reference_accuracy` (KB-szám validáció) hiteles, de a JSON-ben `hallucination` néven többet ígér, mint amit mér. Javaslat: tengely átkeresztelése vagy scope-komment, hogy az olvasó ne értse "nincs hallucináció"-ként.

**A spec 011-es `_find_hallucinated_components` prototípusa** (a spot-checkből, ~15 sor):
```python
candidates  = re.findall(r"'([A-Z][A-Za-z0-9 _.:/-]{2,50})'", html)        # idézett nevek
candidates += re.findall(r"\b([a-z]+[a-z0-9]*(?:\.[a-z0-9_]+)+)\b", html) # dotted azonosítók
candidates += re.findall(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", html)     # CamelCase
hallucinated = [c for c in candidates
                if c not in story_text and c not in WHITELIST]  # általános szavak kiszűrve
```
Whitelist az `story_text` + `related_articles_context` + általános termékek ("Business Rule", "Script Include", "Incident"). A rich_metric-be a `_find_hallucinated_kb_references` MELLÉ kerülne; addig is gate-ként futhat éles validációknál (T013-minta).

## 31. Éles end-to-end validáció ServiceNow-ból (2026-08-09)

### Incidens: HTTP 0 a ServiceNow gombnál
- A "Create KB Article" gomb **HTTP 0**-val elhasalt — kiderült: **a FastAPI szerver nem futott** a VPS-en (valószínűleg a 08-07-i daemon-leállásokkal ment el; a server.log-ban csak port-scannerek voltak).
- Restart a dokumentált paranccsal (`nohup ../.venv/bin/uvicorn snow_kb.server:app --host 0.0.0.0 --port 8000`), health 200 lokálisan ÉS külső IPv4-en (91.99.175.157).
- **Megjegyzés:** `--host 0.0.0.0` csak IPv4-re bindol — a gép IPv6-címe felé a szerver nem válaszol. Ha a UI Action hostname-t használ, AAAA-rekord esetén HTTP 0 jöhet újra.
- **TODO (nyitott):** a szerver nincs felügyelve — systemd unit (`Restart=always`) vagy docker-compose `restart: unless-stopped` kell, különben minden újraindításnál kézi restart.

### Éles validáció eredménye (STRY0010013 → KB c8c05f4a, update-ág, mod_count 5)
- A gomb sikeresen lefutott (POST /generate-kb 200), a júl. 27-i cikk frissült az optimized+hotfixelt programmal.
- Összevetés a júliusi verzióval: hosszabb (8.5k vs 7.6k), 14 bekezdés + 43 bullet (régen: 0 bekezdés + 69 bullet "listafal") — a spec 010 stílus-cél élesben is látszik.
- Komponens-hallucináció ellenőrzés (a spot-check prototípussal): 4/4 név igazolt a story-ból, 0 kitalált.
- Emberi review: **"tökéletes"** ✅ — az éles pipeline ezzel teljesen validált.

### Nyitott tételek innen
1. systemd/docker restart-policy a szervernek (HTTP 0-megelőzés)
2. `artifacts/` verziózás eldöntése (a jóváhagyott program.json + hotfix csak lokálisan létezik!)
3. spec 011 jelöltek: komponens-hallucináció metrika + dataset update_set-bővítés

## 32. Spec 011: Komponens-hallucináció metrika + Update Set dataset-lefedettség BEFEJEZVE (2026-08-11)

### Mi valósult meg (T001-T008, T010)

- **Metrika-vakfolt lezárva (US1):** a `rich_metric` hallucination tengelye mostantól a KB-számok MELLETT a nevesített komponensneveket is validálja (`_find_hallucinated_components` az `eval/metric.py`-ben). Jelöltek: 'idézett nevek' + CamelCase + dotted azonosítók; igazolás a story_text + related_articles_context + update_set_payloads ellen (3 lépcsős: pontos → normalizált substring → rész-humpok). A `COMPONENT_NAME_WHITELIST` a `BANNED_PHRASES` mintájára közös helyen él. FR-002: belső hiba esetén warning + semleges tengely.
- **False positive-first hangolás:** a prototípus (30. szekció) nyers verziója 8 false positive-t adott a gold dataseten (pl. 'FrameWork', 'ChTask', 'interface.solman', 'e.g', URL/email-töredékek) — a végleges detektor 8/8 gold cikken + a hotfixelt STRY0010010-es éles cikken is 0 FP (SC-002). SC-001: a fabrikált 'ALDI: CHG Scheduled' név → hallucination 0 + a feedback nevesíti.
- **Dataset-hézag lezárva (US2):** Példa 5 (STRY0010016, KB Generator pipeline) valódi, anonymizált Update Set XML-ekkel (`sys_script_include` SnowKbGenerator + `sys_ui_action` createKbArticle a STRY0010005 update setből; sys_id-k, IP, API key, userek anonimizálva). Split: 5 train / 4 val — az új példa szándékosan a TRAINSET-ben (a GEPA reflection csak abból tanul). A loader opcionális `### Update Set Payloads` blokkot parse-ol; a régi 8 példa visszafelé kompatibilis (üres payload). Figyelem: a SolMan példa story-száma ELEVE STRY0010005 volt → az új példa STRY0010016-ot kapott (ütközés!).
- **SC-003 bizonyíték:** program-hívás az új példán → az `analyze_changes` LEFUT (trace: `update_set_xml` input), a `technical_summary` bekerül a generálás story_contextjébe (`runs/t007_analyze_changes_proof.json`).
- **Új baseline-referencia (US3, 2026-08-11, `cache=False`, preflight után):** átlag **0.755**; structure 0.917 / content 0.673 / template 0.750 / hallucination **1.000** / style 0.475 → `runs/baseline.json`. A 2026-08-08/09-i számok (0.773 stb.) ELAVULTAK (a hallucination tengely scope-ja szigorodott); a régi baseline mentve: `runs/baseline_pre_spec011.json`.
- **Tesztek: 275/275 zöld** (2026-08-11).

### T009 — Mini-GEPA: NEM futott (a döntés az emberé)

Az opciók indokolva a `specs/011-component-hallucination-metric/tasks.md` T009 pontjában. Az ágens javaslata: **elhalasztás** — (1) az új metrika zaj-sávja még nem kalibrált (1 mérés); (2) 1 db update_set-es példa gyenge statisztikai alap; (3) a produkciós program.json jóváhagyott állapotban van. Indokoltá válik, ha: újabb komponens-fabrikálás jön élesben, vagy +1-2 update_set-es gold példa készül.

### Tanulságok

- A metrika-bővítés első lépése mindig a gold dataset false positive-sweepje: a "konzervatív" prototípus is 8 FP-t adott — a hump-szintű rész-igazolás + URL/email-strip + whitelist hármasa kellett a 0 FP-hoz.
- Dataset-példa story-szám ütközhet egy meglévővel (STRY0010005 duplikáció) — új példánál ellenőrizni kell a számokat.

## 32. Spec 011 implementáció + kalibráció → T009 ELHALASZTVA (2026-08-11)

### Spec 011 implementálva (dedikált autonóm agent: spec011-runner, ~35 perc!)
- T001-T004: `_find_hallucinated_components()` + whitelist + metric-integráció + tesztek — a metrika mostantól a fabrikált komponensneveket is 0-zza (a KB-szám-check érintetlen)
- T005-T007: update_set-es gold példa (STRY0010010-ből, ServiceNow-ból lekérve) → a dataset 4/4 → **5 train / 4 val**; az `analyze_changes` mostantól ténylegesen fut az eval-ekben
- T008: új baseline az új metrikával: **0.755** (referencia, 2026-08-11)
- Tesztek: 275/275 zöld (+10 új); commit `ac88f03`

### Kalibráció (calib-runner agent): a metrika-zaj felmérése
Három azonos baseline-mérés: 0.755 / 0.796 / 0.741 → összesített zaj ≈ ±0.03.
Tengely-szórások: hallucination 0.000 (STABIL — a komponens-detektálás nem villog ✅), template 0.000, structure 0.042, content 0.070, **style 0.188** (a judge-variancia a fő zajforrás ⚠️).

### T009 döntés: mini-GEPA ELHALASZTVA (emberi döntés)
Indok: a mérési zaj (±0.03 összesített, ±0.19 style) > mini-GEPA reális várható nyeresége (+0.02-0.05) → a futás kimenetele értelmezhetetlen lenne ("mérleg-analógia": ±3 kg-ot tévedő mérlegen nem mérhető 1 kg fogyás).

### Backlog (spec 012-jelölt): style judge zajcsökkentés
- 2 mintás judge-átlagolás vagy determinisztikusabb judge-hívás → a style-szórás cél: ≤ ±0.10
- VAGY valset-bővítés (4 → 8-10 példa) → kisebb standard hiba
- Utána a mini-GEPA újra felmerülhet (az analyze_changes már lefedett, a metrika már látja a komponens-hallucinációt)

### Meta-tanulság (autonóm agentek)
A spec011-runner + calib-runner lánc jól működött: preflight → implementáció → gate (pytest) → kalibráció külön agenttel → befejezés-üzenet a main-sessionnek (agent_message). A "GEPA TILOS / kód módosítása TILOS" klauzulák beváltak.

## 33. Spec 012: Style judge zajcsökkentés (multi-sample) BEFEJEZVE (2026-08-11)

### Mi valósult meg (T001-T009, dedikált runner agent)

- **Multi-sample style judge (US1):** `_style_score()` mostantól `STYLE_JUDGE_SAMPLES = 3` judge-hívást ad ki, a SIKERES minták clamp-elt pontjainak átlaga a score; a critique a mean-hez legközelebbi mintáé (a GEPA reflection reprezentatív szöveget kap). Részleges hibatűrés (FR-001): 1-2 hiba → mean(maradék) + warning, NEM 0.5; mind-hiba → a spec 010-es (0.5, "") viselkedés érintetlen. A konstans tesztekben felüldefiniálható (FR-002). +8 mock-teszt, **282/282 zöld**.
- **Judge diszkrimináció újravalidálva (SC-003):** gépies teszt-ikon **0.017** (< 0.4 ✅), KB0010015 **0.950** (> 0.7 ✅) — `runs/t005_judge_revalidation.json`.
- **Kalibráció (SC-002 TELJESÜL):** 3 azonos baseline-futás (`cache=False`, preflight: llama.cpp health + smoke OK) tengely-szórásai: hallucination 0.000, template 0.000, structure 0.042, content 0.039, **style 0.017** (a 0.188-ról — a cél ≤ 0.10 volt, a várt ~0.11-nél is jobb). Összesített zaj: 0.018. Az N=5 / temp=0 tartalék-opciókra nem volt szükség.
- **Új baseline-referencia:** `runs/baseline.json` átlag **0.751** (structure 0.875 / content 0.667 / template 0.750 / hallucination 1.000 / style 0.513). A spec 011-i számok ELAVULTAK (mentve: `runs/*_pre_spec012.json`).
- **Mini-GEPA számszerű újraértékelés (T008, a tasks.md-ben):** értelmezhetőségi küszöb = mért szórás (0.018) + marge (0.02) ≈ **0.04**; a várható nyereség (+0.02–0.05) felső vége már a küszöb felett → az elhalasztás eredeti oka megszűnt. GEPA NEM futott; **a döntés az emberé** (becsült idő ~5-7 óra a 200-call mintájára, mert a metric call 2→4 lokális hívás).

### Tanulságok
- A per-példa style szórás továbbra is 0.20-0.27, mert abban a task-generálás varianciája (temp=0.6) is benne van — az SC-002 szándékosan a tengely-átlagok szórására szól (az eredeti kalibrációval azonos módszer).
- A 3 baseline-futás N=3 judge mellett is csak ~4 perc/db volt (a becsült 15-25 helyett) — a lokális judge olcsó.

## 33. Modellcsere: Qwen3.6-35B-A3B (MoE) → Qwen3.8-27B dense (2026-08-20)

### Új szerver-config (Windows-gép)
`llama-server --device Vulkan0 -ngl 99 -m Qwen3.8-27B-UD-Q4_K_M.gguf -c 65536 --cache-type-k/v q4_0 --temp 1.0 --spec-type draft-mtp --parallel 2 --port 8080 --reasoning off`; Tailscale serve: kifelé 8033 → befelé 8080 (`tailscale serve --bg --http=8033 http://127.0.0.1:8080`). Megj.: kezdeti lassúság a hangolás alatt (dense 27B vs MoE 3.6B aktiv); végül ~88 tok/s.

### Mérések (spec 012-es zaj-mentesített metrika, 5 train/4 val, cache=False)
- **27B base program: 0.859** (structure 1.000, template 1.000, style 0.754) vs 35B base 0.751 → **+0.108**
- **27B + 35B-re GEPA-zott program: 0.768** → a GEPA-nyereség NEM transzferálódik, sőt ront (template 0.75: direction violation visszajött; hallucination 0.75)
- Judge-validáció az új modellel: gépies 0.050 / KB0010015 0.983 ✅ (jobb diszkrimináció, mint a 35B-nél)

### Döntés (emberi): 27B + ALAPprogram az élesben
- `artifacts/program.json` → `artifacts/program_35b_optimized.json` (verziózva megmaradt); a szerver/CLI fallback így a base programot tölti (pipeline._load_program)
- systemd restart megtörtént, health OK, 282/282 teszt zöld
- Config-frissítések: baseline.py + gepa_optimize.py + config.yaml modellnév; gepa num_threads 4→2 (--parallel 2)

### Backlog
1. **GEPA a 27B-hez** (később, kitalálandó): a zaj-mentesített metrikával már értelmezhető lenne; a 27B base 0.859 a kiindulás — a kérdés, hogy a GEPA hoz-e még +0.02-0.05 felettit
2. A `runs/baseline_qwen38.json` (27B base) az új referencia-pont; ha a 27B-hez GEPA készül, ez a viszonyítási alap

## 34. Éles PDI-teszt az új 27B modellel (2026-08-20)

- UI Action gomb → POST /generate-kb 200 OK → STRY0010014-hez KB cikk (`f662bcda...e3ad`), update-ág
- "Bidirectional REST Integration: ServiceNow ↔ SAP SolMan" — **17.2k karakter**, mind a 7 szekció, helyesen Inbound ÉS Outbound (bidirectional → direction handling ✅)
- Komponens-ellenőrzés (spec 011 prototípus): **8/8 név igazolt a story-ból, 0 fabrikált**
- Sebesség: a felhasználó szerint kellően gyors (draft-mtp spekuláció + Vulkan: ~88 t/s decode mérve)
- Emberi review: **elfogadva** ("minőségben és gyorsaságban kellően elegendő")
- ⇒ Az éles stack ezzel: **Qwen3.8-27B dense + alapprogram + systemd-szerver** — teljesen validált

## 35. PROJEKT-LEZÁRÁS (2026-08-20) — a projekt késznek tekinthető

### Végső állapot
- **Éles stack:** Qwen3.8-27B dense (llama.cpp, Vulkan, draft-mtp, ~88 t/s) + **alapprogram** (a 35B-re GEPA-zott program nem transzferálódott, félretéve: `artifacts/program_35b_optimized.json`) + FastAPI systemd-service (snow-kb.service, Restart=always)
- **Mért minőség (spec 012 metrika, 5 train/4 val):** összesített **0.859** (structure 1.000 / content 0.631 / template 1.000 / hallucination 1.000 / style 0.754); mérési zaj ±0.018
- **Éles validáció:** STRY0010014 → bidirectional cikk, 17.2k karakter, 8/8 komponens igazolt, emberi review elfogadva (2026-08-20)
- **Tesztek:** 282/282 zöld; minden commitolva/pusholva; `validated-2026-08-11` tag a 35B-s korszak visszaállítási pontja

### Lezárt specek
- **010** human-style articles: style tengely + judge + GEPA 200-call (0.773→0.873 best) + éles validáció (a review hallucinációt fogott → hotfix-lánc)
- **011** component-hallucination metric + update_set dataset-példa (a metrika-vakfolt javítva)
- **012** style judge zajcsökkentés multi-sample-lal (N=3): 0.188 → 0.017

### Backlog (tudatosan elhalasztva — NEM befejezetlenség)
1. **Mini-GEPA a 27B-hez** (~1-1.5 óra az új szerveren): csak akkor érdemes, ha éles cikkekben visszatérő gyengeség-minta jelenik meg. Indítócsomag: `specs/012-style-judge-noise-reduction/tasks.md` T008 + `runs/baseline_qwen38.json` referencia. Figyelem: a style judge self-eval, GEPA-val könnyű a judge ízlésére overfitelni.
2. Content-tengely 0.631: ha zavaróvá válik, előbb a metrika fact-extrakcióját érdemes nézni, nem a GEPA-t.
3. Apróságok: `docs/` scaffold-fájlok untrackedek; szerver csak IPv4-en figyel (`--host 0.0.0.0`); Windows-gép restart után a llama-server kézzel indítandó.

### Újrahasznosítható munkamódszer
A spec 010-012 implementációja az `autonomous-spec-runner` skillel történt (tmux + autonóm agent + gate-ek + completion message). A skill a repóban: `.prime/agent/skills/autonomous-spec-runner/` ÉS globálisan `~/.prime/agent/skills/`. Új spechez: spec-kit írás → review → "futtasd az autonomous-spec-runner workflow-val".

### Folytatás fél év múlva is 2 perc:
1. Olvasd ezt a szekciót + a 33-34-et (modellcsere + éles teszt)
2. Szerver: `systemctl status snow-kb.service`; Windows: llama-server parancs a 33. szekcióban
3. Mérések: `../.venv/bin/python -m eval.baseline --model local --output runs/...` (interpreter: `../.venv`, NINCS saját .venv!)

## 36. Incidens: HTML-nesting hiba generált cikkben (2026-08-25) + backlog trigger

### Mi történt
A STRY0010004-hez generált cikk (`dd9006ef...10e6`) vége vizuálisan "elcsúszott": a Testing Guide szekcióban a modell hibás HTML-t termelt (`<li><em><ul>` — lezáratlan `<em>` + felesleges beágyazott lista), amibe a Known Issues és Investigation Steps szekciók beleestek. A tag-SZÁMOK kiegyenlítettek voltak (naiv számláló nem fogja), a beágyazási SORREND volt rossz.

### Javítás és kimenet
- Kézi HTML-javítás API-n keresztül (4 scenárió lapos listára rendezve, árva zárók törölve) → `runs/kb_last_gen_fixed.html`
- Újragenerálás (update-ág): tiszta HTML, 0 nesting-hiba → a hiba **egyszeri modell-glitch** volt, nem reprodukálható
- A metrika ezt a hibaosztályt NEM fogja (a tartalom jó volt, csak a tag-struktúra csúszott)

### A verem-ellenőrző (újrahasználható, ~15 sor)
```python
stack, err = [], 0
for m in re.finditer(r"</?(ul|ol|li|em|p|h2|h3|strong)(?:\s[^>]*)?>", html):
    tok, name = m.group(0), m.group(1)
    if tok.startswith("</"):
        if stack and stack[-1] == name: stack.pop()
        else: err += 1
    else:
        stack.append(name)
# err > 0 vagy stack nem üres → nesting-hiba; H2/H3 sosem lehet <ul>/<ol>/<li>-ben
```
(Másolat: `runs/check_html_nesting.py`.)

### BACKLOG-TRIGGER (döntés: B opció)
**HA** egy generált cikken MÉGEGYSZER nesting-hiba jelenik meg (verem-ellenőrzés err>0), **AKKOR** azonnal nesting-validator a pipeline-ba (push-előtti ág, `KBArticle` validáció kiegészítése, ~20 sor + teszt). Addig is: minden gyanús cikket a fenti scripttel ellenőrizni. Egyetlen esetre nem építünk kódot, a második azonnali implementációt jelent.

## 37. Dev mód bevezetése (2026-08-25)

- **ALAP mód (új alapértelmezés): Kimi K3** (`task_model: "kimi"` a configban) — a Kimi Code előfizetés a napi task modell; a lokális gép leállása már nem blokkolja az éles generálást.
- **Dev mód: lokális Qwen3.8-27B** — ki/bekapcsolás:
  - CLI: `--dev` flag
  - env: `SNOW_KB_DEV_MODE=1` (a load_settings felülírja a task_modelt)
  - systemd-szerveren: drop-in `Environment=SNOW_KB_DEV_MODE=1` (ld. deploy/README.md)
- Érintett fájlok: `config.py` (default + env override), `config.yaml`, `cli.py` (--dev), tesztek igazítva (a régi LM-tesztek most explicit `task_model="local"`-ot állítanak a standard/pi_auth ágakhoz)
- Tesztek: 286/286 zöld (+4 új dev-mód teszt)
- Megj.: a style judge a globális LM-et követi — Dev módban lokális, alap módban Kimi (kevés hívás, nem jelentős kvóta)

## 38. __main__ dupla-import bug + Kimi vs 27B baseline-mérés (2026-08-26)

### A bug (klasszikus Python-csapda)
`python -m eval.baseline --model kimi` futtatáskor a modul `__main__`-ként fut, és a `main()`-beli `import eval.baseline as _self` egy MÁSODIK modul-objektumot hoz létre — a `configure_lm = configure_kimi_lm` csere oda került, a futó `run_baseline` a LOKÁLIS configure-t használta. A bug mindig is ott volt (a T009b óta); amíg a lokális szerver élt, láthatatlan maradt. Javítás: `sys.modules[__name__].configure_lm = configure_kimi_lm` (mindkét futtatási módban helyes).
**Visszatekintő kockázat:** a korábbi `--model kimi` CLI-mérések (pl. júliusi 0.769) a bug miatt potenciálisan lokálisak voltak — azok a számok bizonytalanok; a friss (2026-08-26) mérés az első igazolt Kimi-baseline.

### Mérés (spec 012 metrika, 5 train/4 val, cache=False)
- **Kimi K3 base: 0.869** (structure 0.923 / content 0.682 / template 1.000 / hallucination 1.000 / style 0.841)
- Lokális 27B base: 0.859 → Kimi +0.011 (zaj-sávon belüli paritàs, enyhe Kimi-előny)
- Módszertan: mindkét esetben a judge = a generáló modell (stack vs stack, nem abszolút mérés)
- A Dev-mód architektúra (alap = Kimi, dev = lokális) adatilag alátámasztva

### Diagnosztika-lecture
A "lokális modell megy Kimi helyett" tünet mögött két külön ok is volt: (1) a szerver process-cache régi configja (restart megoldotta), (2) a __main__ dupla-import bug a CLI-ben. A litellm-hívás-spy (model+api_base minden hívásnál) vezetett a megoldáshoz.
