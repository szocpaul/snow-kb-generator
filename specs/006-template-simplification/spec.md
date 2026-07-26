# Feature Specification: Template Simplification (Audience as Style, Not Section)

**Feature Branch**: `006-template-simplification`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "A sablonból el kell távolítani: a 'Knowledge Base Structure for Interface Documentation' főcímet, a 'Theme' sorokat, és a 'Target Audience' szekciókat (beleértve a related articles tábla 3. oszlopát). A célközönség viszont maradjon meg STÍLUSKÉNT: az adott szekció tartalma a célközönségnek megfelelő nyelvezettel legyen megfogalmazva, anélkül hogy a Target Audience explicit megjelennék a cikkben."

## User Scenarios & Testing

### User Story 1 - Simplified Template (Priority: P1)

A sablon (helyi `integration_team_template.md/.html` + a ServiceNow-ban élő "Structure" cikk) lecsupaszítása: KBA1-KBA11 szekciók csak címsorból és Content-listából állnak. Nincs H1 főcím, nincs Theme sor, nincs Target Audience szekció, a related articles tábla 2 oszlopos (Short description + Article number).

**Acceptance Scenarios**:

1. **Given** az új sablon, **When** betöltjük, **Then** nem tartalmaz "Theme:", "Target Audience" szekciót, sem H1 főcímet; a KBA1-KBA11 címsorok megmaradnak.
2. **Given** a ServiceNow-ban élő sabloncikk, **When** a `get_team_template()` lekéri, **Then** a frissített, egyszerűsített HTML-t adja vissza.

### User Story 2 - Audience as Writing Style (Priority: P1)

A program továbbra is kinyeri a célközönséget (ExtractChange.audience), és ezt a template-generáló lépés stílusinstrukcióként kapja meg: "Write for {audience}, but do NOT include a Target Audience section."

**Acceptance Scenarios**:

1. **Given** egy developer-célközönségű Story, **When** a generálás lefut, **Then** a cikk technikai nyelvezetű, de nincs benne "Target Audience" szekció.
2. **Given** a gold dataset frissült, **When** a dataset tesztek futnak, **Then** a példacikkek sem tartalmazzák a kivett elemeket.

### User Story 3 - Dataset + Re-optimization (Priority: P2)

A gold dataset 5 példacikke megtisztítása (H1, Theme, Target Audience, 3. oszlop törlése), baseline + GEPA újrafuttatás, éles validáció.

**Acceptance Scenarios**:

1. **Given** az új dataset, **When** a GEPA lefut, **Then** az optimalizált program az új sablon szerint generál.
2. **Given** éles STRY0010010, **When** újrageneráljuk, **Then** a cikkben nincs Theme/Target Audience/H1 struktúra-cím, a related tábla 2 oszlopos.

## Requirements

- **FR-001**: A sablon KBA1-KBA11 struktúrája megmarad (címsor + Content), minden más meta-elem törlődik.
- **FR-002**: A related articles tábla 2 oszlopos (Short description | Article number).
- **FR-003**: A `GenerateKbFromTemplate` signature instrukció kiegészül: az audience stílus, nem szekció.
- **FR-004**: A gold dataset és a lokális sablonfájlok szinkronban az új struktúrával.
- **FR-005**: A ServiceNow-ban élő sabloncikk `text` mezője frissül (Table API PATCH).
