# Implementation Plan: Komponensnév-hitelesítés az instance ellen + production push-gate

**Branch**: `014-component-instance-verification` | **Date**: 2026-09-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-component-instance-verification/spec.md`

## Summary

A generált KB-cikk nevesített komponensneveit a ServiceNow-írás ELŐTT az
instance-metaadatok ellenében validáljuk: a tiszta esetek determinisztikus
névegyezéssel, a homályos esetek (írásvariánsok) kalibrált, típusos döntéssel —
a 013-ban archivált mérőinfrastruktúra (recording, replay, jev-metrics,
ReAnchor-wrapper, SC-gate minta) újrahasznosításával. Fail-open kötelező;
a meglévő story-alapú védelem (004/011) érintetlen marad mellette.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: a meglévő stack (DSPy 3.x signature-ök érintetlenek),
a `servicenow_client` table-API sessionje a metaadat-lekérdezéshez,
`typesafe-sdk` + `dspy[typesafe]` a kalibrált réteghez (már a pyproject-ban,
a 013 óta), vendored `src/snow_kb/vendor/jev_replay.py` + `eval/jev_metrics.py`

**Storage**: Update Set-whitelist (a story update set XML-jeiből) + per-név
spot-check cache (JSON, a recording része) + JSONL recording-fájlok (a 013-as formátum)

**Testing**: pytest (a 309-es suite zöld marad + új tesztek)

**Target Platform**: Linux VPS, systemd-managed FastAPI szolgáltatás

**Performance Goals**: a gate ≤ ~1 s p95 plusz-latencia cikkenként (snapshot-
cache-ből dolgozik; élő metaadat-lekérdezés csak cache-miss/refresh esetén)

**Constraints**: fail-open kötelező (FR-002); a gold cikkeken 0 false positive
(SC-001); min. 20 példás címkézett minta az SC-002-höz (013-as tanulság);
pinnelt döntési modellverzió

**Scale/Scope**: egy új modul (`verification.py`) + metrika-kiegészítés +
gate-bekötés, ~4 érintett fájl + tesztek

## Constitution Check

*GATE: a repóban továbbra sincs formális constitution-fájl — az ellenőrzés az
Agent.md-ben rögzített implicit elvek alapján készült.*

| Elv (implicit) | Ellenőrzés |
|---|---|
| „Measured, not claimed" | ✅ — SC-k számszerűek, replay-alapú mérés, min. mintaméret |
| Fail-open / hibatűrés | ✅ — FR-002, mindkét rétegnél (spec Edge Cases) |
| A pipeline GEPA-programja érintetlen | ✅ — a gate a programon kívül, az írási út előtt |
| Baseline-előbb | ✅ — Phase 0: a jelenlegi cikkek komponensnevei + instance-snapshot rögzítve |
| Meglévő védelem érintetlen | ✅ — a 004/011 story-alapú ellenőrzés változatlan (FR-006) |

## Architecture

```text
Story fetch + Update Set fetch (változatlan)
        │
        ▼
┌─ pipeline.py ────────────────────────────────────────────────────┐
│  ExtractChange → GenerateKbFromTemplate (változatlan)             │
│                                                                  │
│  ÚJ: verify_component_names(article_html, update_set_text)              │
│    ┌─ determinisztikus mag: jelölt-kinyerés (011-minta)          │
│    │   → 1. Update Set-whitelist (get_update_set_changes), 2. ami nincs benne: per-név spot-check az instance-ben (cache-elve)               │
│    │   → létezik / nem létezik (tiszta esetek)                   │
│    └─ homályos esetek → kalibrált döntés (TypeSafe Noul,         │
│        pinnelt verzió): „ez a megnevezés erre a valós            │
│        komponensre utal-e?"                                      │
│    → JSONL recording (013-formátum) + fail-open (FR-002)         │
│    → config.viselkedés: jelzés (default) / strip / blokkolás     │
└──────────────────────────────────────────────────────────────────┘
        │
        ▼
