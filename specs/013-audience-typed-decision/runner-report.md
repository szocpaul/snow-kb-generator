# Runner-report: spec 013-audience-typed-decision (T001–T014, MANUÁLIS KAPUk nélkül)

**Runner**: spec013-runner-k3 | **Dátum**: 2026-09-29 | **Branch**: `013-audience-typed-decision`
**Futtatási mód**: SNOW_KB_DEV_MODE=1 (lokális Qwen3.8-27B a task-modell; Kimi-token felhasználás: 0)

## Preflight (mind ZÖLD)
- 0: branch + 4 spec-fájl megvolt; 0b: `task_model == "local"` dev-módban; 0c: lokális llama.cpp smoke OK
- 1: TYPESAFE_API_KEY + minimális system_one hívás OK (jev-1.13.0)
- 2: typesafe-sdk 0.7.2 + dspy 3.4.0 a projekt-venvben (`/home/ubuntu/dspy_projects/.venv`)
- 3: gold dataset 9 futtatható story-inputtal; 4: pytest kiinduló állapot 287/287 zöld
- Megj.: `pytest -q` SNOW_KB_DEV_MODE=1-gyel 1 környezetszennyezéses tesztet buktat
  (`test_default_task_model_is_kimi`) — a suite-et env nélkül kell futtatni, a dev-mód az
  LLM-es futtatásokhoz kell. Emellett pre-existing izolációs hiba: a `tests/test_pipeline.py`
  önmagában futtatva 9 tesztet buktat (teljes suite-ben zöld) — a spec 013 előtt is így volt.

## Per-phase eredmények

| Phase | Task | Eredmény |
|---|---|---|
| Setup | T001, T002 | ✅ typesafe-sdk + dspy[typesafe] dep (pin <3.5), `.env.example` + systemd-placeholder, `audience_decision.*` config + 4 config-teszt |
| Baseline | T003 | ✅ 9 gold példa, generatív út lokális Qwennel: **9/9 developer** → `artifacts/audience_baseline.json` |
| Baseline | T004 | ✅ gold címkék evidenciával → `data/examples/gold_audience_labels.json` (6 developer, 3 helpdesk) |
| US1 | T006-T008 | ✅ 12 új teszt (fail-first → zöld), `src/snow_kb/audience.py`, pipeline-bekötés wrapperrel |
| US2 | T009, T010 | ✅ threshold-tesztek (pontos határ → fallback), work_notes-jelzés a client írási útjában |
| Mérés | T012 | ✅ élő felvétel + replay + ReAnchor + SC-gate-ek (lásd lent) |
| Zárás | T014 | ✅ 309/309 pytest zöld, Agent.md §41, backlog TASK-1, commit+push |

## SC-gate kimenetelek (`python -m eval.audience_sc_gates` → exit 1)

- **SC-001 ZÖLD**: baseline 6/9 vs új 6/9 — az új döntés nem rosszabb (per-példa JSON: `artifacts/audience_calibration_report.json`)
- **SC-002 PIROS** (confirmatory 0.7-es kapu): selective_risk=0.200 (>0.15) | coverage=0.833 (≥0.7 ✅) | ECE=0.163 (>0.10)
- **SC-003 ZÖLD**: fail-open tesztek (SDK-hiba, séma-eltérés, resolve-szintű)
- **SC-004 ZÖLD**: kétszeri replay byte-identikus report (4491 byte)

## A PIROS SC-002 anatómiája (T013 emberi review-hoz)

- A Jev mind a 9 gold példára `developer`-t adott; a címkézett 3 helpdesk-esetet (STRY0010003 LDAP, STRY0010004 SAP IDOC, STRY0010005 SolMan sync) elhibázta.
- A címkék evidenciája: mindhárom cikk "Investigation Steps" szekciója explicit troubleshooting-guide ("When to use this guide", "Escalate to infrastructure team") — support-olvasóhoz szól.
- Confidence-szignál működik: a 3 hiba közül 2 alacsony confidence (0.26, 0.60 → a 0.7-es kapu abstain/fallback); 1 magabiztosan rossz (0.95).
- **EXPLORATÍV (NEM confirmatory)**: threshold-sweep 0.8-nál risk=0.111 / coverage=0.75; ReAnchor fitted helpdesk-weight=15.8 (train accuracy 0.667→0.917, fold-check átment). Ezek NEM confirmatory eredmények — a config `confidence_threshold` ezért **0.7-en maradt**; módosítása T013 döntés.

## Döntési jegyzetek

1. Küszöb-operátor: spec Edge Case `<` (nem `<=`) + T009 "pontosan a küszöbön → fallback" — implementáció: `confidence < threshold + 1e-9` (audience.py docstring dokumentálja).
2. A baseline dev-módban készült (lokális Qwen) → az SC-001 "generatív-út-lokális vs Jev" összehasonlítás, NEM Kimi vs Jev.
3. A production döntéshívás közvetlen SDK (`src/snow_kb/audience.py`); a ReAnchor-wrapper (`eval/audience_reanchor.py`) csak mérés.
4. program.py / program.json / eval-metrika érintetlen (a wrapper a pipeline rétegben, deepcopy-n).

## Commit-hash-ek (branch: 013-audience-typed-decision, pusholva)
- `2b89ce4` T001+T002: függőségek + audience_decision config-blokk
- `7183b68` T003+T004: baseline (9/9 developer, lokális Qwen) + gold címkék
- `fede169` T006-T010: audience.py + pipeline-bekötés + work_notes-jelzés
- `07ce995` T012+T014: mérés, SC-gate-ek, Agent.md §41, runner-report

## Nyitott MANUÁLIS KAPUk (NEM pipálva)
- **T005**: baseline + címkék review-ja (`artifacts/audience_baseline.json`, `data/examples/gold_audience_labels.json`)
- **T011**: fail-open + developer-default tradeoff jóváhagyása production-futás előtt
- **T013**: SC-kapuk review-ja; küszöb-módosítás esetén indoklás az Agent.md-be

## Verifikációs-réteg spec újraindítási feltétele
**MÉG NEM TELJESÜL**: a spec 013 nincs productionben stabil állapotban (T011 nyitott), és a küszöb-hangolás emberi döntésre vár (SC-002 PIROS). Backlog: TASK-1.
