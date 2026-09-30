# Feature Specification: Komponensnév-hitelesítés az instance ellen + production push-gate

**Feature Branch**: `014-component-instance-verification`

**Created**: 2026-09-30

**Status**: Draft

**Input**: User description: "A generált KB cikkekben előfordulnak olyan ServiceNow rekord-, komponens- vagy mezőnevek, amelyek nem léteznek az adott instance-ben, és a forrás-story alapján sem vezethetők le — az LLM hallucinálta őket. Ezek jelenleg észrevétlenül kerülhetnek ki a publikált cikkekbe, és a cikket olvasó L2/L3 mérnököt tévútra viszik."

## Background (diagnózis)

- **A meglévő védelem story-alapú, nem instance-alapú** (spec 004/011): a metrika azt
  ellenőrzi, hogy a komponensnév szerepel-e a `story_text`-ben. Ez a „Story-ban nincs benne"
  hibaosztályt fedi, de azt nem, hogy a név **létezik-e egyáltalán** az instance-ben —
  a Story maga is tartalmazhat elírt vagy sosem-létrehozott komponensnevet.
- **A production útvonalon nincs komponensnév-gate**: a `strip_hallucinated_references`
  (pipeline.py) csak KB-cikkszámokat szűr push előtt; a komponensnevek ellenőrizetlenül
  kimennek a ServiceNow-ba.
- **A mérőinfrastruktúra megvan** (spec 013 archivált hozadéka, Agent.md §43): JSONL
  recording, replay, kalibrációs metrikák (selective risk / coverage / ECE), ReAnchor
  eval-only wrapper, exit-code-os SC-gate minta. A 014 ezeket újrahasznosítja —
  NEM építünk újat.
- **013-as tanulság beépítve**: az SC-kapukhoz minimális mintaméret tartozik (lásd SC-002);
  a kalibrációs sweep exploratív, nem confirmatory.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Instance-alapú komponensnév-ellenőrzés a metrikában (Priority: P1)

A generált cikkben szereplő nevesített komponensnevek (táblák, mezők, Business Rule-ok,
Script Include-ok stb.) ellenőrzése kiterjed az **instance-valóságra**: a névnek léteznie
kell az adott instance-en (a metaadat-táblákban), nem elég, hogy a Story-ban szerepel.
A metrika a nem-létező neveket nevesítve bünteti.

**Why this priority**: Ez a probléma-állítás maga — a hallucinált nevek ma a metrika
vakfoltján mennek át, ha a Story-ban szerepelnek (vagy a Story maga hibás).

**Independent Test**: Mock instance-metaadat (ismert tábla-/mezőlista) + mock cikk egy
nem-létező táblanévvel → a metrika az instance-tengelyen 0-t ad és nevesíti a nevet;
ugyanaz valós névvel → 1.0.

**Acceptance Scenarios**:

1. **Given** mock instance-metaadat (ismert tábla-/mezőlista) és generált cikk nem-létező
   táblanévvel, **When** az instance-ellenőrzés fut, **Then** a név „nem létezik"
   státuszt kap és nevesítve jelenik meg a riportban.
2. **Given** cikk, amely csak az instance-ben létező neveket tartalmaz, **When** az
   ellenőrzés fut, **Then** minden név „létezik" státuszú, nincs false positive.
3. **Given** az instance-metaadat lekérdezés elérhetetlen, **When** az ellenőrzés fut,
   **Then** fail-open: a vizsgálat kihagyódik warninggal, a pipeline továbbfut (a
   metrika-story-alapú védelem érintetlen marad).
4. **Given** általános terminusok („Business Rule", „Incident"), **When** a cikk
   tartalmazza őket, **Then** NEM számítanak komponensnévnek (a 011-es whitelist-minta).

---

### User Story 2 - Production push-gate a komponensnevekre (Priority: P1)

A pipeline a cikk ServiceNow-ba írása ELŐTT validálja a nevesített komponensneveket az
instance ellen. Nem-létező név esetén a cikk NEM megy ki észrevétlenül: a gyanús nevek
work_notes-jelzést kapnak a mért bizonyossággal (a 013-as minta szerint), és a viselkedés
konfigurálható (jelzés / strip / blokkolás — a default a plan.md Key Decision-je).

