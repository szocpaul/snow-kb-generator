# Feature Specification: Kontextus-válogatás a cikkgeneráláshoz

**Feature Branch**: `016-context-selection`

**Created**: 2026-10-02

**Status**: Draft

**Input**: User description: "A cikkgenerálás ma a teljes story-szöveget, az összes update set XML-t és az összes kapcsolódó KB-cikket változatlanul kapja meg kontextusként — ezek egy része zaj, ami feleslegesen növeli a költséget és a hallucinációs lehetőségeket (ami nincs a kontextusban, azt a modell nem másolhatja be tévesen), és a releváns részek is elveszhetnek a tömegben."

## Background (diagnózis)

- **A pipeline ma „minden be"**: a GenerateKb a teljes story + update set XML-ek +
  kapcsolódó cikkek nyers együttesét kapja. A zaj két kárt okoz: token-költség
  (minden futásnál) és hallucinációs felület (a 004/011/014-es specek sorozata
  bizonyítja, hogy a kontextusban lévő zaj a cikkbe szivároghat).
- **A mérőinfrastruktúra teljes**: recording, replay, jev-metrics, ReAnchor
  eval-only wrapper, SC-gate minta, rich_metric a minőség-méréshez — a 016
  ezeket újrahasznosítja.
- **Tanulság-halmozás**: aszimmetrikus költség (015 — itt is releváns: a releváns
  kontextus elrejtése drágább, mint a zaj mutatása); safety floor kézzel (015);
  min. mintaméret az SC-kapukhoz (013); a kinyerő/kontextus-változás recall-védelemmel
  (014: a valós jelöltek nem eshetnek ki).
- **A kinyerő-finomítás kész** (fix/extractor-refinement): a false candidate-ek
  4→0, recall 21/21 — a 016 rá épül, nem fedi át.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Kontextus-darabok minősítése a generálás előtt (Priority: P1)

A generálás előtt minden kontextus-darab (story-szekciók, update set rekordok,
kapcsolódó KB-cikkek) egy zárt, háromállású minősítést kap: **elrejteni /
összefoglalni / változatlanul bekerül**. A minősítés kalibrált, típusos döntés
(confidence-szel, pinnelt modellel); a végrehajtás plain Python policy
(küszöbök kézzel/configból); minden döntés replay-kompatibilis JSONL-be naplózódik.
Alacsony confidence vagy hiba esetén a darab **változatlanul bekerül** (fail-open
a jelenlegi viselkedésre).

**Why this priority**: Ez a probléma-állítás maga — a zaj kiszorítása a költség-
és hallucináció-csökkentés motorja.

**Independent Test**: mock kontextus-darabokkal (nyilvánvalóan releváns update set
rekord vs. boilerplate XML-részlet) → a releváns „show"/„summarize", a zaj „hide";
hiba esetén minden darab bekerül (fail-open).

**Acceptance Scenarios**:

1. **Given** egy nyilvánvalóan irreleváns kontextus-darab (pl. üres/boilerplate
   update set rekord), **When** a válogatás fut, **Then** „hide" vagy „summarize"
   a minősítés, és a generáló promptba nem kerül be változatlanul.
2. **Given** a változás tényleges tartalmát hordozó rekord, **When** a válogatás
   fut, **Then** „show" és változatlanul bekerül.
3. **Given** a döntési szolgáltatás kiesik, **When** a pipeline fut, **Then**
   minden darab változatlanul bekerül (fail-open), warning-naplóval.
4. **Given** alacsony confidence a küszöb alatt, **When** a policy értékel,
   **Then** a darab „show" (a biztonságos irányba dől — recall-védelem).

---

### User Story 2 - A válogatás hatásának mérése (Priority: P1)

A válogatás hatása mérve: token-költség-delta és minőség-delta (rich_metric) a
gold példákon, baseline-előbb szabállyal, replay-kompatibilisen. A minőség NEM
romolhat; a költség-csökkenés legyen számszerű és indokolt.

**Why this priority**: „Measured, not claimed" — a feature csak akkor ér valamit,
ha a zaj-csökkentés minőség-romlás nélkül megy végbe.

**Independent Test**: a gold példákon baseline (válogatás nélkül) vs válogatással
mért token- és minőség-számok összevetve, fájlba írva.

**Acceptance Scenarios**:

1. **Given** a gold példák, **When** baseline és válogatott futás is lemegy,
   **Then** a riport tartalmazza per-példa és összesített token-deltát és
   rich_metric-deltát.
2. **Given** a válogatás bekapcsolva, **When** a rich_metric fut a kimeneteken,
   **Then** az összesített minőség nem rosszabb a baseline-nál a zaj-sávon túl
   (a 013/014-es nem-átfedő-intervallum szabály).
3. **Given** a mérés kétszer fut replay-módban, **Then** byte-identikus riport.

---

### User Story 3 - Kalibráció a hide/show küszöbre (Priority: P2)

