# Feature Specification: Human-Written Style for Generated KB Articles

**Feature Branch**: `010-human-style-articles`

**Created**: 2026-07-28

**Status**: Draft

**Input**: User description: "Az elkészített KB cikkek nagyon AI által írtnak tűnnek, nem elég emberiek. A struktúra és a tények rendben vannak, de a hangnem gépies: boilerplate fordulatok ('This document describes', 'seamless', 'leverage'), egyforma mondatritmus, általánosítások a konkrétumok helyett. A cél: a cikkek úgy olvashatók legyenek, mintha senior mérnök írta volna őket — a kézzel írt KB0010015 a stílus-referencia."

## Background (diagnózis)

- A `rich_metric` jelenleg 4 tengelyt mér (structure, content, template, hallucination) — **stílust nem**. A GEPA alaptörvénye: csak azt javítja, amit a metric lát. Ezért a gépies hangnem láthatatlan az optimalizáció számára.
- A KB0010015 (kézzel írt SolMan cikk) a gold datasetben már jelen van — ez az emberi stílus-minta, amihez viszonyítani lehet.
- A Kimi-direct architektúra óta a task modell erős (0.655 baseline), így a stílus az egyetlen maradó minőségi hézag.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tone Guidance in Signature (Priority: P1, "ingyen" lépés)

A `GenerateKbFromTemplate` instrukció kiegészül explicit stílus-szabályokkal: szakértői hangnem, boilerplate-tiltólista, változatos mondatszerkezet, konkrétumok előnyben.

**Why this priority**: Azonnali, nulla költségű javítás — mielőtt bármit mérnénk, a prompt ne kérje eleve a gépies stílust.

**Independent Test**: Egy generálás a STRY0010010-en, és emberi review: a tiltólistás fordulatok nem jelennek meg.

**Acceptance Scenarios**:

1. **Given** a frissített signature, **When** a pipeline cikket generál, **Then** a kimenet nem tartalmazza a tiltólista elemeit ("This document describes", "seamless", "leverage", "In today's fast-paced world").
2. **Given** ugyanaz a Story, **When** összevetjük a régi és új cikket, **Then** az újban kevesebb generikus fordulat, több konkrétum (mezőnév, endpoint, érték) szerepel.

---

### User Story 2 - Style Judge in Metric (Priority: P2)

A `rich_metric` ötödik tengelye: egy **LLM-as-judge** (Kimi K3), ami 0-1 skálán értékeli, hogy a cikk emberi szakértői hangon szól-e, és konkrét kritikát ad ("milyen fordulat gépies és miért"). A judge promptja a KB0010015-öt tartalmazza pozitív stílus-mintaként.

**Why this priority**: Ez teszi a stílust *mérhetővé* — ettől a ponttól a GEPA látja és tudja optimalizálni.

**Independent Test**: Két mock cikk — egy gépies (boilerplate-teljes) és egy emberies — a judge szignifikánsan alacsonyabbra értékeli a gépiest, és a feedback megnevezi a konkrét problémákat.

**Acceptance Scenarios**:

1. **Given** gépies cikk (tele tiltólistás fordulatokkal), **When** a style judge fut, **Then** a style score < 0.4 és a feedback tartalmaz konkrét példát.
2. **Given** emberi hangnemű cikk, **When** a judge fut, **Then** a style score > 0.7.
3. **Given** a metric súlyok, **When** a style axis bekerül, **Then** a végösszeg súlyozva frissül (structure 0.25 + content 0.25 + template 0.15 + hallucination 0.15 + style 0.20), és a meglévő tesztek igazítva zöldek.

---

### User Story 3 - Small-Budget GEPA on Style (Priority: P3)

Kis büdzséjű GEPA futás (~250 metric call) Kimi task modellel, amelynek célja kizárólag a stílus-javítás bizonyítása: a style axis átlag javuljon a valset-en.

**Why this priority**: Csak a mért stílus után van értelme — és korlátozott kvótával (a rolloutok Kimi-hívások).

**Acceptance Scenarios**:

1. **Given** a GEPA futás, **When** befejeződik, **Then** az optimized program style-átlaga > baseline style-átlag (mérve a runs/*.json-ben).
2. **Given** az optimalizált program, **When** éles STRY0010010 generálás történik, **Then** emberi review szerint a cikk kevésbé gépies, mint az előző változat.

---

### User Story 4 - Small-Budget GEPA on Style (Priority: P3)

Kis büdzséjű GEPA futás (~250 metric call) Kimi task modellel, amelynek célja kizárólag a stílus-javítás bizonyítása: a style axis átlag javuljon a valset-en.

**Why this priority**: Csak a mért stílus és a stílus-tudatos proposer után van értelme — és korlátozott kvótával (a rolloutok Kimi-hívások).

**Acceptance Scenarios**:

1. **Given** a GEPA futás, **When** befejeződik, **Then** az optimized program style-átlaga > baseline style-átlag (mérve a runs/*.json-ben).
2. **Given** az optimalizált program, **When** éles STRY0010010 generálás történik, **Then** emberi review szerint a cikk kevésbé gépies, mint az előző változat.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A signature stílus-szabályai NEM rontják a meglévő viselkedést (evidence-first, template-konformitás, guardrails érintetlenek).
- **FR-002**: A style judge determinisztikusan hibátűrő: ha a judge hívás elszáll, a style axis 0.5 (semleges) és warning — a metric sosem áll meg miatta.
- **FR-003**: A judge promptja tartalmazza a tiltólistát és a KB0010015 referencia-részletet.
- **FR-004**: A GEPA futás `max_metric_calls <= 300` marad (kvótavédelem).
- **FR-005**: A `run_gepa_optimization()` a SkilledProposer-t a stílus-fókuszú `additional_instructions`-szel hozza létre; a meglévő evidence-first és KB-hallucináció szabályok megmaradnak.

### Success Criteria

- **SC-001**: Éles cikkekben 0 tiltólistás fordulat (automatikus regex-ellenőrzéssel is mérhető).
- **SC-002**: A style judge validált (gépies < 0.4, emberi > 0.7 a teszt-ikonokon).
- **SC-003**: Emberi review: a végleges cikkek "emberinek tűnnek" (subjektív, de a spec ezt is rögzíti mint cél).

## Out of Scope

- Teljes újraírás emberi kézzel (a cél a generált minőség, nem a manuális munka).
- A stílus judge finomhangolása külön LM-mel (a Kimi K3 judge most elég).
