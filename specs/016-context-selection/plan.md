# Implementation Plan: Kontextus-válogatás a cikkgeneráláshoz

**Branch**: `016-context-selection` | **Date**: 2026-10-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/016-context-selection/spec.md`

## Summary

A GenerateKb kontextus-darabjai (story-szekciók, update set rekordok, kapcsolódó
KB-cikkek) a generálás előtt kalibrált, típusos Score-minősítést kapnak
(hide/summarize/show); a végrehajtás plain Python policy, fail-open a „show"
irányba. A hatás (token-delta, minőség-delta) baseline-előbb, replay-kompatibilis
méréssel igazolva; a hide/show küszöb aszimmetrikus ReAnchor-kalibrációval —
a 013–015 infrastruktúra változatlanul újrahasznosul.

## Technical Context

**Language/Version**: Python 3.12

**Primary Dependencies**: `typesafe-sdk` + `dspy[typesafe]` (a projektben a 013 óta;
az új döntés `dspy.experimental.Score`-típusú — eval-wrapper a 014/015 mintára),
vendored `jev_replay.py` + `eval/jev_metrics.py`; a „summarize" a lokális Qwen-
endpointról (lásd KD3)

**Storage**: JSONL recording (013-formátum) + a baseline/mérés artifactok
(`artifacts/context_selection_*.json`)

**Testing**: pytest (387-es suite zöld marad + új tesztek)

**Target Platform**: Linux VPS, systemd-managed FastAPI szolgáltatás

**Performance Goals**: a válogatás plusz-latenciája ≤ a token-megtakarítás
időnyeresége (a System One döntés ~70–500 ms/darab; a darabszám kicsi — a
story-szekciók + update set rekordok + kapcsolódó cikkek összesen jellemzően
< 30 darab)

**Constraints**: fail-open = „show" (FR-002); a story-főtörzs sosem „hide"
(FR-004); a minőség nem romolhat (SC-002); recall-védelem (SC-003);
pinnelt modellverzió; safety floor kalibrációval nem mozgatható

**Scale/Scope**: egy új modul (`context_selection.py`) + pipeline-bekötés +
eval-kiegészítés + tesztek; a program.py/program.json érintetlen

## Constitution Check

*GATE: formális constitution továbbra sincs — az ellenőrzés az Agent.md implicit
elvei alapján.*

| Elv (implicit) | Ellenőrzés |
|---|---|
| „Measured, not claimed" | ✅ — SC-001 célértéke a Phase 0 baseline UTÁN rögzül |
| Fail-open | ✅ — FR-002: hiba/alacsony confidence → show |
| A GEPA-program érintetlen | ✅ — a válogatás a program ELŐTT, a pipeline-rétegben |
| Baseline-előbb | ✅ — Phase 0: token + minőség + zaj-leltár rögzítve |
| Recall-védelem | ✅ — SC-003 exit-code-os teszt (a kinyerő-finomítás mintája) |

## Architecture

```text
Story fetch + Update Set fetch + kapcsolódó-cikk keresés (változatlan)
        │
        ▼
┌─ pipeline.py ───────────────────────────────────────────────────────┐
│  ÚJ: select_context(pieces)  ← a 016 modulja                         │
│    per darab: Score-döntés (Jev, pinnelt) + confidence               │
│    → Python-policy: hide (< küszöb) / summarize / show               │
│    → story-főtörzs: mindig show (FR-004)                             │
│    → summarize: lokális Qwen összefoglaló (KD3)                      │
│    → JSONL recording + fail-open (hiba → show)                       │
│                                                                      │
│  GenerateKbFromTemplate a VÁLOGATOTT kontextussal (program érintetlen)│
└──────────────────────────────────────────────────────────────────────┘
        │
        ▼
servicenow_client.create_kb_article → a 014/015-ös gate változatlanul él
```

## Key Decisions

1. **Score-típusú döntés per darab** (nem külön Noul per darab) — a hide/summarize/show
   egy rendezett skála, a `Score`-cuts pont erre való (a cmpnd-ai v3 minta);
   a kérdés: „How much of this piece matters for writing the KB article?"
   (Alternatíva: két Noul lépcső — elvetve, két küszöb helyett egy skála a
   természetes modell.)
2. **A végrehajtás plain Python policy** — a valószínűségek a Jevtől, a küszöbök
   configból/kézzel; a modell sosem „dönti el", csak pontoz (a patterns-repó
   alapszabálya: „Jev returns the probability, plain Python owns the policy").
3. **A „summarize" a lokális Qwen-endpointon** (a dev-mód api_base-ja), NEM a
   task-modellel — élesben is az olcsó réteg összefoglal; ha az endpoint nem
   érhető el, fail-open: a darab show-ként kerül be. (Alternatíva: a task-modell
   (Kimi K3) összefoglal — elvetve, token-költség és a Kimi-token érintettség;
   a 015-ös dev-mód tapasztalat szerint a lokális 27B összefoglalásra elég.)
4. **Aszimmetrikus kalibráció a hide-küszöbre**: a releváns darab elrejtése
   (recall-hiba) többszörösen drágább, mint a zaj mutatása — az arány a
   kalibrációs riportban érzékenység-analízissel (a 015-ös KD1 minta; kiinduló
   arány 5:1, mert a fail-open amúgy is a show irányba véd).
5. **A válogatás a pipeline-rétegben, a program ELŐTT** — a GEPA-program és a
   program.json érintetlen (Constitution Check). (Alternatíva: a signature-be
   építve — elvetve, az a program módosítása lenne.)
6. **Az SC-001 célérték a baseline után rögzül** — a Phase 0 zaj-leltár adja a
   reális célt (ha nincs mérhető zaj, a spec megáll — a 014-es minta).

   **RÖGZÍTVE a T003 MANUÁLIS KAPUn (2026-10-02, emberi jóváhagyás): ≥5% token-
   megtakarítás a TELJES PROMPTON mérve (template + kontextus, a generálás LM
   usage prompt_tokens alapja) — NEM csak a kontextus-darabokon.** Az SC-002
   minőség-gate ELSŐDLEGES: ha az 5% csak minőség-romlással érhető el, a minőség
   nyer (a T009 riport őszintén jelenti, PIROS-sal is). A kontextus-token-
   csökkenés referencia-számként a riportban marad (baseline: 8540 kontextus-
   token, 1825 zaj-jelölt = 21.4%; a teljes prompt ~3200-8100 token/példa, így
   az 5% teljes-prompt cél szűkebb mozgástér — ld.
   artifacts/context_sc001_target.json).

## Phases

1. **Phase 0 – Baseline**: a gold példák kontextusának darabolása + token-leltár
   (darabonként), zaj-becslés; a rich_metric baseline újramérve `cache=False`-szal;
   az SC-001 célérték EZ UTÁN rögzítve a plan frissítésével.
2. **Phase 1 (US1)**: `context_selection.py` (Score-döntés + policy + recording +
   fail-open) + pipeline-bekötés + tesztek.
3. **Phase 2 (US2)**: mérés a gold példákon — token-delta + rich_metric-delta
   riport, replay-módban.
4. **Phase 3 (US3)**: címkézett kontextus-minta (min. 20 darab: releváns/zaj/
   határeset — a fixture mintára gépi + kézi címkézéssel) + ReAnchor-kalibráció +
   riport.
5. **Phase 4 – Zárás**: SC-001..SC-006 gate-ek exit-code-dal, Agent.md, backlog.

## Complexity Tracking

Nincs constitution-violation — a tábla üresen marad.