A „hide" döntés küszöbe kalibrált (ReAnchor, eval-only wrapper, a 014/015 minta):
a metrika aszimmetrikus — a releváns darab elrejtése (recall-hiba) többszörösen
drágább, mint a zaj mutatása (precízió-hiba). A safety floor (fail-open = „show")
kalibrációval nem mozgatható.

**Why this priority**: Az US1 működik kézzel tippelt küszözzel is; a kalibráció
azt igazolja vagy javítja — mint a 015-ben.

**Independent Test**: címkézett minta (releváns/zaj darabok) + ReAnchor-futás +
riport; a „küszöb marad" ág is fájlba írt eredmény.

**Acceptance Scenarios**:

1. **Given** címkézett kontextus-minta (min. 20 darab, a 013-as tanulság),
   **When** a kalibráció fut, **Then** a riport a küszöb előtt/utána értéket és
   az aszimmetrikus költséget mutatja.
2. **Given** a kalibráció nem talál jobb küszöböt, **Then** az marad + indoklás
   fájlba (nem csendes maradás).
3. **Given** romlás a gold-baseline-on, **Then** a küszöb nem lép életbe
   (regresszió-gate, a 015-ös SC-003 minta).

### Edge Cases

- Minden darab „hide" lenne → a generálás minimal-kontextussal fut? Nem: a
  story-szöveg maga SOHA nem rejthető el (csak szekcionálva minősíthető); legalább
  a story-törzs mindig bekerül.
- A „summarize" összefoglaló hibázik/hallucinál → az összefoglaló olcsó lokális
  modellel készül; a hallucináció-kockázatot a gate (014) a cikk-kimeneten fogja.
- A válogatás lassítja a pipeline-t (plusz döntési hívások) → a döntési modell
  gyors (System One), a latency-költség a token-megtakarítással szemben mérve.
- Küszöb-operátor `<`; a safety floor (fail-open = „show") kalibrációval NEM
  mozgatható (a 015-ös minta).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Minden kontextus-darab zárt háromállású minősítést kap a generálás
  előtt; a minősítés kalibrált, pinnelt modellel, confidence-szel.
- **FR-002**: Fail-open kötelező: hiba vagy alacsony confidence esetén a darab
  változatlanul bekerül (a jelenlegi viselkedés a biztonságos alap).
- **FR-003**: Minden minősítés replay-kompatibilis JSONL-be naplózódik (a 013-as
  recording-formátum).
- **FR-004**: A story-főtörzs sosem rejthető el (legfeljebb szekcionálva
  minősíthető).
- **FR-005**: A minőség-mérés baseline-előbb, a meglévő rich_metric-tel,
  replay-reprodukálhatóan; a gate (014) és a kinyerő (§46/47) érintetlen.
- **FR-006**: A válogatás configból kikapcsolható (a 013/014-es flag-minta).

### Key Entities

- **Kontextus-darab**: a generálás bemenetének egy egysége (story-szekció /
  update set rekord / kapcsolódó cikk) + forrás-típus.
- **Minősítés**: {hide / summarize / show} + confidence + naplózott bizonyíték.
- **Válogatási riport**: per-példa és összesített token- és minőség-delta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Költség: a válogatott futás token-felhasználása számszerűen
  kisebb a baseline-nál a gold példákon (a célérték a plan.md-ben, a baseline
  mérése után rögzítve — ne léggombokból).
- **SC-002**: Minőség-védelem: az összesített rich_metric NEM rosszabb a
  baseline-nál nem-átfedő zaj-intervallumon túl (a 013/014-es szabály).
- **SC-003**: Recall-védelem: a válogatott prompt továbbra is tartalmazza a
  gold cikkek által hivatkozott valós komponensneveket (0/9 kiesés, exit-code-os
  teszt — a kinyerő-finomítás recall-mintája).
- **SC-004**: Fail-open bizonyított: szimulált kiesésnél a pipeline változatlan
  kontextussal fut (teszt).
- **SC-005**: Replay: a mérés kétszeri lefuttatása byte-identikus riport.
- **SC-006** (kalibráció): a hide/show küszöb döntése (változás vagy maradás)
  indoklással fájlba, min. 20 címkézett darabon (a 013-as mintaméret-tanulság).

## Assumptions

- A kontextus-darabok felbonthatók anélkül, hogy a generáló prompt-szerkezet
  összeomlana (a template szekcionált — a 006-os spec óta).
- A lokális dev-modell (Qwen3.8-27B) elég a „summarize" összefoglalókhoz.
- A gold példák kontextusában van valódi zaj (a Phase 0 baseline igazolja —
  ha nincs mérhető zaj, a spec itt megállhat, a 014-es „0 találat" minta szerint).

## Out of Scope

- A generatív program (program.py / program.json) és a GEPA-program változtatása.
  *(Újraindítási feltétel: ha az US2 mérés azt mutatja, hogy a válogatás a
  prompt-struktúra módosítása nélkül nem ad javulást.)*
- A kapcsolódó-cikk keresés (search_kb_articles) javítása — az a recall oldala,
  ez a spec a már megtalált darabok válogatása.
  *(Újraindítási feltétel: ha a válogatás után a darabok SZÁMA a szűk keresztmetszet.)*
- A „summarize" minőségének finomhangolása (prompt-hangolás) — első körben
  egyszerű összefoglaló; a minőség az SC-002-n mérik.
- A threshold-újramérés a 015-ös gate-en (T009 feltétel) — az külön kör, a
  megfigyelési időszak adataiból.