**Why this priority**: Defense-in-depth — a metrika az eval-útvonalat védi, ez a gate a
productiont. A probléma-állítás éle („észrevétlenül kerülnek ki") pontosan ezt zárja.

**Independent Test**: Egységteszt: a gate egy nem-létező komponensnevet tartalmazó
cikket jelöl/blokkol a mock instance-lista alapján; valós neveket érintetlenül átenged.

**Acceptance Scenarios**:

1. **Given** cikk nem-létező komponensnévvel, **When** a push-gate fut, **Then** a név
   jelölve/work_notes-ban megnevezve (vagy a konfig szerinti viselkedés), és a napló
   tartalmazza a döntést.
2. **Given** cikk csak valós nevekkel, **When** a gate fut, **Then** a cikk változatlanul
   kimegy, plusz latency elhanyagolható.
3. **Given** az instance-ellenőrzés elérhetetlen, **When** a gate fut, **Then** fail-open:
   a cikk kimegy warninggal (a rendelkezésreállás elsődleges — a 013-as KD4 minta).

---

### User Story 3 - Kalibrált döntés a homályos esetekre (Priority: P2)

A „létezik / nem létezik" tiszta esetei determinisztikusak (pontos névegyezés az
instance-metaadattal). A homályos esetekre (írásvariáns, rövidítés, „ez a megnevezés erre
a valós komponensre utal-e?") kalibrált, típusos döntés készül confidence-szel, replay-
kompatibilis naplózással — a 013-as mérőinfrastruktúra újrahasznosításával.

**Why this priority**: A P1 gate determinisztikus magja önállóan is értéket szállít;
a kalibrált réteg a false positive-okat csökkenti az írásvariánsoknál.

**Independent Test**: Írásvariánssal („JiraIntegrationUtils" vs „Jira Integration Utils")
→ a kalibrált döntés a valós komponenshez rendeli magas confidence-szel; teljesen új név
→ alacsony confidence / „nem létezik".

**Acceptance Scenarios**:

1. **Given** név-írásvariáns, ami valós komponensre utal, **When** a kalibrált döntés fut,
   **Then** „létezik (utalás)" a döntés, magas confidence.
2. **Given** teljesen ismeretlen név, **When** a döntés fut, **Then** alacsony confidence
   vagy „nem létezik", és work_notes-jelzés.
3. **Given** a kalibrációs szolgáltatás kiesik, **When** a gate fut, **Then** fail-open a
   determinisztikus ellenőrzésre.

### Edge Cases

- A név a Story-ban ÉS az instance-ben is szerepel, de mást jelent (ütköző névhasználat) →
  a kalibrált réteg feladata; a determinisztikus út „létezik"-nek veszi.
- Az instance-metaadat lekérdezés részleges (egyes táblatípusok elérhetetlenek) → az érintett
  típusok kihagyódnak warninggal, a többi ellenőrzés él.
- A cikk placeholder-t vagy általános terminusokat tartalmaz → nem komponensnév (011 whitelist).
- Nagyon nagy komponenslista az instance-ben → a spot-check cache frissítési és memória-
  korlátai a plan.md-ben.
- A story-hoz nincs Update Set → a gate csak az instance spot-check rétegig megy
  (whitelist nélkül); a gyakoriságát a Phase 0 leltár méri.
- Küszöb-operátor: a 013-as minta szerint `<` (nem `<=`), a pontos határérték a biztonságos
  irányba dől.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A rendszernek a generált cikkben szereplő nevesített komponensneveket az
  instance-metaadatok ellenében kell validálnia (létezik / nem létezik / homályos).
- **FR-002**: Fail-open kötelező: az instance-lekérdezés vagy a döntési szolgáltatás
  bármilyen hibája esetén a pipeline a meglévő úton fut tovább, warning-naplóval.
- **FR-003**: Minden döntés replay-kompatibilis JSONL-be naplózódik (a 013-as
  recording-formátum újrahasznosítva).
- **FR-004**: A gate a `servicenow_client` írási útja elé kerül; a viselkedés
  (jelzés/strip/blokkolás) configból kapcsolható, a generatív út érintetlen marad.
- **FR-005**: A döntési szolgáltatás modellverziója pinnelt (lebegő alias TILOS).
- **FR-006**: A metrika instance-tengelye visszafelé kompatibilis: a meglévő
  story-alapú ellenőrzés érintetlen marad mellette.

### Key Entities

- **Komponensnév-jelölt**: a cikkből kinyert nevesített entitás (a 011-es kinyerési minta:
  idézett nevek, CamelCase, dotted identifier) + típus-tipp (tábla/mező/script).
- **Ground truth (hierarchikus)**: 1) a story Update Set-jének komponensnevei
  (elsődleges whitelist), 2) per-név spot-check az instance-metaadatokban (cache-elve)
  azokra, amik nincsenek az update setben.
- **Validálási döntés**: jelöltenként {létezik / nem létezik / homályos} + confidence +
  naplózott bizonyíték.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Az instance-tengely nem rontja a meglévő eval-eredményt: a gold cikkeken
  nincs false positive (0/9 false „nem létezik" jelölés a mérés pillanatában érvényes
  metaadat-snapshoton).
- **SC-002**: A kalibrált gate a gold + szándékolt-hibás mintán: selective risk ≤ 0.15 és
  coverage ≥ 0.7 a confirmatory 0.7-es kapunál, **minimum 20 példás címkézett mintán**
  (a 013-as tanulság: mintaméret-minimum kötelező — 9 példán a kapu nem igazolható).
- **SC-003**: Fail-open bizonyított: szimulált instance- és szolgáltatás-kiesésnél a
  pipeline zöld marad (teszt exit-code).
- **SC-004**: Replay-reprodukálhatóság: a mérés kétszeri lefuttatása byte-identikus
  riportot ad (cache-higiénia: `cache=False` vagy replay-mód).

## Assumptions

- Az instance-metaadatok (tábla-/mező-/scriptnevek) API-n lekérdezhetők a PDI-ról, és a
  snapshot mérete kezelhető (cache-elhetó).
- A gold cikkek komponensnevei a mérés időpontjában valódiak (ha egy régi gold név időközben
  törlődött az instance-ből, azt a címkézésnél javítjuk — a 013-as T004 minta).
- A „homályos" esetek aránya kicsi; a döntések többsége determinisztikus.
- A kalibrált réteg (US3) a 013-as archivált infrastruktúrát használja; ha a típusos
  döntési szolgáltatás elérhetetlenné válik, a P1-es determinisztikus mag önállóan is értelmes.

## Out of Scope

- A story-alapú ellenőrzés (004/011) módosítása — az működik, érintetlen.
- A generatív program (program.py / program.json) és a GEPA-program változtatása.
- Hallucináció *megelőzése* a promptokban — ez a spec detektálásról és kapuról szól.
  *(Újraindítási feltétel: ha az SC-002 mérés azt mutatja, hogy a hallucináció-arány a
  kalibrált gatetel is magas, jön a megelőzés-spec.)*
- Nem-ServiceNow entitások (URL-ek, külső rendszerek objektumai) validálása.
  *(Újraindítási feltétel: ha a mérési adat azt mutatja, hogy a kimenő hibák többsége
  ilyen.)*
