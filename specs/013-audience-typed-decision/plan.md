# Implementation Plan: Audience-döntés kalibrált bizonyossággal

**Branch**: `013-audience-typed-decision` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/013-audience-typed-decision/spec.md`

## Summary

Az `ExtractChange.audience` mezőt (`Literal["helpdesk","end-user","developer"]`) egy dedikált,
típusos döntési hívás állítja elő a generatív `change_summary`/`key_steps` mellett, kalibrált
confidence-szel és replay-kompatibilis naplózással. Alacsony confidence-nél default `developer`
+ work_notes-jelzés; a döntési szolgáltatás hibája esetén fail-open a meglévő útra.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: DSPy 3.3.x (signature-ök, a program érintetlen), FastAPI + Uvicorn
(szerver), `typesafe-sdk` a nyilvános PyPI-ről (`pip install typesafe-sdk`), méréshez a
`jev-dspy-lab` metrikakódja (MIT, vendored vagy dependency — ld. Key Decisions)

**Storage**: N/A (a naplózás a meglévő log-infrastruktúrába + JSONL recording-fájlok)

**Testing**: pytest (a meglévő 286-tesztes suite zöld marad + új tesztek)

**Target Platform**: Linux VPS, systemd-managed FastAPI szolgáltatás

**Project Type**: web-service (webhook-driven pipeline)

**Performance Goals**: a döntési hívás ≤ ~500 ms p95 (a TypeSafe-szerinti 70–500 ms sáv),
nem lassíthatja érzékelhetően a Story → KB pipeline-t

**Constraints**: fail-open kötelező; a generatív út megmarad kapcsolható fallback-ként;
pinnelt modellverzió a kalibrációs mérésekhez

**Scale/Scope**: egy signature-mező, egy pipeline-beszúrás, ~3 érintett fájl + tesztek

## Constitution Check

*GATE: a repóban jelenleg nincs formális constitution-fájl — a felvétel javasolt külön
kezdeményezésként (`/speckit-constitution`), nem blokkoló. Az alábbi ellenőrzés a projekt
Agent.md-ben és README-ben implicit rögzített elvei alapján készült.*

| Elv (implicit) | Ellenőrzés |
|---|---|
| „Measured, not claimed" | ✅ — SC-k számszerűek, replay-alapú mérés |
| Fail-open / hibatűrés (spec 010 FR-002 minta) | ✅ — FR-001 kötelező |
| A pipeline GEPA-programja érintetlen | ✅ — a beszúrás a programon kívül, a pipeline rétegben |
| Baseline-előbb | ✅ — Phase 0 rögzíti a jelenlegi modell audience-döntéseit a gold példákon |

## Architecture

```text
Story fetch + Update Set fetch (változatlan)
        │
        ▼
┌─ pipeline.py ─────────────────────────────────────────────┐
│  ExtractChange (DSPy + Kimi K3)                            │
│    → change_summary, key_steps          (változatlan)      │
│                                                            │
│  ÚJ: decide_audience(story_text)                           │
│    → TypeSafe Choice: helpdesk / end-user / developer      │
│    → confidence + opciónkénti valószínűségek               │
│    → JSONL recording (hash + response + latency + model)   │
│    → hiba / timeout → fail-open: LLM-fallback (config-flag)│
│    → confidence < threshold → developer + work_notes-jelzés│
└────────────────────────────────────────────────────────────┘
        │
        ▼
GenerateKbFromTemplate (változatlan, audience-t kontextusként kapja)
```

## Key Decisions

1. **Közvetlen SDK-hívás, NEM a `dspy-typesafeify` fork** — a fork PoC, nem éles
   disztribúció; a DSPy-signature és a GEPA-program érintetlen marad. (Alternatíva: a fork
   dekorátora — elvetve, mert upstream-forkot nem viszünk productionbe.)
2. **A Jev mint döntési modell** — kalibrált, opciónkénti valószínűséget ad (RLCD).
   (Alternatíva: az LLM-et saját confidence-becslésre kérni — elvetve, az RLHF-modellek
   túlbiztosak; a spec Backgroundja.)
3. **Mérés a jev-dspy-lab metrikakódjával** (selective risk, coverage, ECE, Brier),
   record/replay SDK-szinten adaptálva. (Alternatíva: saját mini-metrika — elvetve, a
   kalibrációs statisztika nem triviális, a lab MIT-licencű és battle-tested.)
   *Kiegészítés (2026-09-26): a küszöb-hangolás eszköze a hivatalos DSPy `ReAnchor`
   optimizer (`dspy[typesafe]` extra, `dspy.experimental`) — LLM-hívás nélküli
   kalibráció a trainseten; a kapumetrikák továbbra is a jev-dspy-lab-ból jönnek.
   A hivatalos `TypeSafe` LM-connectorra való teljes átállás elvetve ebben a spec-ben:
   `dspy.experimental` API production-pinnelése ugyanaz a kockázat, amit a forknál
   elutasítottunk; újraindítási feltétel: stabil (nem experimental) API.*
4. **Fail-open, nem fail-closed** — TypeSafe-kiesésnél a pipeline a meglévő úton fut
   tovább, warninggal. (Alternatíva: blokkolás — elvetve, a rendelkezésreállás elsődleges;
   ez a spec Edge Cases-ben rögzített tradeoff, MANUÁLIS KAPU a tasks.md-ben.)
5. **Pinnelt modellverzió** a kalibrációhoz (`jev-1.13.0` vagy a mérés pillanatában aktuális
   pinned), nem `jev-latest` — playbook: „modell-csere = baseline újramérés".
6. **Alacsony-confidence default = `developer`** — a legbiztonságosabb technikai hangnem
   (spec Assumptions; ha a review másképp látja, a tasks.md-ben javítandó).

## Phases

1. **Phase 0 – Baseline (US1 előfeltétel)**: a jelenlegi modell audience-döntései
   rögzítve a 9 gold példán (fájlba, nem chatbe); gold audience-címkék ellenőrzése
   (Assumptions szerint, különben kézi címkézés).
2. **Phase 1 (US1)**: `decide_audience` modul + recording + fail-open + tesztek.
3. **Phase 2 (US2)**: confidence-küszöb + fallback + work_notes-jelzés + tesztek.
4. **Phase 3 – Mérés és kalibráció**: élő felvétel a gold + mock mintán, offline replay,
   SC-001..SC-004 gate-ek exit-code-dal.
```

## Complexity Tracking

Nincs constitution-violation — a tábla üresen marad.
