# Implementation Plan: Aszimmetrikus kalibráció + gate-emelés az írást végző komponensbe

**Branch**: `015-asymmetric-verification-gate` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-asymmetric-verification-gate/spec.md`

## Summary

Két fókuszált változás a 014-es verification gate-en: (1) a kalibráció aszimmetrikus
költségű metrikára áll át (a téves „létező" többszörösen drágább), PDI-natív
fixture-mintán; (2) a gate a `servicenow_client` írási útjába költözik, hogy minden
hívási út egyetlen, megkerülhetetlen kapun menjen keresztül. A 013/014-es
mérőinfrastruktúra változatlanul újrahasznosul.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: változatlan (typesafe-sdk + dspy[typesafe] már a projektben);
a fixture-létrehozás a meglévő `servicenow_client` table-API-n + `scripts_pdi/` mintán

**Storage**: PDI fixture (Story + Update Set, instance-oldali), címkézett minta a
`data/examples/` alatt, spot-check cache + JSONL recording (meglévő)

**Testing**: pytest (349-es suite zöld marad + új tesztek)

**Target Platform**: Linux VPS, systemd-managed FastAPI szolgáltatás + PDI

**Performance Goals**: a gate-emelés nem ad plusz latency-t (a hívás ugyanaz, csak
máshol él); a kalibráció offline, egy trainset-lefuttatás (ReAnchor)

**Constraints**: fail-open változatlan (FR-005); a safety floor (fail-open +
flag-only alapviselkedés) kalibrációval NEM mozgatható (spec Edge Cases);
SC-003 regresszió-gate a meglévő 24 példás mintán

**Scale/Scope**: ~3 érintett fájl (`verification.py`, `servicenow_client.py`,
`pipeline.py`) + eval-kiegészítés + tesztek + fixture-script

## Constitution Check

*GATE: formális constitution továbbra sincs — az ellenőrzés az Agent.md implicit
elvei alapján.*

| Elv (implicit) | Ellenőrzés |
|---|---|
| „Measured, not claimed" | ✅ — SC-002/SC-003 számszerűek, riport fájlba |
| Fail-open | ✅ — FR-005 változatlan, tesztelve (SC-004 minta) |
| Baseline-előbb | ✅ — Phase 0: fixture + a jelenlegi threshold aszimmetrikus költsége rögzítve |
| Meglévő védelem érintetlen | ✅ — FR-006 |
| Visszafelé kompatibilitás | ✅ — SC-003: romlás esetén a threshold nem lép életbe |

## Architecture

```text
JELENLEG (014)                          CÉL (015)
─────────────                           ─────────
pipeline.py                             pipeline.py
  └ _apply_verification_gate()            └ (gate-hívás megszűnik)
  └ create_kb_article()                   └ create_kb_article()
       └ _live: írás                           └ _live: GATE ITT (belsejében)
                                                       → flag/strip/block
                                                       → 1 döntés, 1 recording
Más (jövőbeli) hívási út → gate NÉLKÜL   Más hívási út → ugyanazon a kapun át
```

Kalibráció (offline, a mérés része — productiontől elválasztva):

```text
PDI fixture (Story + Update Set, valós komponensek)
   → címkézett minta (valós / írásvariáns / fabrikált)
   → ReAnchor ASZIMMETRIKUS metrikával (FALSE_POS_EXISTS_COST : FALSE_NEG_COST)
   → threshold-riport (előtt/utána, szimmetrikus összevetés, indoklás fájlba)
   → config.confidence_threshold (vagy marad + indoklás)
   → regresszió: meglévő 24 példás minta újramérve (SC-003)
