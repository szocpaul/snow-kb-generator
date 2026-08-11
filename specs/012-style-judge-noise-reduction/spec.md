# Feature Specification: Style Judge zajcsökkentés (multi-sample pontozás)

**Feature Branch**: `012-style-judge-noise-reduction`

**Created**: 2026-08-11

**Status**: Draft

**Input**: User description: "A kalibráció (2026-08-11) kimutatta: a style tengely 0.188-at szór három AZONOS baseline-futás közben — a style judge egymintás, temperature=0.6-os LLM-hívása a pipeline legnagyobb mérési zajforrása. Emiatt lett a mini-GEPA elhalasztva (spec 011 T009): a várható nyereség (+0.02-0.05) kisebb, mint a zaj. A judge lokális modell (ingyen), tehát a több-mintás átlagolás olcsó megoldás."

## Background (diagnózis)

- **A mérés (Agent.md 32):** 3 azonos baseline-futás tengely-szórásai: hallucination 0.000, template 0.000, structure 0.042, content 0.070, **style 0.188**. A style szórása ~3-4× akkora, mint a többi tengelyé.
- **A zaj forrása:** `_style_score()` (eval/metric.py) EGYETLEN `dspy.Predict(StyleJudge)` hívást ad ki, a globális `temperature=0.6`-os LM-konfiggal. Ugyanaz a cikk futásról futásra más pontot kap.
- **A judge maga jó** (spec 010 SC-002 validáció): a gépies teszt-ikon 0.00, a kézzel írt KB0010015 1.00 — az *átlag* jó helyen van, a *szórás* a baj. Nem judge-csere kell, hanem variancia-csökkentés.
- **Fizika:** n független minta átlagának szórása ≈ σ/√n → 3 minta: ±0.19 → ~±0.11; 5 minta: ~±0.08.
- **Költség-oldal:** a judge lokális (marginális költség nulla), viszont a mérésidő nő: metric call = 1 generálás + N judge-hívás. A baseline-mérés (~10 perc) N=3 mellett ~15-25 perc. Egy jövőbeli GEPA-futás becslését ez módosítja.
- **Miért nem temperature=0?** Egyetlen temp=0-s hívás merevvé teheti a judge-ot (rejtett torzítás), és a clampelési viselkedését sem ismerjük. A spec elsődleges útja a mintavételi átlagolás; a temp=0 tartalék-opció a kalibrációs fázisban.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Multi-sample style pontozás (Priority: P1)

A `_style_score()` N mintát vesz a judge-tól (alapértelmezett `STYLE_JUDGE_SAMPLES = 3`), és a pontszámok **átlagát** adja vissza. Részleges hibatűrés: ha 1-2 hívás elszáll, a megmaradt mintákból számol; ha mind elszáll, a spec 010-es FR-002 viselkedés marad (semleges 0.5 + warning).

**Why this priority**: Ez a zajcsökkentés magja; minden más erre épül.

**Independent Test**: mock judge fix sorozattal ([0.4, 0.6, 0.8] → 0.6); részleges hiba (2 hiba + 1 siker → a sikeres érték); teljes hiba → 0.5.

**Acceptance Scenarios**:

1. **Given** 3 sikeres judge-hívás különböző pontokkal, **When** `_style_score` fut, **Then** a visszaadott pont a 3 érték átlaga (±0.001).
2. **Given** 1-2 sikertelen hívás, **When** a függvény fut, **Then** a sikeres minták átlaga adódik, warning-gal, NEM 0.5.
3. **Given** minden hívás sikertelen, **When** a függvény fut, **Then** (0.5, "") — a meglévő hibatűrés érintetlen.
4. **Given** a critique kiválasztása, **When** több minta készül, **Then** az átlaghoz legközelebbi minta kritikája kerül a feedbackbe (a GEPA reflectionnek egy konkrét, reprezentatív szöveg kell).

---

### User Story 2 - Kalibrációs igazolás (Priority: P2)

