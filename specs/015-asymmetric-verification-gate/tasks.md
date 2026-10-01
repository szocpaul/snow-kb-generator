# Tasks: Aszimmetrikus kalibráció + gate-emelés az írást végző komponensbe

**Input**: Design documents from `/specs/015-asymmetric-verification-gate/`
**Prerequisites**: plan.md, spec.md

## Format: `[ID] [P?] [Story] Description`

* **\[P]**: párhuzamosan futtatható (más fájl, nincs függőség)

* **\[USn]**: melyik user story-hoz tartozik

* **MANUÁLIS KAPU**: emberi döntés — a runner/agent NEM pipálhatja

## Phase 1: Fixture + baseline (US1, playbook: baseline-előbb)

* [x] T001 [US1] Fixture-script `scripts_pdi/`-mintára. **A Story a snow\_kb\_generator projektről szól** (mint integrációs projekt: „ServiceNow oldali webhook-fogadás és KB-draft-generálás bekötése"). **A komponensek a PDI-n MÁR MEGLEVŐ rekordok** (capture, NEM létrehozás): a script a metaadat-táblákat kérdezi le a table-API-n (sys\_script\_include / sys\_script / sys\_properties / sys\_dictionary; active=true, global scope, sys\_updated\_on preferencia), típusonként kiválaszt összesen **10–15 meglévő komponenst** (több típusból: Script Include, Business Rule, System Property, mező — ha van a PDI-n, UI Policy vagy ACL is), capture-öli őket egy Update Set-be, és a Story-szöveget EZERE a valós nevekre írja meg (a logika fordított: nem a story határozza meg a komponenseket). Minden lépés naplózva

* [x] T002 \[US1] A kiválasztott komponensnevek dumpolása artifactba (név, típus, sys\_id, sys\_updated\_on) + a fixture-integritás gate: az update set MINDEN neve spot-checkkel „létezik" (SC-001, exit-code-os script)

* [ ] T003 [US1] **MANUÁLIS KAPU**: a dumpolt komponens-lista emberi review-ja (furcsa/instabil nevek kiszúrása) — a runner NEM pipálhatja

* [x] T004 \[US1] Baseline-rögzítés: a jelenlegi threshold (0.7) ASZIMMETRIKUS költsége a meglévő 24 példás mintán, fájlba (a későbbi összevetés alapja)

## tPhase 2: US1 – Címkézett minta a fixture-ből

* [x] T005 [US1] Minta-származtató script: valós / írásvariáns / fabrikált / típus-eltérés példák gépi generálása a dumpolt név-halmazból (minimalista változat: egyetlen story-kontextus, név-szintű minta); **magminimum-feltétel: ha a jóváhagyott magnév-halmaz < 8 név, a task ÁLLJON MEG és jelentsen — a minta NEM hígítható korrelált variánsokkal**; egyesítés a meglévő 24 példával (az aldidev-eredetű „létezik" címkék kizárva a PDI-mérésből, FR-002) → összesen ≥30 példa, címkék commitolva a `data/examples/` alá

## Phase 3: US2 – Aszimmetrikus kalibráció

* [x] T006 \[US2] Teszt: az aszimmetrikus metrika viselkedése (téves „létező" = 10×, téves „nem létező" = 1× büntetés, jó döntés = 0); a riport-séma (threshold előtt/utána, költség előtt/utána, szimmetrikus összevetés). FAIL implementáció előtt

* [x] T007 \[US2] Aszimmetrikus metrika + ReAnchor-futás az egyesített mintán (`eval/verification_reanchor.py` bővítés, 014-es minta); kalibrációs riport fájlba, beleértve a „threshold marad" eset indoklását is; a production hívás továbbra is közvetlen SDK

* [x] T008 \[US2] Regresszió-gate (SC-003): az új (vagy maradó) threshold a meglévő 24 példás mintán újramérve, összevetve a 014-es baseline-nal → romlás esetén a riport PIROS, a config NEM módosul

* [ ] T009 [US2] **MANUÁLIS KAPU**: a kalibrációs riport review-ja; ha a threshold módosul, az indoklás az Agent.md-be — a runner NEM pipálhatja

## Phase 4: US3 – Gate-emelés a kliensbe (teszt-előbb)

* [x] T010 [US3] Teszt: közvetlen `_create_kb_article_live` hívás (pipeline megkerülve) is gated; normál pipeline-futásban pontosan 1 gate-döntés + 1 recording-bejegyzés; fail-open a kliens-beli gate-ben; a régi pipeline-hívás megszűnt (nincs dupla védelem). FAIL implementáció előtt

* [x] T011 [US3] A `_apply_verification_gate` logika átköltözik a `servicenow_client` írási útjába; a pipeline-rétegű hívás törlődik; deploy-megjegyzés a `deploy/README`-be (restart-pillanatbeli in-flight kérések)

## Phase 5: Zárás

* [x] T012 SC-gate-ek futtatása (SC-001 fixture-integritás, SC-002 kalibrációs riport, SC-003 regresszió, SC-004 gate-tesztek, SC-005 byte-identikus replay) — exit-code-dal, `cache=False`/replay-mód

* [ ] T013 Zárás: teljes pytest-suite zöld (349 + új), Agent.md naplóbejegyzés (tények, döntések, tanulságok), commit + push, backlog-frissítés

## Dependencies

* T001 blokkolja T002-t és T005-öt; T003 (MANUÁLIS KAPU) blokkolja T005-öt

* T006/T010 (tesztek) ELŐBB, mint T007/T011 (implementáció) — teszt-előbb sorrend

* T007 csak T004 (baseline) és T005 (minta) után; T008 a T007 után

* T011 független a kalibrációtól (T007-től) — párhuzamosan mehet a Phase 3-mal, de a T012 mindkettő után fut

## Validation Checklist

* [ ] Minden FR-hez van task (FR-001→T006/T007, FR-002→T005, FR-003→T007/T009, FR-004→T010/T011, FR-005→T010/T011, FR-006→T007)

* [ ] Minden SC-hez van gate (SC-001→T002, SC-002→T007, SC-003→T008, SC-004→T010, SC-005→T012)

* [ ] A tesztek az implementáció előtt állnak

* [ ] Minden task konkrét fájlt nevez

