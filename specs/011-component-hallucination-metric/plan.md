# Implementation Plan: Komponens-hallucináció detektálás + Update Set dataset-lefedettség

**Branch**: `011-component-hallucination-metric` | **Date**: 2026-08-11 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.3.0, lokális Qwen3.6-35B-A3B (llama.cpp, `-np 4`) + Kimi K3 reflection
- **Interpreter: `../.venv`** (szülőkönyvtár közös venv-je — ld. spec 010 plan)
- Érintett fájlok: `eval/metric.py` (US1), `eval/dataset.py` + `data/examples/gold_dataset.md` (US2), `eval/baseline.py` futtatás (US3), `tests/`
- Kiinduló prototípus: Agent.md 30. szekció (a 2026-08-09-i spot-check kódja, 4/4 igazolt névvel validálva a jóváhagyott cikken)
- Előzmény-döntések, amiket NEM változtatunk: hallucination tengely súlya 0.15; a KB-szám-detektálás (spec 004) érintetlen; cache-higiénia (minden mérés `cache=False`)

## Architecture

```
generált cikk (HTML)
      │
      ▼
_find_hallucinated_components()          ← ÚJ (US1)
  1. jelölt-kinyerés: 'idézett nevek' + CamelCase + dotted azonosítók
  2. szűrés whitelisttel (általános terminusok, terméknevek)
  3. minden jelölt: benne van-e a story_text + related_articles_context-ben?
      │
      ├── van fabrikált név → hallucination = 0, feedback nevesíti
      └── minden rendben → a spec 004-es KB-szám-check fut tovább (érintetlen)

gold_dataset.md + update_set_payloads     ← ÚJ példa (US2)
      │
      ▼
program.forward() → if update_set_payloads: analyze_changes LEFUT
      │
      ▼
GEPA reflection már látja az analyze_changes trace-eket
```

## Key Decisions

1. **A meglévő hallucination tengely bővül**, nem új tengely jön — a súlyok (0.25/0.25/0.15/0.15/0.20) és a metrika-szerkezet változatlan, így a spec 010-es eredményekkel való összevethetőség korlátozottan megmarad (a tengely-szemantika szigorodik: KB-számok + komponensnevek).
2. **False positive-first megközelítés**: a detektálást úgy hangoljuk, hogy a gold cikkek hibátlanul átmenjenek (SC-002) — inkább engedjen át határesetet, mint hogy zajt adjon a GEPA-nak. A whitelist a fő eszköz.
3. **A jelölt-kinyerés konzervatív**: csak erős jelzésű jelöltek (idézett nevek, CamelCase, dotted identifier); sima angol szavak nem jelöltek.
4. **Az update_set-példa egyelőre 1 db** (nem 2) — a cél a lefedettség bizonyítása és a GEPA-üresjáratok megszüntetése, nem a statisztikai erő. A split 4 train / 4 val → 5 train / 4 val vagy 4/5 — a tasks.md dönti el a példa elkészültekor.
5. **A baseline újramérés része a specnek** (nem opcionális) — a metrika-változás elavulttá teszi a 2026-08-08/09-i számokat; az új referencia kell minden jövőbeli összevetéshez.
6. **Mini-GEPA csak külön döntéssel** — a spec a döntési pontot dokumentálja, nem automatizálja.

## Phases

1. **Phase 1 (US1)**: `_find_hallucinated_components()` + whitelist + metric-integráció + tesztek (fabrikált név → 0; gold HTML-ek → 0 false positive).
2. **Phase 2 (US2)**: update_set-es gold példa (valódi XML-ek, anonymizálva) + dataset-loader igazítás + analyze_changes futás-bizonyíték.
3. **Phase 3 (US3)**: baseline újramérés + dokumentáció + mini-GEPA döntés.
