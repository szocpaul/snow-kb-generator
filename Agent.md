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
