# Feature Specification: Aszimmetrikus kalibráció + gate-emelés az írást végző komponensbe

**Feature Branch**: `015-asymmetric-verification-gate`

**Created**: 2026-10-01

**Status**: Draft

**Input**: User description: "A verification gate jelenleg úgy kezeli a téves „létező" és a téves „nem létező" jelöléseket, mintha ugyanolyan súlyúak lennének — pedig egy átsikló hallucinált név tévútra viszi a cikket olvasó mérnököt, míg egy felesleges jelzés legfeljebb zaj. Emellett a kapu a pipeline-rétegben él, nem magában az írást végző komponensben, így egy jövőbeli másik hívási út azt kikerülheti."

## Background (diagnózis)

- **A 014-es gate működik** (SC-002 ZÖLD n=24-en, flag módban productionben), de a
  kalibrációs metrika **szimmetrikus**: mindkét hibafajta ugyanannyiba „kerül". A
  valóságban a téves „létező" (hallucinált név átmegy) sokkal drágább, mint a téves
  „nem létező" (felesleges jelzés) — a threshold ezért nem biztos, hogy a valós
  költséget minimalizálja.
- **A gate a pipeline-rétegben él** (`_apply_verification_gate` a `create_kb_article`
  hívása előtt), nem az írást végző kliensben — egy jövőbeli másik hívási út
  (CLI, másik endpoint) kikerülhetné. A referencia-minta (cmpnd-ai v1 permission
  gate): a kapu a tool BELSÉJÉBEN él, „semmi, amit a hívó ír, nem kerülheti meg".
- **Az aldidev-minták nem használhatók instance-mérésre** (céges policy: áthozni
  nem lehet) — a 014-es SC-001 PIROS nagy része ebből fakadt. A kalibrációs minta
  ezért egy **új, a PDI-n natívan létező** story+update set fixture-re épül (a
  snow-kb-generator projekt maga mint integrációs projekt), ahol a ground truth
  tiszta. Ez egyben a 011-es dataset-hézagot is foltozza (update set-es gold példa).
- **A 013/014-es infrastruktúra újrahasznosul**: recording, replay, jev-metrics,
  ReAnchor eval-only wrapper, SC-gate minta — újat nem építünk.
- Tanulság-halmozás: min. mintaméret az SC-kapukhoz (013), exploratív ≠ confirmatory
  (013/014), küszöb-operátor `<` (013).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PDI-natív story+update set fixture (Priority: P1)

A snow-kb-generator projektről (mint integrációs projektről) egy valódi Story készül
a PDI-n, hozzá egy Update Set, amely a PDI-n TÉNYLEGESEN létező komponenseket
tartalmazza. Ez a kalibrációs minta ground truth-ja: a „létező" címkék az instance
valóságából jönnek, az írásvariáns- és fabrikált példák ebből gépiesen származnak.

**Why this priority**: Blokkoló előfeltétel — a jelenlegi 24 példás minta nagy része
az aldidev↔PDI eltérés artefaktja; tiszta kalibráció csak PDI-natív mintán értelmes.

**Independent Test**: a fixture létrehozása után egy ellenőrző script igazolja, hogy
a story update set-jében szereplő MINDEN komponensnév spot-checkkel „létezik" a PDI-n.

**Acceptance Scenarios**:

1. **Given** az új Story + Update Set a PDI-n, **When** a spot-check az update set
   komponensneveire fut, **Then** mindegyik „létezik" (0 not_found).
2. **Given** a fixture-ből származtatott címkézett minta (valós nevek + írásvariánsok
   + fabrikált nevek), **When** a címkék review-zásra kerülnek, **Then** minden címke
   az instance-tényből levezethető.
3. **Given** a bővített dataset, **When** a dataset loader fut, **Then** az új példa
   a 011-es formátumnak megfelel (story + update_set_payloads + gold cikk-vázlat).

---

### User Story 2 - Aszimmetrikus költségű kalibráció (Priority: P1)