```

## Key Decisions

1. **A költség-arány: 10:1** (téves „létező" : téves „nem létező") — a referencia-minta
   (fit_thresholds.py) értéke, és a mi domainünkben is védi: az átsikló hallucináció
   tévútra viszi az olvasót, a felesleges jelzés zaj. (Alternatíva: 5:1 vagy 20:1 —
   a pontos arány a kalibrációs riportban érzékenység-analízissel alátámasztandó;
   ha a threshold az arányra érzéketlen, a legegyszerűbb 10:1 marad.)
2. **A fixture a PDI-n készül, scripttel** (`scripts_pdi/` mintára): Story + Update Set
   + a PDI-n létező komponensek regisztrálása — reprodukálható, PDI-újraépítés esetén
   újrafuttatható. (Alternatíva: kézi fixture — elvetve, nem reprodukálható.)
3. **A gate a `_create_kb_article_live` belsejébe költözik** (nem wrapper, nem decorator):
   a hívás egyetlen belépési pontja tartalmazza. A pipeline-rétegű hívás törlődik.
   (Alternatíva: decorator a clienten — elvetve, az aláíráson kívüli varázslat;
   a v1 minta „a tool belsejében" elve szerinti legtisztább alak a belső hívás.)
4. **A kalibráció csak a `confidence_threshold`-ot hangolja** — a fail-open és a
   flag-only alapviselkedés kézzel beállított safety floor (spec Edge Cases).
   (A referencia-minta is így: DENY_BELOW kézzel marad.)
5. **Regresszió-gate a meglévő mintán (SC-003)** — az új threshold csak akkor lép
   életbe, ha a 24 példás mintán nem ront. (Alternatíva: csak az új mintán mérni —
   elvetve, a régi minta a production-viselkedés egyetlen hosszabb múltú tanúja.)
6. **A 24 + fixture-példák egyesített mintán megy a kalibráció**, de az aldidev-eredetű
   „létezik" címkék kizárva a PDI-mérésből (FR-002) — azokat az instance-tények nem
   támasztják alá. (Ez a 014-es SC-001 PIROS tudatos lezárása.)

## Fixture-tartalom (KD2 részlete — a 2026-10-01-i megbeszélés alapján)

**A Story témája**: a snow-kb-generator projekt maga, mint integrációs projekt —
„ServiceNow oldali webhook-fogadás és KB-draft-generálás bekötése". A story-szöveg
a valós projekthez hasonló felépítésű (problem, change summary, érintett komponensek).

**Az Update Set tartalma**: a PDI-n **MÁR MEGLEVŐ** komponensek kerülnek bele
(update set capture meglévő rekordokra — semmit nem hozunk létre újonnan). A
fixture-script a `scripts_pdi/` mintára 4–6 meglévő komponenst választ ki típusonként
(pl. egy Script Include, egy Business Rule, egy System Property, egy tábla-mező),
capture-öli őket egy Update Set-be, és a Story-szöveg ezekre a valós nevekre
hivatkozik. (Alternatíva: új, projektjellegű komponensek létrehozása — ELVETVE,
a programozott Scripted REST/Business Rule-gyártás felesleges kockázat; a nevek
„projektjellege" kozmetika, nem mérési érték.)

**A komponensnevek nem hard-codedek**: a fixture-script az első futáskor dumpolja a
kiválasztott neveket egy artifact-fájlba → emberi pillantás (MANUÁLIS KAPU a
tasks.md-ben), mielőtt a minta-építés rájuk támaszkodik. PDI-újraépítésnél a gyári
komponensek minden friss PDI-n megvannak → a fixture újrafuttatható.

**A komponens-felfedezés mechanizmusa** (nem találgatás): a fixture-script a PDI
metaadat-tábláit kérdezi le a meglévő table-API kliensen (`sys_script_include`,
`sys_script`, `sys_properties`, `sys_dictionary` — `active=true`, `global` scope,
név-szűrés, `sys_updated_on` preferencia). Kiválasztási szempontok: aktív, globális
scope, „rendes" azonosító-név, típus-diverzitás. **A logika fordított**: a script
előbb lekéri a valós neveket, és a Story-szöveg EZEKRE íródik meg — így garantált,
hogy minden story-beli név létezik a PDI-n (ez a fixture értelme).

**A címkézett minta származtatása** a dumpolt név-halmazból:
- **valós**: a kiválasztott komponensnevek pontos alakja
- **írásvariáns**: gépi variánsok (szóközös/kötőjeles/eltérő kisbetű-nagybetű
  alakok) — a 2-es mechanizmus tesztelésére
- **fabrikált**: valóságosnak tűnő, de nem létező nevek — a hallucináció-osztály
- **típus-eltérés**: valós név, rossz táblában keresve (pl. a Script Include neve
  Business Rule-ként keresve) — a 3-as mechanizmus tesztelésére

## Phases

1. **Phase 0 – Fixture + baseline**: a PDI-natív Story + Update Set létrehozása
   scripttel; fixture-integritás gate (SC-001); a jelenlegi threshold (0.7)
   aszimmetrikus költsége rögzítve a meglévő 24 példán (baseline-előbb).
2. **Phase 1 (US1)**: címkézett minta építése a fixture-ből (valós / írásvariáns /
   fabrikált, gépies származtatással), címkék commitolva.
3. **Phase 2 (US2)**: aszimmetrikus metrika + ReAnchor-futás + riport
   (threshold döntés + indoklás + regresszió a régi mintán).
4. **Phase 3 (US3)**: gate-emelés a kliensbe + tesztek (közvetlen hívás is gated;
   nincs dupla döntés/recording) + deploy-megjegyzés a deploy/README-be.
5. **Phase 4 – Zárás**: SC-001..SC-005 gate-ek exit-code-dal, Agent.md, backlog.

## Complexity Tracking

Nincs constitution-violation — a tábla üresen marad.
