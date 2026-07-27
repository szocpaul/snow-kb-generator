# Feature Specification: Evidence-First KB Generation (Direction Violation mint speciális eset)

**Feature Branch**: `007-direction-aware-quality` (egyesített spec 007+008)

**Created**: 2026-07-26

**Status**: Draft (review pending — NEM implementált)

**Input**: User description: "A template-filling architektúra strukturálisan hallucinációra kényszerít: a sablon kötelező fejlécei és a hiányos Story közötti rést a modell kitalációval tölti. Megoldás: 'evidence-first' — csak az a szekció kerüljön a cikkbe, amihez a Story bizonyítékot ad; a támogatatlan szekció NE N/A legyen, hanem maradjon ki. Az inbound/outbound direction violation ennek speciális esete (outbound story → Inbound szekció = támogatatlan szekció)."

## Background (diagnózis)

- A STRY0010010 (tisztán outbound Story) Inbound szekciója tartalommal töltődött ki, pedig a Story 100% outbound jelet ad és a gold példák helyes N/A mintát mutatnak.
- Gyökérok: a signature "fill every section, do NOT remove headings" utasítása + a lokális 35B modell gyenge feltételes-utasítás-követése + a metric irány-/támogatottság-vaksága (a feedback nem nevezi meg a hibát → a Kimi K3 reflection vak rá).
- Bármely hiányos Story ugyanezt a mintát produkálja bármelyik szekcióban — a direction violation csak a leglátványosabb eset.
- A stock GEPA proposer "niche factual information" másolására buzdít (ld. KB0012345 hallucináció) — SkilledProposer anti-overfitting + `extra_guidance` kontrollal cseréljük.

## Core Principle

**"No evidence, no section."** A sablon (KBA1–KBA11) ettől kezdve *menü*, nem kötelező váz. A cikk szerkezete a Story tartalmából következik; a hiányzó szekció egyben tisztességes jelzés a Story gazdájának, hogy a mezők hiányosak.

## User Scenarios & Testing

### User Story 1 - Evidence-Aware Metric (Priority: P1)

A `rich_metric` két új ellenőrzést kap:

1. **Direction violation (speciális eset):** a story_text irány-detektálása (inbound/outbound/both/unknown); outbound story + kitöltött Inbound szekció (vagy fordítva) → büntetés + explicit feedback: `"Direction violation: outbound story but 'Inbound Technical Implementation' section is filled."`
2. **Unsupported section penalty (általános eset):** ha a gold cikkben egy szekció N/A/hiányzik, de a pred-ben tartalommal szerepel → büntetés + feedback: `"Unsupported section: '<h2>' has content but the gold article marks it N/A/absent."`

**Why this priority**: Ez az érzékelő — a GEPA reflection csak azt javítja, amit a feedback megnevez.

**Independent Test**: Mock pred kitöltött Inbound szekcióval + outbound gold → "Direction violation" feedback; mock pred gold szerinti N/A-val → nincs büntetés; mock pred extra fejléccel → "Unsupported section" feedback.

**Acceptance Scenarios**:

1. **Given** outbound story_text és kitöltött Inbound szekció, **When** a metric fut, **Then** a template tengely < 1.0 és a feedback tartalmazza: "Direction violation".
2. **Given** a gold cikkben N/A/hiányzó szekció, de a pred-ben kitöltve, **When** a metric fut, **Then** "Unsupported section" feedback.
3. **Given** both/unknown irány, **When** a metric fut, **Then** az irány-ellenőrzés kihagyott (nincs false positive).

---

### User Story 2 - Evidence-First Signature (Priority: P1)

A `GenerateKbFromTemplate` instrukció megfordul: "The html_template is a MENU, not a mandate. Include ONLY sections the story supports with concrete evidence. Omit unsupported sections entirely (do NOT write 'N/A' placeholders). Corollary: for an outbound-only story, omit 'Inbound Technical Implementation' (and vice versa); shared components belong to the direction the story implements."

**Acceptance Scenarios**:

1. **Given** hiányos Story, **When** a generálás lefut, **Then** a cikk csak a támogatott szekciókat tartalmazza.
2. **Given** outbound Story, **When** a generálás lefut, **Then** nincs Inbound szekció (sem N/A, sem tartalom).

---

### User Story 3 - Gold Dataset & Template Alignment (Priority: P2)

A gold dataset példacikkei átállnak az evidence-first logikára: a teljesen N/A-s szekcióblokkok (pl. outbound példában az Inbound szekció) **törlődnek** (nem N/A-ként maradnak). A sablonfájlok (md/html) változatlanok — a sablon továbbra is a teljes menüt tartalmazza.

**Acceptance Scenarios**:

1. **Given** a frissített dataset, **When** betöltjük, **Then** a példacikkek nem tartalmaznak "N/A-only" szekcióblokkot.
2. **Given** a dataset tesztek, **When** futnak, **Then** zöldek (a szerkezeti validáció a frissített elváráshoz igazítva).

---

### User Story 4 - SkilledProposer Integration (Priority: P2)

A GEPA futtatás `instruction_proposer=SkilledProposer(...)`-t használ:
- `extra_guidance`: "Include only sections the story supports; no evidence → omit the section entirely. For outbound-only stories omit the Inbound section (and vice versa). Never invent KB article numbers or titles."
- anti-overfitting meta-prompt; fallback stock proposerre warning-gal.

**Acceptance Scenarios**:

1. **Given** a GEPA futás, **When** proposals készülnek, **Then** az instrukciók tartalmazzák az evidence-first szabályt (gepa_logs run_log.json).
2. **Given** az optimalizált program, **When** a valset-en fut, **Then** 0 direction violation és 0 unsupported section.

---

### User Story 5 - Re-optimization & E2E Validation (Priority: P3)

Baseline + GEPA újrafuttatás (tiszta `gepa_logs/`), export, szerver restart, éles STRY0010010 validáció: nincs Inbound szekció, a megosztott komponensek az Outbound szekcióban.

**Acceptance Scenarios**:

1. **Given** éles újragenerálás, **Then** a cikk ServiceNow API-val ellenőrizve: 0 direction violation.
2. **Given** a teljes tesztcsomag, **Then** minden teszt zöld.

## Requirements

- **FR-001**: Irány-detektálás: story_text "inbound"/"outbound" kulcsszó-előfordulás (0 inbound + ≥1 outbound → outbound; fordítva → inbound; mindkettő → both; egyik sem → unknown = kihagyott ellenőrzés).
- **FR-002**: A direction violation és unsupported section a template_adherence tengelyt rontja (súlyok változatlanok); a feedback explicit és cselekvési javaslatos.
- **FR-003**: A signature evidence-first: menü, nem mandátum; támogatatlan szekció KIHAGYÁS (nem N/A).
- **FR-004**: A gold dataset megtisztítása: N/A-only szekcióblokkok törlése.
- **FR-005**: `skilled-proposer` pip csomag; fallback stock proposer warning-gal.
- **FR-006**: A spec 004/005 védelmi vonalak (hallucination axis, guardrail, related search) változatlanul működnek.

## Success Criteria

- **SC-001**: Valset + éles cikk: 0 direction violation, 0 unsupported section.
- **SC-002**: Optimized score ≥ előző futam (0.850).
- **SC-003**: Teljes tesztcsomag zöld.

## Out of Scope

- Pipeline-guardrail szekció-kényszer (csak ha a metric+GEPA útvonal nem elég — külön spec).
- Teljes LLM-alapú grounding-metric (minden tényállítás story-bizonyíték ellen) — későbbi spec.
- A work_notes-ban lévő "KB article created:" self-reference szűrése (takarítási lista).