A kalibrációs metrika a hibafajtákat a valós költségük szerint súlyozza: a téves
„létező" (átsikló hallucináció) többszörösen drágább, mint a téves „nem létező"
(felesleges jelzés). A ReAnchor ezzel a metrikával hangolja a thresholdot a
PDI-natív mintán; a kijött küszöb a korábbi szimmetrikus eredménnyel szembeállítva,
indoklással kerül a configba (vagy marad, ha nem veri a fold-eken — a referencia-minta
viselkedése).

**Why this priority**: Ez a probléma-állítás első fele — a gate jelenleg nem a valós
költséget minimalizálja.

**Independent Test**: a kalibrációs futás riportja mutassa a szimmetrikus vs
aszimmetrikus metrikával mért költséget ugyanazon a mintán, és a threshold-változás
(vagy -maradás) indoklása fájlba kerüljön.

**Acceptance Scenarios**:

1. **Given** a PDI-natív címkézett minta, **When** a kalibráció aszimmetrikus
   metrikával fut, **Then** a riport tartalmazza: threshold előtt/utána,
   költség előtt/utána, és az összevetést a szimmetrikus metrikával.
2. **Given** a kalibráció nem talál jobb küszöböt, **When** a riport készül,
   **Then** a threshold marad + az indoklás fájlba írva (nem „csendes maradás").
3. **Given** az új threshold a configban, **When** a production hívás fut,
   **Then** a közvetlen SDK-út azt olvassa (a ReAnchor-wrapper továbbra is csak
   mérés — 013/014 minta).

---

### User Story 3 - A gate az írást végző komponensbe emelése (Priority: P2)

A verification gate a `servicenow_client` írási útjába költözik (a `_create_kb_article_live`
belsejébe), hogy MINDEN hívási út — jelenlegi és jövőbeli — ugyanazon a kapun menjen
keresztül. A pipeline-rétegű hívás megszűnik (dupla védelem helyett egyetlen,
megkerülhetetlen pont).

**Why this priority**: Védelem-architektúra kérdés; a funkcionális viselkedés ma már
működik, ez a „nem kerülhető meg" garancia.

**Independent Test**: teszt, ami a klienst KÖZVETLENÜL hívja (a pipeline-t megkerülve)
→ a gate így is lefut; és egy teszt, ami igazolja, hogy a pipeline-rétegű hívás
megszűnt (nincs dupla ellenőrzés + dupla recording).

**Acceptance Scenarios**:

1. **Given** közvetlen `_create_kb_article_live` hívás nem-létező névvel, **When** a
   kliens fut, **Then** a gate lefut (flag: work_notes-jelzés), a pipeline-réteg
   nélkül is.
2. **Given** normál pipeline-futás, **When** a cikk íródik, **Then** pontosan EGY
   gate-döntés és EGY JSONL-bejegyzés keletkezik.
3. **Given** instance-kiesés, **When** a kliens-beli gate fut, **Then** fail-open a
   meglévő módon (warning + a cikk kimegy).

### Edge Cases

- A kalibrált réteg thresholdja megváltozik → a meglévő 24 példás mintán is újra kell
  mérni a viselkedésváltozást (regresszió-riport), nem csak az új mintán.
- A fixture update set-jébe kerülő komponensek a PDI-frissítéskor törlődhetnek → a
  fixture-ellenőrző script (US1) a mérés előtt mindig lefut; ha hiányzik komponens,
  a mérés megáll (nem improvizál).
- Küszöb-operátor: `<` (nem `<=`) — a 013-as minta.
- A kalibráció CSAK a `confidence_threshold`-ot hangolja: a fail-open és a flag-only
  alapviselkedés kézzel beállított „safety floor", kalibrációval nem mozgatható
  (a fit_thresholds.py minta: DENY_BELOW kézzel marad — „one mistake that no other
  example repeats is not enough to move it").
- A gate-emelés során az in-flight cikkek: a restart pillanatában futó kérések a régi
  úton fejeződnek be (deploy-megjegyzés, nem funkcionális követelmény).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A kalibrációs metrika aszimmetrikus költségeket használ; a súlyarány
  (pl. 10:1) a plan.md Key Decision-je, nem hard-coded „véletlen" érték.
- **FR-002**: A kalibrációs minta PDI-natív fixture-ből származik (US1); az
  aldidev-eredetű nevek NEM kerülnek „létezik" címkével a PDI-mérésbe.
- **FR-003**: A threshold-változás (vagy -maradás) indoklása fájlba íródik, a
  szimmetrikus metrikás ellenértékkel együtt.
- **FR-004**: A gate a `servicenow_client` írási útjába költözik; minden cikk-írás
  (pipeline, CLI, jövőbeli út) ezen megy keresztül; dupla védelem/dupla recording TILOS.
- **FR-005**: Fail-open változatlan (instance/TypeSafe-kiesés → cikk kimegy warninggal).
- **FR-006**: A 004/011 story-alapú ellenőrzés és a production közvetlen SDK-hívás
  érintetlen; a ReAnchor-wrapper csak mérés.

### Key Entities

- **PDI fixture**: Story + Update Set + a benne lévő valós komponensnevek listája
  (a kalibráció ground truth-ja).
- **Költség-súlyozott metrika**: a téves „létező" és téves „nem létező" explicit
  költségével (aránya Key Decision).
- **Kalibrációs riport**: threshold előtt/utána, költség előtt/utána, szimmetrikus
  összevetés, indoklás — fájlban, nem chatben.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A fixture-integritás igazolt: az update set MINDEN komponensneve
  spot-checkkel „létezik" a PDI-n (0/0 eltérés), exit-code-os scripttel, a mérés előtt.
- **SC-002**: A kalibrációs riport a PDI-natív mintán (a meglévő 24 + az új
  fixture-példák, összesen ≥30): az aszimmetrikus metrikával mért összköltség
  NEM ROSSZABB, mint a szimmetrikusé; a threshold-döntés (változás vagy maradás)
  indoklása a riportban.
- **SC-003**: Regresszió a meglévő mintán: az új kalibrációval a 24 példás minta
  eredménye fájlba írva és összevetve a 014-es baseline-nal — romlás esetén a
  riport PIROS és a threshold nem lép életbe.
- **SC-004**: Gate-emelés igazolva: a közvetlen kliens-hívás is gated (teszt),
  és a pipeline-futásban pontosan 1 gate-döntés + 1 recording-bejegyzés (teszt).
- **SC-005**: Replay-reprodukálhatóság: a kalibrációs mérés kétszeri lefuttatása
  byte-identikus riport (cache-higiénia, 013/014 minta).

## Assumptions

- A PDI-n van admin jogú user → a metaadat-lekérdezés jogosultsági vakfoltja nem
  releváns (a 014-es 4-es mechanizmus kizárva).
- A fixture-komponensek a PDI élettartama alatt megmaradnak; ha a PDI újraépül,
  a fixture újralétrehozása a bootstrap része.
- A deploy (gate-emelés) külön, ember által irányított lépés — nem a runner végzi.

## Out of Scope

- A behavior szigorítása (flag → strip/block) — az a megfigyelési időszak adataiból
  születő külön döntés. *(Újraindítási feltétel: a JSONL-statisztika azt mutatja,
  hogy a flag-zaj elhanyagolható ÉS a valós találatok aránya igazolja a szigorítást.)*
- Az aldidev-minták „megmentése" bármilyen formában — a céges policy ezt kizárja,
  a fixture (US1) váltja fel őket mérési szempontból.
- A 013-as archivált audience-feature újraaktiválása.
- A kalibrációs minta további bővítése a ≥30 példa fölé. *(Újraindítási feltétel:
  ha az SC-002-szerű kapuk a ≥30-as mintán is instabilnak bizonyulnak.)*
