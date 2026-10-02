# spec 016 runner-report — KONTEXTUS-VÁLOGATÁS A CIKKGENERÁLÁSHOZ

**Állapot**: 🟡 PARKOLVA a **T003 MANUÁLIS KAPUnál** — emberi döntésre vár
(baseline review + SC-001 célérték rögzítése).

**Branch**: `016-context-selection` | **Futási mód**: DEV (SNOW_KB_DEV_MODE=1,
lokális Qwen3.8-27B; Kimi-token felhasználás nélkül) | **Dátum**: 2026-10-02

## Per-phase eredmények

### Phase 1: Setup + Baseline

| Task | Állapot | Eredmény |
|---|---|---|
| T001 config | ✅ KÉSZ | `context_selection` config-blokk (enabled=false, pinnelt jev-1.13.0, hide_below=0.25, summarize_below=0.60, min_confidence=0.6, summarizer_endpoint=lokális Qwen, recording_path) + 5 új config-teszt |
| T002 baseline | ✅ KÉSZ | `artifacts/context_baseline.json`: 9 gold példa, lokális Qwen, cache=False; **8540 kontextus-token**, **1825 zaj-jelölt (21.4%)**, **rich_metric avg 0.8417**; replay-ból byte-identikus |
| T003 MANUÁLIS KAPU | 🟡 VÁRAKOZIK | gate-riport: `specs/016-context-selection/gate-T003.md`; javasolt SC-001 cél: **≥5% kontextus-token-csökkenés** |

### Phase 2: US1 – a válogató modul

| Task | Állapot | Eredmény |
|---|---|---|
| T004 tesztek | ✅ KÉSZ | `tests/test_context_selection.py` — 22 teszt, FAIL-first (collection error a modul hiányában), majd zöld |
| T005 modul | ✅ KÉSZ | `src/snow_kb/context_selection.py`: darabolás (JSON/markdown story, update set XML, related sorok) + Score-döntés (pinnelt jev-1.13.0, typesafe_sdk.Score) + Python-policy (`<` operátor, határérték a biztonságos irányba) + fail-open show + FR-004 (story_core-ra LLM-hívás sem indul) + summarize a lokális endpointon (fail-open az eredeti szövegre) + jev-formátumú JSONL recording |
| T006 bekötés | ✅ KÉSZ | `pipeline.py`: a program a VÁLOGATOTT kontextust kapja; a 014/015 gate és a strip-guardrailek az EREDETIT; enabled=False → bit-azonos viselkedés; program.py/program.json érintetlen |

### Phase 3–5: előkészítve, a T003 kapu után fut

- T007/T008/T010/T011/T013 eval-scriptek megírva (`eval/context_measure.py`,
  `eval/context_recall_gate.py`, `eval/context_labeled.py`,
  `eval/context_calibration_016.py`, `eval/context_sc_gates_016.py`) —
  az élő mérések a kapu döntése után indulnak.

## Baseline kulcsszámok (a T003 kapu tárgya)

- Mérhető zaj: **21.4%** (1825/8540 token) — a spec NEM áll meg.
- Nyilvánvaló hide-jelöltek (number/state/assigned_to/assignment_group): 333 token (3.9%).
- Summarize-jelöltek (work_notes/comments): ~1492 token.
- Token-módszer: llama.cpp `/tokenize` (a Qwen valódi tokenizere) — az after-mérés ugyanez.

## SC-gate-ek

Még nem futottak (a T013 a záráskor; az SC-001 célérték a T003 kapun rögzül).

## Pytest-suite

- Kiindulás: **387 passed** ✅
- T001/T004–T006 után: **414 passed** ✅ (`env -u SNOW_KB_DEV_MODE` alatt)

## Commit-hash-ek

- `ee0d6e4` T001: context_selection config-blokk + config-tesztek
- `8cbec87` T004+T005+T006: context_selection modul + pipeline-bekötés + 22 teszt (414 zöld)
- `3502be3` T002: baseline-mérés + eval-scriptek
- `2485fc8` T003 MANUÁLIS KAPU: gate-riport — runner VÁR

## Elakadás / várakozás

A runner a T003 MANUÁLIS KAPUnál vár: az ember review-ja kell a baseline-hoz és
az SC-001 célérték rögzítéséhez (javaslat: 5%). A kapu-üzenet elküldve a
`snow-main` sessionnek. A döntésig a runner NEM folytatja a T007-et.
