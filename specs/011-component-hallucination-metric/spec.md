# Feature Specification: Komponens-hallucináció detektálás a metrikában + Update Set dataset-lefedettség

**Feature Branch**: `011-component-hallucination-metric`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "A T013 emberi review (2026-08-09) hallucinációt fogott ('ALDI: CHG Scheduled' fabrikált Business Rule-név), amit a metrika nem látott — a hallucination tengely csak KB-cikkszámokat validál. Emellett a GEPA-futás kimutatta, hogy az analyze_changes modul sosem fut a gold dataseten (0 update_set példa), ezért a reflection-iterációk fele üresjárat volt."

## Background (diagnózis)

- **A vakfolt (2026-08-09, T013 review):** a generált cikk 'ALDI: CHG Scheduled' Business Rule-nevet említett, ami a Story-ban 0-szor fordul elő (a modell az `aldi.atlassian.net` URL-ből + a base docstring példamondatából fabrikálta). A metrika eközben `hallucination: 1.000`-et mutatott — a spec 004-es `_find_hallucinated_kb_references` **csak `KBxxxxxxx` számokat** validál, komponensneveket nem.
- **A vakfolt NEM a CLI/artifact-hibából fakad** (azok javítva): az optimized programmal is láthatatlan lenne ez a hibaosztály — az összes eddigi eval-mérés (baseline 2×, optimized 2×, GEPA 200 rollout) komponensnév-ellenőrzés nélkül készült.
- **Prototípus már létezik** (Agent.md 30. szekció): idézett nevek + CamelCase + dotted azonosítók kinyerése → minden jelöltnek a `story_text`-ben kell szerepelnie. A jóváhagyott cikk ezzel 4/4 igazolt nevet adott.
- **Dataset-hézag (T011 GEPA-log tanulsága):** a gold datasetben 0 update_set-es példa → az `analyze_changes` modul a rolloutokban sosem fut (`program.py: if update_set_payloads:`) → a GEPA reflection 6/11 iterációja "No valid reflective examples" üresjárat volt, és az analyze_changes minősége mérhetetlen.
- **Metrika-változás = baseline-elavulás** (spec 010 minta): az új detektálás bekapcsolása után a baseline-t újra kell mérni, `cache=False`-szal.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Komponensnév-hallucináció detektálás (Priority: P1)

A `rich_metric` hallucináció-ellenőrzése kiterjed a nevesített komponensekre: a generált cikkben szereplő minden komponensnév-jelöltnek (idézett nevek, CamelCase azonosítók, dotted identifier-ek) a `story_text`-ben (vagy whitelisten) kell szerepelnie. Ha fabrikált nevet talál, a hallucination tengely 0, és a feedback **nevesíti** a kitalált komponenst.

**Why this priority**: Ez zárja a tegnap leleplezett vakfoltot — a metrika (és a GEPA) csak azt tudja jutalmazni/büntetni, amit lát.

**Independent Test**: Mock cikk egy fabrikált komponensnévvel ('ALDI: CHG Scheduled') → hallucination 0 + a feedback tartalmazza a nevet; ugyanaz a cikk a valódi névvel ('JiraIntegrationUtils', ami a story-ban benne van) → hallucination 1.0.

**Acceptance Scenarios**:

1. **Given** generált cikk fabrikált komponensnévvel, **When** a rich_metric fut, **Then** a hallucination tengely 0, és a feedback felsorolja a kitalált neveket.
2. **Given** generált cikk kizárólag a story-ban szereplő nevekkel, **When** a metric fut, **Then** a hallucination tengely 1.0 marad.
3. **Given** a gold dataset gold HTML-jei, **When** a detektálás rájuk fut, **Then** NINCS false positive (a gold cikkek átmennek).
4. **Given** általános terminusok ("Business Rule", "Script Include", "Incident"), **When** a cikk tartalmazza őket, **Then** NEM számítanak komponensnévnek (whitelist).

---

### User Story 2 - Update Set-es gold példa (Priority: P2)

A gold dataset kap legalább 1 olyan példát, amely tartalmaz `update_set_payloads`-t (valódi Update Set XML-ek) — így az `analyze_changes` modul fut a GEPA-rolloutokban, mérhetővé és optimalizálhatóvá válik, és megszűnnek a "No valid reflective examples" üresjáratok.

