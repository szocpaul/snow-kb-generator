# snow-kb-generator

> DSPy pipeline that turns completed ServiceNow **Stories** into **Knowledge Base articles** — automatically.

## Mi ez?

Amikor a fejlesztők befejeznek egy ServiceNow Story-t (`STRY...`), arról manuálisan kellene Knowledge Base (KB) cikket írni. Ez a project automatizálja: egy AI pipeline (DSPy) a Story mezőiből strukturált, célközönségnek szóló, ServiceNow-kompatibilis KB cikket generál, és visszaíratja a KB-be.

**Bemenet:** lezárt ServiceNow Story — `short_description`, `description`, `acceptance_criteria`, `work_notes`, `comments`, `state`, …
**Kimenet:** KB Article (HTML) — `title`, `summary`, `problem`, `solution` (reprodukálható lépések), `category`, `audience`.

## Technológiai verem

- **Python 3.12**
- **DSPy 3.2.x** — Signatures + Modules, GEPA optimalizáció
- **ServiceNow Table API** (`requests`) — Story lekérés + KB létrehozás (CRUD)
- **Pydantic v2** — adatmodell
- **python-dotenv + PyYAML** — konfiguráció (`.env` titkok, `config.yaml` beállítások)

## Mappa-struktúra

```
snow_kb_generator/
├── Agent.md                    # a project célja, határai, működési elvei
├── README.md                   # ez a fájl
├── .env.example                # sablon a titkokhoz
├── requirements.txt            # függőségek
├── config.yaml                 # beállítások (KB id, kategóriák, modellek)
└── src/snow_kb/
    ├── __init__.py
    ├── config.py               # .env + config.yaml betöltés
    ├── servicenow_client.py    # ServiceNow Table API kliens
    ├── schemas.py              # Pydantic adatmodellek
    ├── signatures.py           # DSPy Signatures (a pipeline lépései)
    ├── program.py              # StoryToKBArticle(dspy.Module)
    ├── pipeline.py             # orchestrátor: fetch → generate → push
    └── cli.py                  # parancssori felület
data/                           # minta / gold adatok
eval/                           # dataset + rich metric
runs/                           # baseline / optimized JSON eredmények
artifacts/                      # lementett optimalizált program
gepa_logs/                      # GEPA reflection logok
```

## Állapot

Ez a project jelenleg **tervezési fázisban** van. A `src/snow_kb/*.py` fájlok csak
**komment-formájú terveket** tartalmaznak (nincs még implementált kód). A teljes
cél és a 7 lépéses DSPy workflow leírása az [`Agent.md`](Agent.md)-ben található.

## Munkafolyamat (tervezett)

1. **Spec** → 2. **Program** → 3. **Data** → 4. **Rich metric** →
5. **Baseline** → 6. **GEPA optimalizáció** → 7. **Export & deploy**

Részletek: lásd `Agent.md` 5. szakasz.

## Használat (tervezett)

```bash
# egyszeri beállítás
cp .env.example .env   # és töltsd ki
pip install -r requirements.txt

# egy Story-ból KB cikk
python -m snow_kb STRY0012345

# dry-run: csak generál, nem ír a ServiceNow-ba
python -m snow_kb STRY0012345 --dry-run
```

## Licenc

Még nincs megadva (private project).
