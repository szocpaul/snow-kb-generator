# Runner-átadás: 016-context-selection (Prime Agent / autonomous-spec-runner)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

Ezt a promptot a szerveren, a repó gyökeréből indított Prime Agentnek add át, MIUTÁN a
`specs/016-context-selection/` mappa (spec.md, plan.md, tasks.md) bekerült a repóba
és commitolva van.

---

## Indítóprompt (másold át változatlanul)

```
Implementáld a specs/016-context-selection specet. Használd az
`autonomous-spec-runner` skillt (telepített skill a szerveren — töltsd be
és kövesd az utasításait); az alábbi prompt a skill szabályaira RÁÉPÜL.

FUTTATÁSI MÓD: az egész munka DEV MÓDBAN fusson — SNOW_KB_DEV_MODE=1
környezeti változóval, hogy a task-modell a lokális llama.cpp Qwen3.8-27B
legyen, Kimi-token felhasználás NÉLKÜL.

ELŐSZÖR: checkoutold a `016-context-selection` branchet
(git checkout 016-context-selection) — a spec-fájlok és az összes munka ezen a
branchen él. A mainhez NE nyúlj.

A spec-FÁJLOKBÓL dolgozz: specs/016-context-selection/spec.md, plan.md, tasks.md.
A tasks.md checkboxai a külső memóriád — pipáld ahogy haladsz.

PREFLIGHT (ha bármelyik meghiusul, NE indulj el, jelentsd mi hiányzik):
0.  A `016-context-selection` branch ki van checkoutolva, spec-fájlok megvannak
0b. SNOW_KB_DEV_MODE=1 érvényes: settings.pipeline.task_model == "local"
0c. A lokális LLM-endpoint elérhető (http://desktop-c5ikame-1.tailee6bc1.ts.net:8033/v1)
    — minimális completion-hívás sikeres (a summarize KD3 szerint EZT használja
    productionben is — itt különösen kritikus)
1.  TYPESAFE_API_KEY be van állítva + minimális system_one-hívás sikeres
2.  typesafe-sdk és dspy[typesafe] telepítve (a 013 óta a projekt része)
3.  A 013–015-ös mérőinfrastruktúra megvan: vendor/jev_replay.py,
    eval/jev_metrics.py, eval/verification_reanchor*.py minták
4.  pytest -q zöld a kiinduló állapotban (387 teszt; SNOW_KB_DEV_MODE NÉLKÜL
    futtasd a suite-et)

GATE-ek: minden phase végén pytest -q; a T013 gate-ei az SC-001..SC-006
exit-code-jai. A kalibráció ReAnchorral, csak-evaluációs wrapperen; a küszöb
CSAK T012 emberi jóváhagyás után kerülhet a configba.

TILALMAK:
- GEPA TILOS (dev-módban nincs Kimi K3 reflection-modell)
- a MANUÁLIS KAPU checkboxokat (T003, T009, T012) NE pipáld
- a DSPy-programhoz (program.py, program.json), a rich_metric-hez, a 004/011-es
  tengelyekhez, a 014/015-ös verification gate-hez és a kinyerőhöz NE nyúlj
- a story-főtörzs SOHA nem lehet „hide" (FR-004)
- a fail-open irány MINDIG „show" (hiba/alacsony confidence → a darab bekerül)
- a safety floor (fail-open=show, flag-only alapok) kalibrációval NEM mozgatható
- ha a T002 baseline NEM mutat mérhető zajt → ÁLLJ MEG és jelentsd a T003
  kapunál (a spec megállhat; NE „gyárts" zajt)
- a T007 mérésben minőség-romlás vagy recall-kiesés → a riport PIROS, a T009
  kapunál jelentsd — NE „hangold szépnek"
- külső szolgáltatás elérhetetlen → állj meg és jelentsd, NE improvizálj
- a threshold-sweep exploratív — NE jelentsd confirmatoryként
- deploy NEM a runner dolga

Ha elakadsz a MANUÁLIS KAPUnál, állj meg és szólj. Befejezéskor küldj
összefoglalót a main-sessionnek (per-phase eredmények, SC-gate-ek kimenetei,
commit-hash-ek), aztán goal.complete().
```

---

## Emberi teendők a futás közben (a MANUÁLIS KAPUk)

| Task | Mikor | Mit kell tenned |
|---|---|---|
| T003 | baseline után | Zaj-leltár review + **az SC-001 token-célérték rögzítése** (vagy a spec leállítása, ha nincs zaj) |
| T009 | T007/T008 után | A hatásriport review-ja: minőség-romlás/recall-kiesés esetén megállás |
| T012 | T011 után | A kalibrációs riport review-ja; küszöb-jóváhagyás + Agent.md-indoklás |

## Takarítás (a futás után)

- runner leállítva, tmux/heartbeat/schedule törölve
- Agent.md naplóbejegyzés (T013 része)
- backlog: TASK-3 lezárása (ez a spec volt a 016-os jelölt)
