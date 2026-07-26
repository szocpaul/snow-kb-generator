# Feature Specification: Direction-Aware KB Quality (Inbound/Outbound N/A Enforcement)

**Feature Branch**: `007-direction-aware-quality`

**Created**: 2026-07-26

**Status**: Draft (review pending — NEM implementált)

**Input**: User description: "Outbound Story esetén a generált cikk Inbound szekciója tele íródik tartalommal (és fordítva), holott N/A-nak kellene lennie. A hiba 3 rétegben javítandó: (1) a metric legyen irány-érzékeny (a GEPA reflection kapjon jelet), (2) a signature mondja ki explicit az irányszabályt, (3) a GEPA futás SkilledProposer-t használjon extra_guidance-szel és anti-overfittinggel."

## Background (diagnózis)

- A STRY0010010 (tisztán outbound Story) generált cikkében az "Inbound Technical Implementation" szekció tartalommal töltődött ki (megosztott komponensek, pl. `JiraIntegrationUtils` oda lettek sorolva).
- A Story szövege 100% outbound jelet ad (0 inbound említés); a gold dataset arany példái helyesen mutatják az N/A mintát.
- A jelenlegi `template_adherence` tengely csak azt ellenőrzi, *hogy van-e* N/A a cikkben — azt nem, hogy *hol kellene*. A feedback így nem nevezi meg az irány-hibát → a reflection modell (Kimi K3) számára láthatatlan a probléma.
- A stock GEPA proposer "niche factual information" másolására buzdít (ld. korábbi KB0012345 hallucináció) — a SkilledProposer (github.com/cmpnd-ai/skilled-proposer) anti-overfitting meta-prompttal és `extra_guidance` kontrollal ezt strukturálisan kezeli.

## User Scenarios & Testing

### User Story 1 - Direction-Aware Metric (Priority: P1)

A `rich_metric` a story_textből detektálja az integráció irányát (inbound / outbound / both / unknown), és ellenőrzi, hogy a nem alkalmazható szekció (outbound story → Inbound Technical Implementation; inbound story → Outbound Technical Implementation) "N/A"-e. Hiba esetén a feedback explicit: `"Direction violation: outbound story but 'Inbound Technical Implementation' section is filled with content."`

**Why this priority**: Ez az érzékelő — nélküle a GEPA reflection továbbra is vak marad a hibára.

**Independent Test**: Mock pred: outbound gold + kitöltött Inbound szekció → csökkent score + "Direction violation" feedback. Gold N/A-s pred → nincs büntetés.

**Acceptance Scenarios**:

1. **Given** outbound story_text és kitöltött Inbound szekció, **When** a metric fut, **Then** a template/direction axis < 1.0 és a feedback tartalmazza: "Direction violation".
2. **Given** outbound story_text és N/A-s Inbound szekció, **When** a metric fut, **Then** nincs büntetés.
3. **Given** "both" irány (mindkettő említve) vagy "unknown", **When** a metric fut, **Then** az irány-ellenőrzés kihagyott (nincs false positive).

---

### User Story 2 - Explicit Signature Rule (Priority: P2)

A `GenerateKbFromTemplate` signature instrukciója kategorikusan kimondja: "Determine the integration direction from the story. For an outbound-only story, the 'Inbound Technical Implementation' section MUST be exactly 'N/A' (and vice versa). Shared components belong to the direction the story implements."

**Acceptance Scenarios**:

1. **Given** a frissített signature, **When** a program lefut egy outbound story-n, **Then** az Inbound szekció "N/A" (a megosztott komponensek az Outbound szekcióban).

---

### User Story 3 - SkilledProposer Integration (Priority: P2)

A GEPA futtatás `dspy.GEPA(instruction_proposer=SkilledProposer(...))`-t használ:
- `extra_guidance`: az irányszabály + "never invent KB article numbers or titles" (spec 005 tanulsága)
- anti-overfitting meta-prompt (a stock "copy niche facts" viselkedés kiváltása)
- opcionális: prompting-guide skill a gyenge (35B) task modellhez

**Acceptance Scenarios**:

1. **Given** a GEPA futás, **When** az proposals generálódnak, **Then** az új instrukciók tartalmazzák az irányszabályt (a gepa_logs run_log.json-ban ellenőrizhető).
2. **Given** az optimalizált program, **When** a valset-en fut, **Then** 0 direction violation a metric szerint.

---

### User Story 4 - Re-optimization & E2E Validation (Priority: P3)

Baseline + GEPA újrafuttatás (tiszta `gepa_logs/`), export, szerver restart, éles STRY0010010 validáció: az Inbound szekció "N/A", az Outbound szekció tartalmazza a megosztott komponenseket.

**Acceptance Scenarios**:

1. **Given** az éles újragenerálás, **Then** a cikkben nincs "Direction violation" (ServiceNow API-val ellenőrizve).
2. **Given** a teljes tesztcsomag, **Then** minden teszt zöld.

## Requirements

- **FR-001**: Irány-detektálás: a story_text-ben az "inbound"/"outbound" kulcsszavak előfordulása alapján (0 inbound + ≥1 outbound → outbound; fordítva → inbound; mindkettő → both; egyik sem → unknown = ellenőrzés kihagyva).
- **FR-002**: A direction violation a template_adherence tengelyt rontja (súlyok változatlanok); a feedback explicit és cselekvési javaslatot ad.
- **FR-003**: A signature irányszabálya kategorikus ("MUST be exactly 'N/A'"), és a megosztott komponensek elhelyezését is szabályozza.
- **FR-004**: `skilled-proposer` pip csomag; a `run_gepa_optimization()` a SkilledProposer-t használja (fallback: stock proposer, ha az import sikertelen — de ez warning).
- **FR-005**: A meglévő hallucination axis és guardrail viselkedése változatlan (nincs regresszió spec 004/005-ben).

## Success Criteria

- **SC-001**: Valset + éles cikk: 0 direction violation.
- **SC-002**: Az optimized score ≥ az előző futamé (0.850), ideálisan közelíti a gold-konzisztenciát.
- **SC-003**: Teljes tesztcsomag zöld (221+ új tesztek).

## Out of Scope

- A guardrail pipeline-szintű N/A-kényszere (a metric + GEPA útvonal az elsődleges; ha a GEPA után is marad hiba, külön spec).
- Egyéb szekció-szintű tartalmi validációk (pl. Testing Guide kötelező elemei).