A változás után a baseline-t 3-szor újramérjük, és a style tengely szórásának a 0.188-ról **≤ 0.10**-re kell csökkennie. Ha nem teljesül: N=5 vagy temp=0 kiértékelése (döntés a tasks.md-ben dokumentálva).

**Why this priority**: A zajcsökkentés csak akkor létezik, ha mérhetően bekövetkezik — ugyanazzal a módszerrel, amivel a problémát kimutattuk.

**Independent Test**: 3 azonos baseline-futás (`cache=False`) → tengelyenkénti szórás-táblázat; a style-szórás a célérték alatt.

**Acceptance Scenarios**:

1. **Given** a multi-sample judge, **When** a baseline 3-szor lefut, **Then** a style min–max szórás ≤ 0.10.
2. **Given** a kalibráció, **When** a judge validációja megismétlődik, **Then** a gépies teszt-ikon < 0.4 és a KB0010015-referencia > 0.7 (a diszkrimináció nem romlott).
3. **Given** az új baseline-átlagok, **When** dokumentálás történik, **Then** az új referencia rögzítve (a korábbiak elavultként).

---

### User Story 3 - Mini-GEPA döntés újraértékelése (Priority: P3)

A spec 011 T009-ben elhalasztott mini-GEPA kérdésének újrafeltevése a mért (csökkentett) zajszint mellett. A döntés az emberé; a spec csak a számokat szolgáltatja.

**Why this priority**: A spec 012 valós célja — nem a judge-javítás önmagában, hanem hogy az optimalizációs eredmények újra értelmezhetők legyenek.

**Independent Test**: a tasks.md tartalmazza a számszerű újraértékelést (mért szórás vs mini-GEPA várható nyereség).

**Acceptance Scenarios**:

1. **Given** a mért új szórás, **When** a döntés-előkészítés készül, **Then** explicit szerepel: "javulás > mért szórás + marge" formában az értelmezhetőségi küszöb.
2. **Given** az újraértékelés, **When** az ember dönt, **Then** a döntés és indoklás a tasks.md-ben rögzült.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A részleges hibatűrés megmarad: 1-2 sikertelen judge-hívás nem eredményezhet semleges 0.5-öt, ha van sikeres minta (különben a hibatűrés maga zajforrássá válna — pont ellentétes irány).
- **FR-002**: `STYLE_JUDGE_SAMPLES` konfigurálható konstans az `eval/metric.py`-ben (alapértelmezett 3); a tesztek felüldefiniálhatják.
- **FR-003**: A többi tengely, a súlyok (0.25/0.25/0.15/0.15/0.20) és a feedback-formátum változatlan. A critique az átlaghoz legközelebbi mintáé.
- **FR-004**: Minden mérés `cache=False`-szal (spec 010 cache-higiénia); a multi-sample hívások sem jöhetnek disk-cache-ből.
- **FR-005**: A judge validációja (spec 010 SC-002) a változás után is teljesüljön: gépies < 0.4, emberi > 0.7.

### Success Criteria

- **SC-001**: `_style_score` = N sikeres minta átlaga; részleges hiba kezelve; mind-hiba → 0.5 (mock tesztek).
- **SC-002**: 3 azonos baseline-futáson a style szórás ≤ 0.10 (a 0.188-ról).
- **SC-003**: A judge diszkriminációja változatlan (gépies < 0.4, KB0010015 > 0.7).
- **SC-004**: A mini-GEPA újraértékelés számszerűen dokumentált; az emberi döntés rögzített.

## Out of Scope

- GEPA futtatás (bármilyen méretben) — a spec 012 csak a mérést javítja.
- Valset-bővítés (a zajcsökkentés másik útja) — külön döntés, külön spec ha kell.
- Judge-modell csere (a lokális Qwen judge marad; az önértékelés-kompromisszum változatlan).
- A judge-hívások párhuzamosítása (async) — mérésidő-optimalizálás, csak ha a kalibráció során probléma lenne.
- Produkciós pipeline (server.py, pipeline.py, program.json) — érintetlen.
