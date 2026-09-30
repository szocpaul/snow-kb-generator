# Tasks: Komponensnév-hitelesítés az instance ellen + production push-gate

**Input**: Design documents from `/specs/014-component-instance-verification/`
**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: párhuzamosan futtatható (más fájl, nincs függőség)
- **[USn]**: melyik user story-hoz tartozik
- **MANUÁLIS KAPU**: emberi döntés — a runner/agent NEM pipálhatja

## Phase 1: Setup

- [x] T001 [P] Config-bővítés `config.yaml`-ban: `verification_gate.enabled` (kezdő: false), `verification_gate.behavior` (flag/strip/block, default: `flag`), `verification_gate.model` (pinnelt verzió), `verification_gate.confidence_threshold` (kezdő: 0.7), `verification_gate.spotcheck_cache_path`, `verification_gate.recording_path` — + teszt a config-parsolásra
- [x] T002 [P] `.env.example` ellenőrzés: `TYPESAFE_API_KEY` már benne van (013 óta); ha a spot-check új jogosultságot igényel a ServiceNow-nál, dokumentálni a deploy/ alatt

## Phase 2: Baseline (US1 előfeltétel — playbook: baseline-előbb)

- [ ] T002b [US1] PDI-előkészítés: a mért story-k Update Set-jeinek importja a PDI-ba (`scripts_pdi/bootstrap_pdi.py` bővítés vagy manuális import) + ellenőrzés egy mintakomponens spot-checkkel — a gold minták ügyfél-instance-ről származnak, import nélkül a spot-check 100% false positive (spec Assumptions). MEGJEGYZÉS (runner, 2026-09-30): a T002b a mérés LEZÁRULÁSA UTÁN került a specbe — a T014 kapu az SC-001-et a környezeti magyarázattal elfogadta import NÉLKÜL; a T002b a JÖVŐBELI mérések előfeltétele
- [x] T003 [US1] Baseline-leltár: a meglévő gold cikkek + egy frissen generált cikkminta komponensnév-jelöltjei kinyerve (011-minta: idézett nevek, CamelCase, dotted), per-példa JSON az `artifacts/` alá — változatlan kóddal
- [x] T004 [US1] A T003-as jelöltek ellenőrzése: update set-tartalom (ahol van) + manuális/spot-check az instance-ben → hány „nem létezik" név van MA (a probléma nagysága számszerűen, fájlba írva)
- [ ] T005 [US1] **MANUÁLIS KAPU**: a baseline-leltár review-ja — a runner NEM pipálhatja

## Phase 3: US1 – Instance-tengely a metrikában (teszt-előbb)

- [ ] T006 [US1] Teszt: metrika instance-tengely — mock spot-check válaszokkal: nem-létező név → tengely 0 + nevesítés; csak valós nevek → 1.0; lekérdezési hiba → fail-open (a tengely kihagyódik warninggal, FR-002/FR-006); a gold cikkeken 0 false positive. FAIL implementáció előtt
- [ ] T007 [US1] `src/snow_kb/verification.py` — jelölt-kinyerés (011-minta újrahasznosítva), update-set whitelist-építés (`get_update_set_changes` kimenetéből), per-név spot-check a `servicenow_client` sessionjén (cache-elve, `spotcheck_cache_path`), fail-open minden lekérdezési hibára; bekötés az `eval/metric.py`-be új tengelyként (a story-alapú tengely érintetlen)

## Phase 4: US2 – Production push-gate (teszt-előbb)

- [ ] T008 [US2] Teszt: gate a `servicenow_client._create_kb_article_live` előtt — nem-létező név → behavior szerinti viselkedés (default: work_notes-jelzés a nevekkel + confidence); valós nevek → cikk változatlan; instance elérhetetlen → fail-open, a cikk kimegy warninggal. FAIL implementáció előtt
- [ ] T009 [US2] Gate-bekötés a `pipeline.py`-ba (a `_create_kb_article_live` hívás elé): `verify_component_names` futtatása, a behavior végrehajtása (flag: work_notes-jelzés; strip/blokk csak konfiggal), JSONL recording (013-formátum) — T007 után

## Phase 5: US3 – Kalibrált réteg a homályos esetekre (teszt-előbb)

- [ ] T010 [US3] Teszt: homályos esetek — írásvariáns valós komponensre → „létezik (utalás)" magas confidence-szel; ismeretlen név → alacsony confidence / „nem létezik"; SDK-hiba → fail-open a determinisztikus útra. FAIL implementáció előtt
- [ ] T011 [US3] Kalibrált döntés a `verification.py`-ban: TypeSafe Noul per homályos jelölt (pinnelt modell), threshold-logika a 013-as mintára (`<` operátor, eps), recording + fail-open — T007 után

## Phase 6: Mérés, kalibráció, zárás

- [ ] T012 Címkézett minta építése: **≥20 példa** (valós nevek + szándékolt írásvariánsok + fabrikált nevek), a címkék commitolva a dataset mellé — a 013-as tanulság: mintaméret-minimum az SC-kapuhoz
- [ ] T013 [US3] Kalibrációs mérés: élő felvétel a címkézett mintán pinnelt modellel, offline replay; ReAnchor csak-evaluációs wrapperen (013-as T012 minta); a kijött threshold a configba; kapuk: SC-001 (gold: 0 false positive), SC-002 (selective risk ≤0.15, coverage ≥0.7 a 0.7-es kapunál), SC-003 (fail-open tesztek), SC-004 (byte-identikus kétszeri replay) — exit-code-dal, `cache=False`/replay-mód
- [ ] T014 **MANUÁLIS KAPU**: a gate default behavior (KD1: flag) és a fail-open tradeoff jóváhagyása production-futás előtt; SC-kapuk review-ja; ha a küszöb módosul, indoklás az Agent.md-be — a runner NEM pipálhatja
- [ ] T015 Zárás: teljes pytest-suite zöld, Agent.md naplóbejegyzés (tények, döntések, tanulságok), commit + push, backlog-frissítés (TASK-2 lezárása / verifikációs-réteg állapot)

## Dependencies

- T006/T008/T010 (tesztek) ELŐBB, mint T007/T009/T011 (implementáció) — teszt-előbb sorrend
- T007 blokkolja T009-et és T011-et
- T013 csak T003 (baseline), T009 és T012 (címkézett minta) után
- MANUÁLIS KAPUk (T005, T014) embert igényelnek

## Validation Checklist

- [ ] Minden FR-hez van task (FR-001→T007, FR-002→T006/T008/T010, FR-003→T009/T011, FR-004→T009, FR-005→T001, FR-006→T006/T007)
- [ ] Minden SC-hez van gate (SC-001→T013, SC-002→T013, SC-003→T006/T008/T010, SC-004→T013)
- [ ] A tesztek az implementáció előtt állnak
- [ ] Minden task konkrét fájlt nevez
