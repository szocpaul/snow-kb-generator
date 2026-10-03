# T012 MANUÁLIS KAPU — spec 016 kalibrációs riport review

**Dátum**: 2026-10-02 (runner)
**Állapot**: VÁRAKOZIK emberi döntésre — a runner MEGÁLLT.

## A kapu tárgya (tasks.md T012)

A kalibrációs riport review-ja; küszöb-módosítás jóváhagyása + indoklás az
Agent.md-be. A küszöb CSAK emberi jóváhagyás után kerülhet a configba. A T009
kapu döntése szerint a PLAFON-SZÁM alapján: célérték-revízió, rubrika-
újratervezés (a spec újraindítási feltétele) vagy megállás.

## 1. A labeled-minta sweep-je (56 darab, EXPLORATÍV)

- Jelenlegi küszöb (hide_below=0.25): aszimmetrikus költség **16.5** (5:1).
- Legjobb jelölt: **0.05**, költség **16.0** — a javulás EGYETLEN borderline
  darab verdict-fluktuációja, nem valódi szeparációs nyereség.
- Recall-hiba (releváns elrejtve): **0** mindkét küszöbnél; a költség teljes
  egésze borderline verdict-mismatch.
- Ratio-érzékenység: 3:1 / 5:1 / 10:1 — **azonos** (16.5 / 16.5 / 16.5 →
  16.0 / 16.0 / 16.0): nincs releváns-elrejtés a költségben, az arány nem mozgat.
- ReAnchor (eval-only wrapper): train score **−0.2946 → −0.2946** — a kalibráció
  nem talált javítást.

**Runner-álláspont**: a küszöb **MARADJON 0.25** — a 0.05-ös „javulás" zajszintű,
a config-módosítás nem indokolt (a „küszöb marad" ág a riportban fájlba írva).

## 2. A plafon-számok (a T009 kapu által követelt táblázat)

| Nézet | Max megtakarítás | Teljes prompton | SC-001 (1878 t / 5%) |
|---|---|---|---|
| Nyers plafon (hide_below-sweep, production probék) | 4161 t | **11.1%** | eléri (de a labeled költség szerint tilos zóna) |
| **Költség-korlátos plafon** (labeled költség ≤ jelenlegi) | **0 t** | **0.0%** | NEM éri el |
| Context-free becslés (state-fix után, ld. §3) | 428–450 t | **~1.1–1.2%** | NEM éri el |

## 3. Gyökéroka-megállapítás (a legfontosabb fun)

A production `_score_piece` a `story_context`-et (core-szöveg, 2000 kar.) is
elküldi a state-ben. **Ez a mező FELFÚJJA a Score-t**: az azonos zaj-darabok
(number/state/assigned_to/assignment_group) story_context-TEL 0.86–0.99
relevanciát kapnak (→ sosem hide), story_context NÉLKÜL 0.00–0.03-at,
0.93–1.00 confidence-szel (→ tiszta szeparáció). A releváns update set
rekordok mindkét feltételnél 0.95 körül vannak. (56/56 darab összevetve, a
T007 vs T011 capture-ből — a riport `probe_condition_finding` szekciója.)

**DE**: még a state-fixszel (story_context kivétele — a rubrika/kérdés
változatlan) is csak **~1.1–1.2%** érhető el a teljes prompton, mert a
work_notes/comments darabokat (a zaj-leltár tömegét) a modell ÉS a címkék is
essential/borderline-nek tartják — azok elrejtése recall-/minőség-kockázat.

## 4. Az őszinte konklúzió

**Az SC-001 ≥5% cél a jelenlegi rubrikával a gold kontextusokon minőség-
kockázat nélkül NEM elérhető.** A ténylegesen biztonságos zaj (admin-meta:
number/state/assigned_to/assignment_group) a teljes prompt ~0.9–1.2%-a. Az
SC-002 minőség-gate elsődlegessége (T003 döntés) ezt a határt húzza meg.

## Döntési opciók

- **(a) KÜSZÖB MARAD (0.25) + production state-fix (story_context kivétele a
  `_score_piece` state-ből) + SC-001 célérték-revízió 5% → ~1%** → a runner
  implementálja a fixet (a modul saját kódja, a rubrika/kérdés változatlan),
  újraméri a T007-et az új state-tel, és a T013 gate-eket az EMBER ÁLTAL
  revidiált célértékkel futtatja.
- **(b) Rubrika/kérdés újratervezés** — a spec újraindítási feltétele: a
  „How much of this piece matters" Score-rubrica nem szeparál production
  feltételben; új baseline + újramérés kell.
- **(c) MEGÁLLÁS** — a feature `enabled=false`-szal inaktív marad; a
  runner-report lezárja a specet; a T013 csak a mérhető gate-eket futtatja
  (SC-002/003/004/005 zöld, SC-001 PIROS = dokumentált, SC-006 a „marad"
  döntéssel zöld).

A küszöb-módosítás (ha lesz) az indoklással az Agent.md-be kerül — a runner
NEM módosítja a configot a jóváhagyás előtt.

## Bizonyíték-fájlok

- `artifacts/context_calibration_report_016.json` (sweep + plafon + finding,
  replay-ból byte-identikus)
- `artifacts/context_reanchor_report_016.json` (ReAnchor, EXPLORATÍV)
- `artifacts/context_calibration_capture_016.json` (56 nyers probe)
- `data/examples/context_labeled_016.json` (56 címkézett darab)
