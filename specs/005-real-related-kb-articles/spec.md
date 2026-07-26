# Feature Specification: Real Related KB Articles from ServiceNow

**Feature Branch**: `005-real-related-kb-articles`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "A 'Table of related KB articles' szekció jelenleg hallucinált short descriptionöket tartalmaz KBXXXXXXX placeholder számokkal, mert a sablon kötelezi a szekciót, de nincs valódi adatforrás. A pipeline generálás előtt ServiceNow KB kereséssel találjon valódi kapcsolódó cikkeket, és azok (valódi szám + valódi cím) kerüljenek a táblába. Ha nincs találat, a szekció legyen 'N/A'."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - KB Search in ServiceNow Client (Priority: P1)

A `ServiceNowClient` kap egy `search_kb_articles(query, limit)` metódust, ami a `kb_knowledge` táblában keres (short_description alapján, `123TEXTQUERY321` vagy CONTAINS operátorral), és strukturált listát ad vissza: `[{number, short_description, sys_id}]`.

**Why this priority**: Ez az adatforrás az egész feature alapja — valódi cikkek nélkül nincs mit a táblába írni.

**Independent Test**: Mockolt ServiceNow válasszal tesztelhető: a metódus helyesen építi fel a query-t, és a válaszból a mezőket kinyeri.

**Acceptance Scenarios**:

1. **Given** egy mockolt kb_knowledge válasz 2 cikkel, **When** `search_kb_articles("jira")` fut, **Then** a lista a valódi number + short_description párokat tartalmazza.
2. **Given** üres találati lista, **When** a metódus fut, **Then** üres listát ad vissza (nem dob hibát).

---

### User Story 2 - Pipeline Integration (Priority: P1)

A `generate_kb_article()` a generálás előtt lekéri a kapcsolódó cikkeket (a Story short_description kulcsszavai alapján), és a `related_articles_context`-et átadja a programnak új inputként. A program ebből tölti ki a "Table of related KB articles" szekciót; üres lista esetén "N/A".

**Why this priority**: Így jut el a valódi adat a modellhez — a hallucináció forrása szűnik meg.

**Independent Test**: Mock client + mock programmal: a pipeline meghívja a keresést, és a kapott kontextust továbbítja a program hívásába.

**Acceptance Scenarios**:

1. **Given** a client 2 valódi cikket talál, **When** a pipeline fut, **Then** a program `related_articles_context`-e tartalmazza a valódi KB számokat és címeket.
2. **Given** nincs találat, **When** a pipeline fut, **Then** a kontextus "N/A"-t jelölő üres érték, és a generált cikkben a szekció "N/A".
3. **Given** a KB keresés hibát dob (hálózat), **When** a pipeline fut, **Then** a generálás warning-gal folytatódik (mint az Update Set lekérésnél).

---

### User Story 3 - Guardrail & Metric Extension (Priority: P1)

A hallucináció-ellenőrzés (spec 004) kiterjed a `related_articles_context`-re: a valódi keresési találatokból származó KB számok "ismert" hivatkozásnak számítanak mind a `strip_hallucinated_references()`-ben, mind a metric hallucination axis-ában.

**Why this priority**: Enélkül a spec 004-es guardrail pont a valódi cikkeket törölné hallucináltként (false positive).

**Independent Test**: A guardrail a related context-ben szereplő KB számot érintetlenül hagyja, az azon kívülit továbbra is törli.

**Acceptance Scenarios**:

1. **Given** generált HTML a related context-ből származó KB számmal, **When** a guardrail fut, **Then** a hivatkozás érintetlen marad.
2. **Given** a metric a related contextet is ismeri, **When** a pred a valódi számot tartalmazza, **Then** nincs hallucination büntetés.

---

### User Story 4 - Re-optimization (Priority: P2)

A signature változás (új input) miatt a baseline + GEPA újrafuttatása, új `artifacts/program.json` export, éles validáció.

**Acceptance Scenarios**:

1. **Given** az új program, **When** a GEPA lefut, **Then** az optimalizált program a related szekciót valódi adattal tölti ki (valset + éles STRY0010010 validáció).

## Requirements

- **FR-001**: `ServiceNowClient.search_kb_articles(query, limit=5)` → `[{number, short_description, sys_id}]`, hibátűrő (ServiceNowError terjed, de a pipeline elkapja).
- **FR-002**: A pipeline a keresés eredményét `related_articles_context` stringként adja át a programnak (formátum: soronként `KB<number> | <short_description>`).
- **FR-003**: A program signature kibővül a `related_articles_context` inputtal (default ""); üres esetben a szekció "N/A".
- **FR-004**: `strip_hallucinated_references(html, story_text, known_refs="")` — a `related_articles_context` KB számai ismert hivatkozásnak számítanak.
- **FR-005**: A metric hallucination axis a gold example opcionális `related_articles_context` mezőjét is figyelembe veszi.
- **FR-006**: Dry-run módban a keresés kihagyható (mock cikk).

## Success Criteria

- **SC-001**: Éles STRY0010010 cikkben a "Related articles" tábla valódi KB számokat tartalmaz (ServiceNow-ban létező cikkek), vagy "N/A".
- **SC-002**: A guardrail false-positive rátája 0 a valódi találatokon (tesztekkel).
- **SC-003**: Teljes tesztcsomag zöld.
