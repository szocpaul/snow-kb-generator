# spec 014 runner-report — Komponensnév-hitelesítés az instance ellen + production push-gate

**Állapot: MEGÁLLVA a T005 MANUÁLIS KAPUnál** — emberi review-ra vár.
Dátum: 2026-09-30 | Branch: `014-component-instance-verification` | Futtatás: DEV mód (SNOW_KB_DEV_MODE=1, lokális Qwen3.8-27B)

## Preflight (mind ZÖLD)

| # | Ellenőrzés | Eredmény |
|---|---|---|
| 0 | branch + spec-fájlok | ✅ `014-component-instance-verification`, spec/plan/tasks/handoff megvan |
| 0b | SNOW_KB_DEV_MODE=1 → task_model == "local" | ✅ (api_base: desktop-c5ikame-1.ts.net:8033) |
| 0c | lokális LLM minimal completion | ✅ Qwen3.8-27B válaszol |
| 1 | TYPESAFE_API_KEY + minimal system_one (jev-1.13.0) | ✅ ChoiceAnswer(confidence=0.92) |
| 2 | typesafe-sdk 0.7.2 + dspy 3.4.0 telepítve | ✅ (a pyproject része, nem telepítettem újra) |
| 3 | ServiceNow minimal table-API | ✅ `sys_db_object` lekérdezés OK (dev432044) |
| 4 | pytest -q zöld (dev mód NÉLKÜL) | ✅ 309 passed |

## Phase 1 — Setup

- **T001** ✅ `verification_gate` config-blokk (`config.yaml` + `VerificationGateConfig`):
  enabled=false (default), behavior=flag|strip|block (default flag), pinnelt model
  (jev-1.13.0, lebegő alias ConfigError), confidence_threshold=0.7 (0..1 validáció),
  spotcheck_cache_path, recording_path. 5 új config-teszt zöld.
- **T002** ✅ `.env.example`: TYPESAFE_API_KEY benne van (013 óta), új env NEM kell.
  `deploy/README.md`: a spot-check által olvasott metaadat-táblák (sys_db_object,
  sys_dictionary, sys_script, sys_script_include) + olvasási jog megjegyzés.

## Phase 2 — Baseline (US1 előfeltétel)

- **T003** ✅ `eval/component_inventory.py`: a 011-es kinyerési minta replikája
  (változatlan regexek), 12 példa (9 gold + 3 frissen generált lokális Qwennel),
  összesen 49 jelölt → `artifacts/component_inventory.json`.
- **T004** ✅ `eval/spotcheck_baseline.py`: Update Set-whitelist (beágyazott
  payloadok) + élő per-név spot-check (sys_db_object/sys_dictionary/sys_script/
  sys_script_include) → `artifacts/component_baseline_report.json/.md`.

  **Összesítés**: exists=6, in_update_set=5, whitelisted_generic=12,
  **not_found=26**, error=0.

  **Vakfolt-elemzés** (`artifacts/component_baseline_blindspot.json`):
  mind a 26 not_found név a forrás-story-ban IS szerepel → a 011-es story-alapú
  tengely egyiket sem fogná — a spec vakfoltja valós. A not_found lista
  három osztályra bomlik (részletek a report .md-ben):
  1. külső (SolMan/SAP) objektumok — spec szerint out of scope, a gate-nek
     kezelnie kell (false-positive kockázat!);
  2. workflow-állapot/UI-szöveg idézőjelben — kinyerési false positive;
  3. valósnak tűnő SNOW-komponensnevek (pl. `JiraInboundUtils`,
     `ALDIS4ProjectInterface`) — **a tényleges probléma-mag**, és a 3 frissen
     generált cikkből 2-ben is megjelent → a hallucináció MA reprodukálható.

- **T005** ⏸ **MANUÁLIS KAPU — NEM pipálva.** Review-tárgy: a baseline-leltár
  (artifacts/component_baseline_report.md). Kérdés az emberhez:
  (a) a probléma nagysága igazolt-e a folytatáshoz (javaslat: IGEN — a 3-as
  osztály ma is reprodukálható a friss generáláson);
  (b) a külső-rendszer-objektumok (SolMan/SAP) kezelése: a spec out of scope-nak
  tartja a *validálásukat*, de a gate false positive-jait csökkentendő érdemes-e
  a jelölt-kinyerést SNOW-specifikusabbá tenni (a T007 implementációs döntése,
  javaslat: igen, típus-tipp + külső-rendszer-heurisztika).

## Phase 3-6

Még nem futottak — a T005 kapu döntésére várnak.

## SC-gate-ek (T013)

Még nem futottak.

## Commitok

| Hash | Tartalom |
|---|---|
| df709b8 | spec 014 fájlok (kiindulás) |
| c8da6e0 | T001+T002: verification_gate config-blokk + deploy-jogosultságok |
| 9919aaa | T003+T004: baseline leltár + instance spot-check + vakfolt-elemzés |

## Tilalom-ellenőrzés

- GEPA: nem futott ✅
- T005/T014 MANUÁLIS KAPU: nincs pipálva ✅
- program.py / program.json / 004-011 story-alapú ellenőrzés: érintetlen ✅
- verification_gate.enabled: false maradt ✅
- Kimi-token a task-modellre: 0 (minden LLM-futtatás DEV módú lokális Qwen volt) ✅
