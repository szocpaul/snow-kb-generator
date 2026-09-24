# Feature Specification: Audience-döntés kalibrált bizonyossággal

**Feature Branch**: `013-audience-typed-decision`

**Created**: 2026-09-17

**Status**: Draft

**Input**: User description: "Az ExtractChange audience mezőjét a Kimi K3 adja, de kalibrált bizonyossági jelzés nélkül — a határesetekben nem látjuk, hogy a modell biztos volt vagy tippelt, így a cikk stílusa rossz alapra épülhet."

## Background (diagnózis) *(projekt-overlay)*

- Az `ExtractChange` signature `audience` mezője `Literal["helpdesk","end-user","developer"]` — zárt, három opciós döntés, amit jelenleg a generatív modell ad stringként, bármilyen bizonyossági jelzés nélkül.
- Az audience határozza meg a generált cikk stílusát és technikai mélységét (`GenerateKbFromTemplate` docstring: "use it ONLY to adapt the writing style/tone") — egy rosszul landolt döntés az egész cikk hangját elviszi, és a hiba csak az emberi review-ban derül ki.
- A generatív modellek (RLHF-tanítás miatt) jellemzően túlbiztosak: a határeset (pl. "end-user vs helpdesk") ugyanolyan magabiztos stringként jön vissza, mint a nyilvánvaló eset.
- A döntés jellege amúgy is "gut-check" — egy pillanat-ítélet három opció közül, nem hosszú reasoning; különösen alkalmas arra, hogy a generálástól elválasszuk.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Az audience-döntés valószínűséggel és confidence-szel (Priority: P1)

A pipeline az audience-mezőt egy dedikált, típusos döntési hívással állítja elő: a válasz tartalmazza a kiválasztott opciót, az opciónkénti valószínűségeket és egy confidence-értéket. A `change_summary` és `key_steps` változatlanul a generatív modellé marad.

**Why this priority**: Ez a spec egyetlen értéke — a bizonyosság láthatóvá tétele. Minden más erre épül.

**Independent Test**: Mock story (egyértelműen developer-jellegű) → audience="developer", magas confidence; határeset mock story → confidence mérhetően alacsonyabb.

**Acceptance Scenarios**:

1. **Given** egyértelmű story, **When** a pipeline fut, **Then** az audience ugyanaz, mint a jelenlegi modelltől, ÉS confidence ≥ 0.8.
2. **Given** szándékosan határeset story (üzleti folyamatot leíró, de fejlesztői részletekkel), **When** a pipeline fut, **Then** a confidence < 0.8, és az érték naplózva van.
3. **Given** a 9 gold példa, **When** az új döntési út rajtuk fut, **Then** a gold audience-del való egyezés rátája nem rosszabb, mint a jelenlegi modellé (per-példa JSON-kimenet).

---

### User Story 2 - Alacsony confidence kezelése (Priority: P2)

Ha a confidence egy konfigurálható küszöb alatt van, a pipeline explicit viselkedik: default `developer` (a legbiztonságosabb technikai hangnem) + jelzés a work_notes-ban, hogy az audience bizonytalan volt.

**Why this priority**: Csak akkor van értelme, ha US1 már ad confidence-t; a fallback-politika kis, de tudatos döntés.

**Independent Test**: Mock alacsony-confidence válasz → audience="developer" + work_notes-jelzés.

**Acceptance Scenarios**:

1. **Given** confidence < küszöb, **When** a pipeline fut, **Then** audience="developer" és a work_notes tartalmazza a jelzést a mért confidence-szel.
2. **Given** confidence ≥ küszöb, **When** a pipeline fut, **Then** nincs fallback, nincs jelzés.

---

### Edge Cases