**Why this priority**: A metrika-vakfolt (US1) fontosabb; a dataset-bővítés a GEPA-hatékonyságot és az analyze_changes minőségét javítja.

**Independent Test**: a dataset loader betölti az új példát, és egy program-hívás során az `analyze_changes` ténylegesen lefut (trace-ben látszik).

**Acceptance Scenarios**:

1. **Given** az új gold példa, **When** a program fut rajta, **Then** az `analyze_changes` lefut, és a kimenete bekerül a cikk-generálás kontextusába.
2. **Given** a bővített dataset, **When** GEPA reflection készül, **Then** az `analyze_changes.predict`-hez is készülnek reflektív példák (nincs több "No valid reflective examples" emiatt).
3. **Given** az új példa gold cikke, **When** a rich_metric fut rajta, **Then** a példa értékelhető (a gold HTML konzisztens a meglévő 8 példával).

---

### User Story 3 - Validáció az új metrikával (Priority: P3)

Baseline újramérés a kiterjesztett metrikával (a metrika-változás elavulttá teszi a korábbi számokat — spec 010 minta), dokumentált új referencia, és döntés egy opcionális rövid GEPA-futásról.

**Why this priority**: Csak a metrika és a dataset után van értelme; a GEPA-döntés külön, az eredmények ismeretében.

**Independent Test**: `python -m eval.baseline --model local` lefut, az új `runs/baseline.json` per-axis adatokkal + a kiterjesztett hallucination-tengellyel készül.

**Acceptance Scenarios**:

1. **Given** az új metrika, **When** a baseline újramérés lefut, **Then** az új referencia dokumentálva van (Agent.md + tasks.md), a régi számok elavultként jelölve.
2. **Given** az új baseline, **When** döntés készül a mini-GEPA-ról, **Then** az indoklás rögzített (akár elhalasztás is legitim kimenetel).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A komponens-detektálás false positive-mentes a gold dataseten — a gold cikkek átmennek az ellenőrzésen (ez a legfontosabb megkötés; egy zajos tengely rontaná a GEPA-t).
- **FR-002**: A detektálás hibatűrő (spec 010 FR-002 minta): bármilyen belső hiba esetén a tengely ne állítsa meg a metrikát (warning + semleges viselkedés).
- **FR-003**: A whitelist (általános terminusok, terméknevek) egy közös, tesztelt helyen éljen (pl. konstans az `eval/metric.py`-ben, a `BANNED_PHRASES` mintájára).
- **FR-004**: A hallucination tengely **súlya és neve változatlan** (0.15); a detektálás kiterjesztése a meglévő tengelyen belül történik (KB-számok ÉS komponensnevek). A tengely scope-ját a kód-komment/docstring pontosítja (ld. Agent.md 30: "kb_reference_accuracy" félreértés-elkerülés).
- **FR-005**: Az új gold példa update_set_payloads-a valódi (anonymizált) Update Set XML-ekből álljon, és a hozzá tartozó gold cikk tükrözze a kódelemzés eredményét.
- **FR-006**: A metrika-változás után baseline újramérés kötelező, `cache=False`-szal (spec 010 cache-higiénia).

### Success Criteria

- **SC-001**: Fabrikált komponensnév → hallucination 0 + a feedback nevesíti a nevet (mock teszt).
- **SC-002**: A gold dataset gold cikkei 100%-ban átmennek a komponens-ellenőrzésen (0 false positive).
- **SC-003**: Az `analyze_changes` legalább 1 dataset-példán ténylegesen lefut (trace-bizonyíték), és a GEPA reflection hozzá is tud reflektív példákat gyűjteni.
- **SC-004**: Új baseline-referencia dokumentálva; a mini-GEPA döntés indokolt.

## Out of Scope

- Teljes (200 call-os) GEPA újrafutás — legfeljebb rövid, külön jóváhagyott validációs futás.
- A KB-szám-detektálás (spec 004) módosítása — az működik, nem nyúlunk hozzá.
- Produkciós deploy-módosítás (a pipeline érintetlen; a metrika csak az eval-oldalon él).
- A `program.json` újraoptimalizálása az új metrikával — külön döntés a validáció után.
