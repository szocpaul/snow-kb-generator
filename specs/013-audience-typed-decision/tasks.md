# Tasks: Audience-döntés kalibrált bizonyossággal

**Input**: Design documents from `/specs/013-audience-typed-decision/`
**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: párhuzamosan futtatható (más fájl, nincs függőség)
- **[USn]**: melyik user story-hoz tartozik
- **MANUÁLIS KAPU**: emberi döntés — a runner/agent NEM pipálhatja

## Phase 1: Setup

- [ ] T001 [P] `typesafe-sdk` függőség felvétele a `pyproject.toml`-ba és `requirements.txt`-be (a csomag a nyilvános PyPI-n van, extra index NEM kell) + `dspy[typesafe]` extra a `ReAnchor` optimizerhez (kalibráció, ld. T012); `TYPESAFE_API_KEY` a `.env.example`-ba és a systemd unit `Environment=` sorába (deploy/ alatt)
- [ ] T002 [P] Config-bővítés `config.yaml`-ban: `audience_decision.enabled`, `audience_decision.model` (pinnelt verzió), `audience_decision.confidence_threshold` (kezdő: 0.7), `audience_decision.recording_path` — + teszt a config-parsolásra

## Phase 2: Baseline (US1 előfeltétel — playbook: baseline-előbb)

- [ ] T003 [US1] Baseline-rögzítés: a jelenlegi (generatív) modell audience-döntései a 9 gold példán, per-példa JSON a `data/` vagy `artifacts/` alá — változatlan kóddal, rögzített körülményekkel
- [ ] T004 [US1] Gold audience-címkék ellenőrzése: a 9 gold cikk stílusából levezethető-e a helyes audience; ha nem, kézi címkézés és a címkék commitolása a dataset mellé
- [ ] T005 [US1] **MANUÁLIS KAPU**: a baseline-eredmény és a címkék review-ja — a runner NEM pipálhatja

## Phase 3: US1 – Döntés confidence-szel (teszt-előbb)

- [ ] T006 [US1] Teszt: `tests/test_audience_decision.py` — mock story egyértelmű developer-esetre (magas confidence) és határesetre (alacsonyabb), mockolt SDK-válasszal; fail-open teszt szimulált SDK-kivétellel. A teszteknek FAIL-elniük kell implementáció előtt
- [ ] T007 [US1] `src/snow_kb/audience.py` — `decide_audience(story_text) -> dict` (choice, probabilities, confidence); TypeSafe Choice-hívás a három opcióval; JSONL recording (request hash, response, latency, modellazonosító — a jev-dspy-lab formátum mintájára); hiba/timeout → fail-open a meglévő generatív útra, warning-log
- [ ] T008 [US1] Bekötés a `pipeline.py`-ba: az audience a `decide_audience`-ből jön (config-flaggel kikapcsolható), a `change_summary`/`key_steps` változatlanul a DSPy-programból — T006 és T007 után

## Phase 4: US2 – Alacsony confidence kezelése (teszt-előbb)

- [ ] T009 [US2] Teszt: alacsony confidence → audience="developer" + work_notes-jelzés a mért értékkel; küszöb felett → nincs jelzés; pontosan a küszöbön → fallback (`<`, nem `<=`)
- [ ] T010 [US2] Threshold-logika a `src/snow_kb/audience.py`-ban + work_notes-jelzés a `servicenow_client.py` írási útjában — T007 után
- [ ] T011 [US2] **MANUÁLIS KAPU**: a fail-open + developer-default tradeoff jóváhagyása production-futás előtt (plan.md Key Decisions 4 és 6) — a runner NEM pipálhatja

## Phase 5: Mérés, kalibráció, zárás

- [ ] T012 [US1] Kalibrációs mérés: élő felvétel a gold + mock mintán pinnelt modellel, offline replay. **Elsődleges kalibrációs eszköz a `ReAnchor` optimizer** (`dspy.experimental`, a `dspy[typesafe]` extrából): mivel a ReAnchor `dspy.Predict` modult optimalizál (közvetlen SDK-hívást nem), a méréshez egy **csak-evaluációs DSPy-wrapper** készül, ami tükrözi a T007-es döntési hívást (ugyanaz a három opció + `desc`-kérdés, TypeSafe LM-mel, pinnelt verzió); a ReAnchor ezen hangolja a `threshold`-ot LLM-hívás nélkül (egy lefuttatás + cache-elt valószínűségek). A kijött küszöb a `config.yaml` `audience_decision.confidence_threshold`-jába kerül, amit a T007/T010 közvetlen SDK-út olvas — a production hívás NEM válik DSPy-modullá. A kaput a jev-dspy-lab metrikái adják (selective risk, coverage, ECE a kalibrált küszöbbel) → SC-001/SC-002 gate exit-code-dal; SC-003 a T006 fail-open teszttel; SC-004 byte-identikus kétszeri replay — `cache=False` / replay-mód, a mérés ténylegesen fusson
- [ ] T013 **MANUÁLIS KAPU**: SC-kapuk eredményének review-ja; ha a küszöb módosul, az indoklás az Agent.md-be — a runner NEM pipálhatja
- [ ] T014 Zárás: teljes pytest-suite (286 + új tesztek) zöld, naplóbejegyzés az Agent.md-be (tények, döntések, tanulságok), commit + push, backlog-frissítés (a verifikációs-réteg spec újraindítási feltételének állapota)

## Dependencies

- T006/T009 (tesztek) ELŐBB, mint T007/T010 (implementáció) — teszt-előbb sorrend
- T007 blokkolja T008-at és T010-et
- T012 csak T003 (baseline) és T008 után
- MANUÁLIS KAPUk (T005, T011, T013) embert igényelnek

## Validation Checklist

- [ ] Minden FR-hez van task (FR-001→T006/T007, FR-002→T002, FR-003→T007, FR-004→T008)
- [ ] Minden SC-hez van gate (SC-001/SC-002→T012, SC-003→T006, SC-004→T012)
- [ ] A tesztek az implementáció előtt állnak
- [ ] Minden task konkrét fájlt nevez
