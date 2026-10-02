# Tasks: Kontextus-válogatás a cikkgeneráláshoz

**Input**: Design documents from `/specs/016-context-selection/`
**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: párhuzamosan futtatható (más fájl, nincs függőség)
- **[USn]**: melyik user story-hoz tartozik
- **MANUÁLIS KAPU**: emberi döntés — a runner/agent NEM pipálhatja

## Phase 1: Setup + Baseline (playbook: baseline-előbb)

- [x] T001 [P] Config-bővítés `config.yaml`-ban: `context_selection.enabled` (kezdő: false), `context_selection.model` (pinnelt), `context_selection.hide_below` / `summarize_below` küszöbök, `context_selection.summarizer_endpoint` (lokális Qwen api_base, KD3), `context_selection.recording_path` — + teszt a config-parsolásra
- [ ] T002 [US2] Baseline-mérés: a gold példák kontextusának darabolása (story-szekciók / update set rekordok / kapcsolódó cikkek) + per-darab token-leltár; rich_metric baseline újramérve `cache=False`-szal → `artifacts/context_baseline.json` (fájlba, nem chatbe). **Részletszabályok**: (a) a baseline a dev-módú lokális Qwennel készül (az after-mérés is ezzel fut — az összevetés azonos modellen kötelező); (b) a token-számlálás a Qwen-tokenizerrel, vagy ha az nem érhető el, dokumentált becslővel (pl. tiktoken) — a használt módszer a riportban jelölve, és az after-mérésnek UGYANAZZAL kell dolgoznia
- [ ] T003 [US2] **MANUÁLIS KAPU**: a baseline + zaj-leltár review-ja; az SC-001 token-célérték EZ ITT rögzül (a plan.md KD6 szerint, plan-frissítéssel); ha nincs mérhető zaj → a spec megáll (014-es minta) — a runner NEM pipálhatja

## Phase 2: US1 – A válogató modul (teszt-előbb)

- [ ] T004 [US1] Teszt: `tests/test_context_selection.py` — nyilvánvaló zaj → hide/summarize; releváns darab → show; alacsony confidence → show (recall-védelem, `<` operátor); SDK-hiba → minden darab show (fail-open); story-főtörzs sosem hide (FR-004); recording-bejegyzés séma. FAIL implementáció előtt
- [ ] T005 [US1] `src/snow_kb/context_selection.py` — darabolás + Score-döntés (pinnelt modell, `dspy.experimental.Score` eval-only minta vagy közvetlen SDK a 013/014 mintára) + Python-policy (hide/summarize/show a küszökből) + summarize a lokális Qwen-endpointon (fail-open: show) + JSONL recording
- [ ] T006 [US1] Bekötés a `pipeline.py`-ba: a GenerateKb a válogatott kontextust kapja (config-flaggel kikapcsolható, FR-006); program.py/program.json érintetlen — T005 után

## Phase 3: US2 – Hatásmérés

- [ ] T007 [US2] Mérés a gold példákon: válogatott futás vs baseline — per-példa és összesített token-delta + rich_metric-delta → `artifacts/context_selection_report.json`; a minőség nem romolhat a zaj-sávon túl (SC-002); replay-módban kétszeri futás byte-identikus (SC-005)
- [ ] T008 [US2] Recall-gate (SC-003): exit-code-os teszt — a válogatott prompt tartalmazza a gold cikkek által hivatkozott valós komponensneveket (0/9 kiesés)
- [ ] T009 [US2] **MANUÁLIS KAPU**: a hatásriport review-ja — ha a minőség romlott vagy a recall kiesett, a spec NEM megy tovább production-felé — a runner NEM pipálhatja

## Phase 4: US3 – Kalibráció

- [ ] T010 [US3] Címkézett kontextus-minta (min. 20 darab: releváns / zaj / határeset — a 015-ös fixture mintára, gépi + kézi címkézés), címkék commitolva
- [ ] T011 [US3] ReAnchor-kalibráció a hide-küszöbre, aszimmetrikus metrikával (kiinduló 5:1, KD4) + érzékenység-analízis + riport; a „küszöb marad" ág is fájlba írt eredmény; a safety floor (fail-open=show) NEM kalibrálható
- [ ] T012 [US3] **MANUÁLIS KAPU**: a kalibrációs riport review-ja; küszöb-módosítás jóváhagyása + indoklás az Agent.md-be — a runner NEM pipálhatja

## Phase 5: Zárás

- [ ] T013 SC-gate-ek (SC-001..SC-006) exit-code-dal, `cache=False`/replay-mód; teljes pytest-suite zöld (387 + új); Agent.md naplóbejegyzés; backlog: TASK-3 lezárása; commit + push

## Dependencies

- T004 (teszt) ELŐBB, mint T005 — teszt-előbb sorrend
- T005 blokkolja T006-ot; T007 csak T002 (baseline) és T006 után
- T011 csak T010 után; T012 (kapu) blokkolja a config-módosítást
- MANUÁLIS KAPUk (T003, T009, T012) embert igényelnek

## Validation Checklist

- [ ] Minden FR-hez van task (FR-001→T005, FR-002→T004/T005, FR-003→T005, FR-004→T004/T005, FR-005→T002/T007, FR-006→T001/T006)
- [ ] Minden SC-hez van gate (SC-001→T003/T013, SC-002→T007, SC-003→T008, SC-004→T004, SC-005→T007, SC-006→T011/T012)
- [ ] A tesztek az implementáció előtt állnak
- [ ] Minden task konkrét fájlt nevez
