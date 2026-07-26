# Feature Specification: Hallucination-Free KB Article Generation

**Feature Branch**: `004-no-hallucinated-references`

**Created**: 2026-07-26

**Status**: Draft

**Input**: User description: "A generált KB cikkek semmiképp sem tartalmazhatnak hallucinált hivatkozásokat (pl. fiktív KB cikkszámok, mint KB0012345/KB0012346, amik a gold dataset fiktív példáiból szivárogtak át). A rendszernek garantálnia kell, hogy minden hivatkozás, tény és cikkszám a forrás Story-ból vagy valós ServiceNow adatból származzon."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Gold Dataset Sanitization (Priority: P1)

A gold dataset (`data/examples/gold_dataset.md`) fiktív KB cikkszámokat tartalmaz a példacikkek "Related Articles" szekcióiban (KB0012345, KB0012346). Ezek a GEPA optimalizáció során beégnek a promptokba, és a generált cikkekben hallucinált hivatkozásokként jelennek meg. A datasetet úgy kell megtisztítani, hogy a hivatkozások egyértelműen placeholder-ek legyenek, vagy valós, a Story kontextusából származó hivatkozások.

**Why this priority**: A tanítóadat a hallucináció elsődleges forrása — amíg a dataset fiktív cikkszámokat tartalmaz, bármelyik újraoptimalizált program reprodukálni fogja őket.

**Independent Test**: Betöltjük a gold datasetet, és assertáljuk, hogy egyetlen példacikk sem tartalmaz valódiságnak álcázott fiktív KB számot (KB + 7 számjegy minta, ami nem placeholder formátum).

**Acceptance Scenarios**:

1. **Given** a megtisztított gold_dataset.md, **When** a loader betölti, **Then** minden "Related Articles" típusú hivatkozás placeholder (`KBXXXXXXX`) vagy "N/A", és egyetlen konkrét, nem létező KB szám sem szerepel.
2. **Given** a megtisztított dataset, **When** lefut a dataset test suite, **Then** az összes teszt zöld marad (a szerkezet változatlan).

---

### User Story 2 - Hallucination Detection in Metric (Priority: P1)

A `rich_metric`-nek ki kell terjednie a hallucináció-detektálásra: ha a generált cikk olyan KB cikkszámot, URL-t vagy konkrét tényt tartalmaz, ami nem szerepel a bemeneti Story szövegben (és nem placeholder), azt a metric bünteti és a feedback-ben megnevezi.

**Why this priority**: A GEPA csak azt javítja, amit a metric mér. Hallucináció-tengely nélkül az optimalizáció visszahozza a fiktív hivatkozásokat.

**Independent Test**: Mock predikcióval tesztelhető: adunk egy pred-et fiktív KB számmal, és egy gold-ot anélkül → a metric score-nak csökkennie kell, és a feedback-nek tartalmaznia kell a hallucinált azonosítót.

**Acceptance Scenarios**:

1. **Given** egy pred, ami `KB0012345`-öt tartalmaz, és a story_text ezt NEM tartalmazza, **When** a rich_metric fut, **Then** a hallucination axis 0, és a feedback tartalmazza: "Hallucinated reference: KB0012345".
2. **Given** egy pred, ami csak a story_text-ben szereplő KB számokat tartalmazza, **When** a rich_metric fut, **Then** a hallucination axis 1.0, büntetés nélkül.
3. **Given** egy pred, ami placeholder-t (`KBXXXXXXX`) vagy "N/A"-t tartalmaz, **When** a rich_metric fut, **Then** nem számít hallucinációnak.

---

### User Story 3 - Post-Generation Guardrail (Priority: P2)

A pipeline a generálás után, push előtt validálja a cikket: minden KB cikkszám-hivatkozásnak (a) a story_text-ben kell szerepelnie, vagy (b) placeholder-nek/"N/A"-nak kell lennie. Hallucinált hivatkozás esetén a pipeline a hivatkozást eltávolítja (strip) vagy hibát dob — sosem pushol hallucinált tartalmat.

**Why this priority**: Defense-in-depth — még ha a metric/GEPA át is engedne valamit, a produkciós útvonalon (server → ServiceNow) ne juthasson ki hallucináció.

**Independent Test**: Egységteszt: a guardrail függvény egy hallucinált KB számot tartalmazó HTML-ből eltávolítja a hivatkozást, a valódit érintetlenül hagyja.

**Acceptance Scenarios**:

1. **Given** generált HTML fiktív KB számmal, **When** a guardrail fut push előtt, **Then** a fiktív hivatkozás eltávolításra kerül, és a pipeline warning-ot logol.
2. **Given** generált HTML valódi (story_text-ből származó) KB számmal, **When** a guardrail fut, **Then** a HTML változatlan marad.
3. **Given** a FastAPI szerver, **When** hallucinált cikk érkezne push-ra, **Then** a végleges HTML már nem tartalmaz hallucinált hivatkozást.

---

### User Story 4 - Re-optimization with Clean Data (Priority: P3)

A megtisztított dataset + kibővített metric mellett a baseline és a GEPA optimalizáció újrafuttatása, az új `artifacts/program.json` exportálása.

**Why this priority**: Csak a tiszta adaton optimalizált program garantálja az hallucináció-mentességet hosszú távon.

**Independent Test**: Az új baseline és optimized score-ok összehasonlítása; az optimalizált program által generált cikkekben a guardrail nem talál hallucinációt a valset-en.

**Acceptance Scenarios**:

1. **Given** az új metric és dataset, **When** a baseline újrafut, **Then** a `runs/baseline.json` frissül, és a hallucination axis látható a per-example feedback-ben.
2. **Given** a GEPA újrafuttatása, **When** befejeződik, **Then** az optimalizált program valset-generálásai hallucináció-mentesek (guardrail-ellenőrzéssel validálva).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A gold dataset NEM tartalmazhat valódiságnak álcázott fiktív KB cikkszámokat; a hivatkozások placeholder (`KBXXXXXXX`) vagy "N/A" formátumúak.
- **FR-002**: A `rich_metric` tartalmaz hallucination axis-t: a generált HTML-ben talált KB szám minták (KB + ≥6 számjegy) összevetésre kerülnek a story_text-tel; az ismeretlen, nem-placeholder azonosítók büntetéshez és explicit feedback-hez vezetnek.
- **FR-003**: A pipeline push előtt minden cikket át kell hogy fusson egy `strip_hallucinated_references(html, story_text)` guardrailen; az eltávolított hivatkozások logolásra kerülnek.
- **FR-004**: A guardrail sosem távolít el a story_text-ben szereplő azonosítót (no false positives).
- **FR-005**: Az új optimalizált program exportja felülírja az `artifacts/program.json`-t; a szerver restart után az új verziót szolgálja ki.

### Success Criteria

- **SC-001**: A valset-en generált cikkek 0 hallucinált hivatkozást tartalmaznak (guardrail-méréssel).
- **SC-002**: A metric hallucination axis unit tesztjei zöldek (fiktív → büntetés, valódi → nincs büntetés, placeholder → nincs büntetés).
- **SC-003**: A teljes tesztcsomag zöld (208+ teszt + újak).
- **SC-004**: Az éles STRY0010010 újragenerálás után a cikk nem tartalmaz KB0012345/KB0012346 hivatkozást.

## Assumptions

- A story_text az egyetlen megbízható forrás a KB hivatkozásokra; a template_context és a gold dataset nem tekinthető valós adatforrásnak.
- A hallucináció-ellenőrzés regex-alapú (KB + számjegyek); URL-ek és egyéb tényállítások validálása későbbi feature tárgya.