servicenow_client.create_kb_article — a gate a _live út ELŐTT fut;
nem-létező nevek → work_notes-jelzés a mért confidence-szel
```

Eval-oldalon: a metrika kap egy instance-tengelyt (US1) — a meglévő
story-alapú hallucination-tengely mellé, visszafelé kompatibilisen.

## Key Decisions

1. **A gate default viselkedése: JELZÉS (work_notes), nem strip és nem blokkolás** —
   a komponensnév eltávolítása a cikkből sokkal durvább beavatkozás, mint a KB-szám-strip
   volt (a szöveg értelmét bontja); a blokkolás pedig a rendelkezésreállást kockáztatja.
   (Alternatíva: strip a 004-es mintára — elvetve, a mondatkörnyezetben lévő nevek
   stripje olvashatatlan cikket ad; blokkolás — elvetve, fail-closed.)
   *A config kapcsolóval bármikor szigorítható, ha a mérési adat igazolja.*
2. **Kétrétegű ellenőrzés: determinisztikus mag + kalibrált réteg csak a homályos
   esetekre** — a „létezik/nem létezik" pontos névegyezéssel dönt (tény, ingyen);
   a Jev csak az írásvariánsoknál lép be. (Alternatíva: minden névre Jev-hívás —
   elvetve, felesleges költség és kalibrációs zaj a tiszta eseteken.)
3. **Hierarchikus ground truth: Update Set-elsődleges + per-név spot-check** — az
   elsődleges whitelist a story Update Set-jének tartalma (a `get_update_set_changes`
   már hozza; ami ott van, az valós ÉS a cikk tárgya). Ami nincs az update setben,
   arra NEM teljes instance-snapshot készül, hanem célzott per-név spot-check
   („létezik-e X nevű Script Include?"), cache-elve. (Alternatíva: teljes
   instance-snapshot — elvetve, felesleges adatmozgatás; „csak update set" — elvetve,
   false positive-özön a legitim már-létező komponens-hivatkozásokon, pl. `incident`
   tábla vagy érintett meglévő script.) A cache a recording része → a replay
   byte-identikus marad (SC-004). **Edge case**: ha a story-hoz nincs update set,
   a gate csak a spot-check rétegig megy (a 011-es dataset-hézag miatt ez gyakori
   lehet — a mérés mutatja meg, mennyire).
4. **Per-komponens döntés** (nem per-cikk) — a work_notes-ban megnevezhető a gyanús
   név; a 013-as work_notes-jelzés mintája ezt kéri. (Alternatíva: per-cikk bool —
   elvetve, nem lokalizálja a hibát.)
5. **A 013-as infrastruktúra újrahasznosítása, általánosítás nélkül** — a
   jev_replay/jev_metrics/ReAnchor minta átemelődik a verification-kontextusba;
   NEM refaktoráljuk „általános decision-frameworkmé" (YAGNI; ha a 015 is döntés
   lesz, akkor éri meg az absztrakció).
6. **Pinnelt döntési modell** a kalibrált réteghez (a 013 óta ismert okból:
   modell-csere = baseline újramérés).
7. **A kalibráció eszköze ReAnchor** a 013-as T012 mintájára (csak-evaluációs
   DSPy-wrapper; a production hívás közvetlen SDK marad).

## Phases

1. **Phase 0 – Baseline + snapshot**: instance-metaadat-snapshot felvétele
   (tábla/mező/script-nevek, PDI-ről, fájlba); a meglévő gold + egy frissen
   generált cikkminta komponensneveinek leltára a snapshot ellenében —
   hány „nem létezik" jelölt van MA (ez a probléma nagyságának első számszerű
   bizonyítéka).
2. **Phase 1 (US1)**: metrika instance-tengely + tesztek (mock snapshot).
3. **Phase 2 (US2)**: `verification.py` determinisztikus mag + gate-bekötés a
   `servicenow_client._create_kb_article_live` elé + work_notes-jelzés + tesztek.
4. **Phase 3 (US3)**: kalibrált réteg a homályos esetekre + recording + tesztek.
5. **Phase 4 – Mérés**: címkézett minta (≥20 példa: valós nevek + szándékolt
   írásvariánsok + fabrikált nevek), élő felvétel + replay + ReAnchor +
   SC-001..SC-004 gate-ek exit-code-dal.

## Complexity Tracking

Nincs constitution-violation — a tábla üresen marad.