- Mi történik, ha a döntési szolgáltatás nem érhető el (timeout, 5xx, auth-hiba)? → fail-open a meglévő generatív útra, warning-loggal (FR-001).
- Mi történik, ha a válasz confidence-értéke pontosan a küszöbön van? → a "küszöb alatt" szabály legyen szigorú egyenlőség-mentes (`<`, nem `<=`), a határérték a biztonságos (fallback) irányba dőljön.
- Mi történik, ha a story szövege annyira hiányos, hogy mindhárom opció valószínűsége alacsony? → az confidence eleve alacsony lesz, a P2-es fallback-út kezeli.
- Mi történik, ha a válasz sémája váratlan (SDK-verzióeltérés)? → ugyanaz a fail-open út, mint az API-hiba, plusz a hiba naplózása.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A döntési hívás hibatűrő (fail-open a jelenlegi viselkedéshez): bármilyen hiba esetén a pipeline visszaesik a meglévő, generatív modell általi audience-re, warning-loggal. A rendelkezésreállás elsődleges.
- **FR-002**: A küszöb és a döntési modell verziója a `config.yaml`-ban konfigurálható; a kalibrációs méréshez pinnelt verzió, nem lebegő alias (playbook: "modell-csere = baseline újramérés").
- **FR-003**: Minden döntés naplózza: választott opció, opciónkénti valószínűségek, confidence — ez a kalibrációs adatforrás. A napló formátuma replay-kompatibilis legyen (a jev-dspy-lab mintája: JSONL, request hash, response, mért latency, modellazonosító), hogy a kalibrációs mérés élő API nélkül, determinisztikusan újrafusson.
- **FR-004**: A jelenlegi, generatív audience-út megmarad kapcsolható fallback-ként (config-flag), amíg a kalibrációs mérés le nem zárul.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Gold dataset (9 példa): az új döntés egyezik a gold audience-del legalább annyi példán, mint a jelenlegi — per-példa JSON-ben, compare-script exit-code-dal ellenőrizve.
- **SC-002**: Kalibrációs minőség a gold + mock mintán (a jev-dspy-lab metrikanyelvén): a 0.7-es confidence-kapunál **selective risk ≤ 0.15** ÉS **coverage ≥ 0.7**, továbbá **ECE (expected calibration error) ≤ 0.10**. A mérés determinisztikus replay-ből (rögzített válaszokból) származzon, ne élő API-hívásból — a threshold-sweep sor csak exploratív, a confirmatory eredmény az előre kijelölt 0.7-es kapu.
- **SC-003**: Fail-open teszt: szimulált API-kiesésnél a pipeline hiba nélkül lefut, a fallback út eredményével.
- **SC-004**: Reprodukálhatóság: ugyanaz a rögzített válaszhalmaz kétszer lejátszva byte-identikus mérőjelentést ad (a lab ReplayClient mintája); élő újrafelvételnél a per-példa döntések stabilak pinnelt modellel.

## Assumptions

- A gold dataset 9 példájához a helyes audience levezethető a gold cikkek stílusából; ha nem, a címkézés a mérés előfeltétele (tasks.md-ben külön task).
- A döntési szolgáltatás kifelé engedélyezett a szerverről (hosted API); a kulcs a systemd unit környezetében elérhető.
- A "developer" mint alacsony-confidence default a legbiztonságosabb hangnem a csapat számára — ha a review ezt másképp látja, az US2 módosul.
- A meglévő 286-tesztes suite zöld marad; az új viselkedéshez új tesztek készülnek.

## Out of Scope *(projekt-overlay, újraindítási feltételekkel)*

- A generálás-utáni verifikációs réteg (komponensnév-hallucináció gate) — külön spec; újraindítási feltétel: ha ez a spec productionben stabil, és a confidence-adatok alapján a küszöb-hangolás értelmezhető.
- A `change_summary`/`key_steps` mezők bármilyen átírása.
- A `dspy-typesafeify` fork vagy bármilyen DSPy-fork használata — közvetlen SDK-hívás a pipeline-ból.
- Az 5-tengelyes eval-metrika módosítása — az audience-váltás hatását a meglévő rich_metric mutatja meg, a metrika maga érintetlen.
