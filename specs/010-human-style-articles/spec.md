# Feature Specification: Human-Written Style for Generated KB Articles

**Feature Branch**: `010-human-style-articles`

**Created**: 2026-07-28

**Status**: In Progress (US1–US3 implementálva és validálva; US4 a T010c–T014 fázisban)

**Input**: User description: "Az elkészített KB cikkek nagyon AI által írtnak tűnnek, nem elég emberiek. A struktúra és a tények rendben vannak, de a hangnem gépies: boilerplate fordulatok ('This document describes', 'seamless', 'leverage'), egyforma mondatritmus, általánosítások a konkrétumok helyett. A cél: a cikkek úgy olvashatók legyenek, mintha senior mérnök írta volna őket — a kézzel írt KB0010015 a stílus-referencia."

## Background (diagnózis)

- A `rich_metric` jelenleg 4 tengelyt mér (structure, content, template, hallucination) — **stílust nem**. A GEPA alaptörvénye: csak azt javítja, amit a metric lát. Ezért a gépies hangnem láthatatlan az optimalizáció számára.
- A KB0010015 (kézzel írt SolMan cikk) letöltve a ServiceNow-ból: **`data/examples/kb0010015_style_reference.html`** (16.5k karakter) — ez az emberi stílus-minta, amihez viszonyítani lehet; a judge promptja egy reprezentatív részletét kapja.
- **Gold dataset tisztítva és bővítve (2026-07-29)**: a gold HTML-ekből kiszedtük a tiltólistás fordulatokat ("This document describes/outlines", "seamless") — korábban a content tengely jutalmazta azt, amit a style axis büntetni fog. A Példa 5 story-jából az idegen (LDAP/auth) work_notes-maradvány törölve. Új 8. példa (SAP S/4HANA outbound OData) → a split **4 train / 4 val**. Minden korábbi baseline-szám elavult; az új referencia a T010-es friss baseline.
- **Modell-döntés (2026-07-29-i TISZTA mérések, `cache=False`)**: Kimi K3 **0.769** > lokális Qwen3.6-35B-A3B **0.733** (a régi 0.655-ös K3-szám cache-szennyezett volt). A task modell mégis a **lokális Qwen** marad — a 0.036-os minőségkülönbség ellenében a GEPA-rolloutok (több száz generálás) marginális költsége nulla, és a stílus-javítást a GEPA-nak kell behoznia. Egyetlen megmaradt Kimi-függés a GEPA reflection/proposer (K3, kevés hívás).
- **Cache-higiénia**: a mérési scriptekben `cache=False` kötelező — a 2026-07-29-i első lokális baseline a DSPy disk cache-ből (`~/.dspy_cache`) játszotta vissza a Kimi válaszokat (fals 0.655). A javítás az `eval/baseline.py`-ben már megtörtént.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Tone Guidance in Signature (Priority: P1, "ingyen" lépés)

A `GenerateKbFromTemplate` docstringje EGYETLEN stílus-blokkal bővül (boilerplate-tiltólista + emberi hangnem). FONTOS: a meglévő instrukció-szöveghez NEM nyúlunk — a docstring konszolidációja/rövidítése KÜLÖN spec tárgya lesz (a hossz növekedése elfogadott átmeneti állapot).

**Why this priority**: Azonnali, nulla költségű javítás — mielőtt bármit mérnénk, a prompt ne kérje eleve a gépies stílust.

**Independent Test**: Egy generálás a STRY0010010-en, és emberi review: a tiltólistás fordulatok nem jelennek meg.

**Acceptance Scenarios**:

1. **Given** a frissített signature, **When** a pipeline cikket generál, **Then** a kimenet nem tartalmazza a tiltólista elemeit ("This document describes", "seamless", "leverage", "In today's fast-paced world").
2. **Given** ugyanaz a Story, **When** összevetjük a régi és új cikket, **Then** az újban kevesebb generikus fordulat, több konkrétum (mezőnév, endpoint, érték) szerepel.

