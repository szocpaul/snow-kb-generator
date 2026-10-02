# spec 016 runner-report — KONTEXTUS-VÁLOGATÁS A CIKKGENERÁLÁSHOZ

**Állapot**: 🟡 PARKOLVA a **T009 MANUÁLIS KAPUnál** — emberi döntésre vár
(a hatásriport review-ja; folytatás a T011 kalibrációval vagy megállítás).

**Branch**: `016-context-selection` | **Futási mód**: DEV (SNOW_KB_DEV_MODE=1,
lokális Qwen3.8-27B; Kimi-token felhasználás nélkül) | **Dátum**: 2026-10-02

## Per-phase eredmények

### Phase 1: Setup + Baseline

| Task | Állapot | Eredmény |
|---|---|---|
| T001 config | ✅ KÉSZ | `context_selection` config-blokk (enabled=false, pinnelt jev-1.13.0, hide_below=0.25, summarize_below=0.60, min_confidence=0.6, summarizer_endpoint=lokális Qwen, recording_path) + 5 új config-teszt |
| T002 baseline | ✅ KÉSZ | `artifacts/context_baseline.json`: 9 gold példa, lokális Qwen, cache=False; **8540 kontextus-token**, **1825 zaj-jelölt (21.4%)**, **rich_metric avg 0.8417**; replay-ból byte-identikus |
| T003 MANUÁLIS KAPU | ✅ JÓVÁHAGYVA (ember, 2026-10-02) | **SC-001 = ≥5% a TELJES PROMPTON** (LM usage prompt_tokens), SC-002 elsődleges; rögzítve: plan.md KD6 + `artifacts/context_sc001_target.json` |

### Phase 2: US1 – a válogató modul

| Task | Állapot | Eredmény |
|---|---|---|
| T004 tesztek | ✅ KÉSZ | `tests/test_context_selection.py` — 22 teszt, FAIL-first (collection error a modul hiányában), majd zöld |
| T005 modul | ✅ KÉSZ | `src/snow_kb/context_selection.py`: darabolás (JSON/markdown story, update set XML, related sorok) + Score-döntés (pinnelt jev-1.13.0, typesafe_sdk.Score) + Python-policy (`<` operátor, határérték a biztonságos irányba) + fail-open show + FR-004 (story_core-ra LLM-hívás sem indul) + summarize a lokális endpointon (fail-open az eredeti szövegre) + jev-formátumú JSONL recording |
| T006 bekötés | ✅ KÉSZ | `pipeline.py`: a program a VÁLOGATOTT kontextust kapja; a 014/015 gate és a strip-guardrailek az EREDETIT; enabled=False → bit-azonos viselkedés; program.py/program.json érintetlen |

### Phase 3: US2 – Hatásmérés

| Task | Állapot | Eredmény |
|---|---|---|
| T007 mérés | ✅ KÉSZ | **INERT válogatás** (0 hide / 0 summarize / 92 show): teljes-prompt csökkenés **0.45%** (SC-001 PIROS a jelenlegi küszöbökön); minőség **nem romlott** (0.8417 → 0.8511, CI95 [−0.029, +0.038], SC-002 zöld); riport byte-identikus (SC-005 mechanika zöld); kontextus-token +1.4% (JSON újraépítési többlet) |
| T008 recall-gate | ✅ KÉSZ | **0/9 kiesés**, exit-code-os (SC-003 zöld) |
| T009 MANUÁLIS KAPU | 🟡 VÁRAKOZIK | gate-riport: `specs/016-context-selection/gate-T009.md`; a Score-modell az admin-metát is magasan pontozza; a ténylegesen alacsony relevanciájú darabokon a confidence is a padlón (fail-open show) — a T011 sweep korlátai előre jelzve |

### Phase 4: US3 – Kalibráció

| Task | Állapot | Eredmény |
|---|---|---|
| T010 címkézett minta | ✅ KÉSZ | **56 darab** (39 noise / 14 borderline / 3 relevant), per-darab indokolt review; `data/examples/context_labeled_016.json` commitolva |
| T011 kalibráció | ⏸ a T009 kapu után | script kész (`eval/context_calibration_016.py`: capture + ReAnchor + replay-sweep, aszimmetrikus 5:1, érzékenység 3:1/10:1) |
| T012 MANUÁLIS KAPU | ⏸ | — |

### Phase 5: Zárás

| Task | Állapot | Eredmény |
|---|---|---|
| T013 SC-gate-ek | ⏸ | `eval/context_sc_gates_016.py` kész; az SC-001 gate a T003 döntés szerint a teljes-prompt arányt méri |

## Baseline kulcsszámok (a T003 kapu tárgya)

- Mérhető zaj: **21.4%** (1825/8540 token) — a spec NEM áll meg.
- Nyilvánvaló hide-jelöltek (number/state/assigned_to/assignment_group): 333 token (3.9%).
- Summarize-jelöltek (work_notes/comments): ~1492 token.
- Token-módszer: llama.cpp `/tokenize` (a Qwen valódi tokenizere) — az after-mérés ugyanez.

## SC-gate-ek (előzetes, a T007 mérésből)

| Gate | Állapot | Megjegyzés |
|---|---|---|
| SC-001 (költség) | 🔴 PIROS a jelenlegi küszöbökön | mért 0.45% < 5% (inert válogatás) |
| SC-002 (minőség) | 🟢 ZÖLD | CI95 [−0.029, +0.038] átfedi a 0-t |
| SC-003 (recall) | 🟢 ZÖLD | 0/9 kiesés |
| SC-004 (fail-open) | 🟢 ZÖLD | 22 teszt (a T013 futtatja exit-code-dal) |
| SC-005 (replay) | 🟢 ZÖLD | riport byte-identikus |
| SC-006 (kalibráció) | ⏸ a T011/T012 után | — |

## Pytest-suite

- Kiindulás: **387 passed** ✅
- T001/T004–T006 után: **414 passed** ✅ (`env -u SNOW_KB_DEV_MODE` alatt)

## Commit-hash-ek

- `ee0d6e4` T001: context_selection config-blokk + config-tesztek
- `8cbec87` T004+T005+T006: context_selection modul + pipeline-bekötés + 22 teszt (414 zöld)
- `3502be3` T002: baseline-mérés + eval-scriptek
- `2485fc8` T003 MANUÁLIS KAPU: gate-riport
- `da4e7ab` T003 JÓVÁHAGYVA: SC-001 = ≥5% a teljes prompton — target.json + plan KD6
- `9b6b4d1` T008+T010: recall-gate zöld + 56 darabos címkézett minta
- `0b9c90d` T007: hatásmérés — INERT válogatás, minőség zöld
- `3b4138a` T009 MANUÁLIS KAPU: gate-riport — runner VÁR

## Elakadás / várakozás

A runner a T009 MANUÁLIS KAPUnál vár: a hatásriport review-ja (folytatás a T011
kalibrációval vagy megállítás). A kapu-üzenet elküldve a `snow-main` sessionnek.
A döntésig a runner NEM folytatja a T011-et.