---

### User Story 2 - Style Judge in Metric (Priority: P2)

A `rich_metric` ötödik tengelye: egy **LLM-as-judge** (ugyanaz a **lokális Qwen3.6-35B-A3B**, mint a task modell), ami 0-1 skálán értékeli, hogy a cikk emberi szakértői hangon szól-e, és konkrét kritikát ad ("milyen fordulat gépies és miért"). A judge promptja a KB0010015-öt tartalmazza pozitív stílus-mintaként.

**Tudatos kompromisszum**: a judge és a task ugyanaz a modell (önértékelés-kockázat) — cserébe nulla költség. Enyhítés: a judge promptja a tiltólista és a KB0010015-referencia köré szerveződik (nem szabad értékelés), és az SC-002 validáció gépies/emberi teszt-ikonokon ellenőrzi a torzítást.

**Why this priority**: Ez teszi a stílust *mérhetővé* — ettől a ponttól a GEPA látja és tudja optimalizálni.

**Independent Test**: Két mock cikk — egy gépies (boilerplate-teljes) és egy emberies — a judge szignifikánsan alacsonyabbra értékeli a gépiest, és a feedback megnevezi a konkrét problémákat.

**Acceptance Scenarios**:

1. **Given** gépies cikk (tele tiltólistás fordulatokkal), **When** a style judge fut, **Then** a style score < 0.4 és a feedback tartalmaz konkrét példát.
2. **Given** emberi hangnemű cikk, **When** a judge fut, **Then** a style score > 0.7.
3. **Given** a metric súlyok, **When** a style axis bekerül, **Then** a végösszeg súlyozva frissül (structure 0.25 + content 0.25 + template 0.15 + hallucination 0.15 + style 0.20), és a meglévő tesztek igazítva zöldek.

---

### User Story 3 - Style Guidance in SkilledProposer (Priority: P2)

A `run_gepa_optimization()` a SkilledProposer `additional_instructions` szövegét stílus-fókuszú guidance-re cseréli (senior engineer hangnem, változatos mondatritmus, konkrétumok az általánosítások helyett) — a meglévő evidence-first és KB-hallucináció szabályok MEGMARADNAK. A reflection/proposer modell továbbra is Kimi K3.

**Why this priority**: A mért stílus (US2) után ez teszi a GEPA-t stílus-tudatossá: a reflection feedbackje alapján a proposer általánosítható stílus-szabályokat építhet a promptokba.

**Independent Test**: Egységteszt: a proposer az új guidance-szel jön létre, a fallback ág változatlan.

**Acceptance Scenarios**:

1. **Given** a GEPA futás, **When** a proposer reflection-t kap a style axisról, **Then** a javasolt új instrukciók tartalmaznak stílus-szabályt (boilerplate-kerülés, konkrétumok).
2. **Given** a proposer létrehozása, **When** a kód fut, **Then** az evidence-first és KB-hallucináció szabályok továbbra is jelen vannak az `additional_instructions`-ben.

---

### User Story 4 - GEPA on Style (Priority: P3)

GEPA futás **lokális task modellel** (a rolloutok ingyenesek), Kimi K3 reflection-nel, amelynek célja kizárólag a stílus-javítás bizonyítása: a style axis átlag javuljon a valset-en.

**Why this priority**: Csak a mért stílus és a stílus-tudatos proposer után van értelme. A büdzsé nem kvóta-, hanem **időkorlátos**: a style judge miatt minden metric call KÉT lokális hívás (cikk + pontozás), mért ár ~60 mp/hívás. Mért adat alapján (T010 baseline) **`max_metric_calls=200` ≈ 2.5-3.5 óra** a `-np 2` slotokkal — a cél csak a style-javulás bizonyítása, ehhez elég; ha nem javulna szignifikánsan, külön döntés után eszkalálható.

**Acceptance Scenarios**:

1. **Given** a GEPA futás, **When** befejeződik, **Then** az optimized program style-átlaga ≥ baseline style-átlag + 0.05, és a többi tengely max −0.02 romlás (per-axis adatok a runs/*.json-ben, T010c).
2. **Given** az optimalizált program, **When** éles STRY0010010 generálás történik, **Then** emberi review szerint a cikk kevésbé gépies, mint az előző változat.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A signature stílus-szabályai NEM rontják a meglévő viselkedést (evidence-first, template-konformitás, guardrails érintetlenek).
- **FR-002**: A style judge determinisztikusan hibátűrő: ha a judge hívás elszáll (pl. a lokális szerver nem elérhető — VPS/szerver restart valós forgatókönyv), a style axis 0.5 (semleges) és warning — a metric sosem áll meg miatta.
- **FR-003**: A judge promptja tartalmazza a tiltólistát és a KB0010015 referencia-részletet.
- **FR-004**: A GEPA futás időkerete kontrollált: `max_metric_calls = 200` (időkorlát, nem kvótavédelem — a rolloutok lokálisak; a judge-hívásokkal együtt ~2.5-3.5 óra a `-np 2` slotokkal). A reflection/proposer hívások továbbra is Kimi K3-ra mennek, azok száma kicsi. A `num_threads` a szerver slotjaihoz igazított (2).
- **FR-005**: A `run_gepa_optimization()` a SkilledProposer-t a stílus-fókuszú `additional_instructions`-szel hozza létre; a meglévő evidence-first és KB-hallucináció szabályok megmaradnak.
- **FR-006**: Minden mérési script (baseline, GEPA, validáció) `cache=False`-szal fut — a DSPy disk cache modell-azonosítás nélkül visszajátszhatja korábbi válaszokat (2026-07-29-i fals baseline tanulsága).
- **FR-007**: A mérési kimenetek (runs/*.json) tengelyenkénti pontszámokat is perzisztálnak (`per_example` axes) — a style-javulás automatizáltan ellenőrizhető legyen, ne csak a szöveges feedbackből olvasható ki.
- **FR-008**: Megszakadt GEPA futás (pl. Kimi kvóta-hiba a reflection-ben) ugyanazzal a `log_dir`-rel újraindítva a checkpointból folytatódik (DSPy 3.3.0b1); a clean run `rm -rf gepa_logs`-ja csak szándékos, preflight-olt újraindításnál megengedett.

### Success Criteria

- **SC-001**: Éles cikkekben 0 tiltólistás fordulat (automatikus regex-ellenőrzéssel is mérhető).
- **SC-002**: A style judge validált (gépies < 0.4, emberi > 0.7 a teszt-ikonokon). Ha a szoros küszöbök miatt elbukna: fallback kritérium a relatív gap (gépies < emberi − 0.3).
- **SC-003**: Emberi review: a végleges cikkek "emberinek tűnnek" (subjektív, de a spec ezt is rögzíti mint cél).
- **SC-004**: A baseline referencia a T010-es friss mérés a **tisztított, 8 példás dataseten** (4 train / 4 val, `cache=False`, új 5-tengelyes metric-kel) → `runs/baseline.json`. A style javulást az ottani style-axis átlaghoz mérjük (a 2026-07-29-i 0.733/0.769 számok a régi datasetre vonatkoznak, nem összehasonlíthatók). A tengely-értékeket a T010c perzisztálja a runs/*.json-be; a javulás küszöbe: **style ≥ baseline + 0.05**, a többi tengely max **−0.02** romlás — ez gate-parancsként automatikusan ellenőrizhető.

## Out of Scope

- Teljes újraírás emberi kézzel (a cél a generált minőség, nem a manuális munka).
- A stílus judge finomhangolása külön LM-mel (a lokális Qwen judge most elég; ha az SC-002 validáció torzítást mutat, külön judge-modell átgondolandó).
