# Runner-átadás: 014-component-instance-verification (Prime Agent / autonomous-spec-runner)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

Ezt a promptot a szerveren, a repó gyökeréből indított Prime Agentnek add át, MIUTÁN a
`specs/014-component-instance-verification/` mappa (spec.md, plan.md, tasks.md) bekerült
a repóba és commitolva van.

---

## Indítóprompt (másold át változatlanul)

```
Implementáld a specs/014-component-instance-verification specet. Használd az
`autonomous-spec-runner` skillt (telepített skill a szerveren — töltsd be
és kövesd az utasításait); az alábbi prompt a skill szabályaira RÁÉPÜL.

FUTTATÁSI MÓD: az egész munka DEV MÓDBAN fusson — SNOW_KB_DEV_MODE=1
környezeti változóval (vagy --dev flaggel), hogy a task-modell a lokális
llama.cpp Qwen3.8-27B legyen a Kimi K3 helyett, Kimi-token felhasználás
NÉLKÜL. A build_lm() így a config.yaml lokális api_base-jára csatlakozik.

ELŐSZÖR: checkoutold a `014-component-instance-verification` branchet
(git checkout 014-component-instance-verification) — a spec-fájlok és az összes
munka ezen a branchen él. A mainhez NE nyúlj; a commitok ide kerüljenek.

A spec-FÁJLOKBÓL dolgozz: specs/014-component-instance-verification/spec.md,
plan.md, tasks.md. A tasks.md checkboxai a külső memóriád — pipáld ahogy haladsz.

PREFLIGHT (ha bármelyik meghiusul, NE indulj el, jelentsd mi hiányzik):
0.  A `014-component-instance-verification` branch ki van checkoutolva és a
    spec-fájlok megvannak
0b. SNOW_KB_DEV_MODE=1 érvényes: settings.pipeline.task_model == "local"
0c. A lokális LLM-endpoint elérhető a szerverről:
    http://desktop-c5ikame-1.tailee6bc1.ts.net:8033/v1 (llama.cpp fut,
    Qwen3.8-27B betöltve, Tailscale serve aktív) — egy minimális
    completion-hívás sikeres
1.  TYPESAFE_API_KEY be van állítva és egy minimális system_one-hívás sikeres
2.  typesafe-sdk és dspy[typesafe] telepítve a projekt-környezetben (a 013 óta
    a pyproject része — ellenőrizd, ne telepítsd újra feleslegesen)
3.  A ServiceNow instance elérhető a szerverről (a spot-check és az update-set
    lekérdezés miatt) — egy minimális table-API hívás sikeres
4.  pytest -q zöld a kiinduló állapotban (309 teszt; env-érzékeny teszt:
    SNOW_KB_DEV_MODE nélkül futtasd a suite-et, a dev-mód az LLM-es
    futtatásokhoz kell — a 013-as runner-report megjegyzése)

GATE-ek: minden phase végén pytest -q; a T013 mérés gate-ei az SC-001..SC-004
exit-code-jai. A T013-ban a kalibráció a ReAnchor optimizerrel történik egy
csak-evaluációs DSPy-wrapperen (013-as T012 minta); a kijött threshold a
config.yaml verification_gate.confidence_threshold mezőjébe kerül. Használd a
projekt saját interpreterét/környezetét (ld. pyproject.toml).

TILALMAK:
- GEPA TILOS (sem baseline-újrafutás, sem optimalizálás — dev-módban nincs
  Kimi K3 reflection-modell)
- a MANUÁLIS KAPU checkboxokat (T005, T014) NE pipáld — azok emberi döntésre
  várnak
- a DSPy-programhoz (program.py, program.json), az eval-metrika MEGLÉVŐ
  tengelyeihez és a 004/011-es story-alapú hallucináció-ellenőrzéshez NE nyúlj
  (az instance-tengely ÚJ tengely MELLÉ, nem helyett — FR-006)
- a production döntéshívást NE alakítsd át DSPy-modullá (a ReAnchor-wrapper
  csak mérésre való)
- a verification_gate.enabled alapértelmezetten false maradjon; a gate
  bekapcsolása a T014 MANUÁLIS KAPU döntése
- külső szolgáltatás (ServiceNow / TypeSafe / lokális LLM) elérhetetlen →
  állj meg és jelentsd, NE improvizálj fallbacket
- a T013-nál a threshold-sweep exploratív — NE jelentsd a legjobb sweep-sort
  confirmatory eredményként; a confirmatory kapu a specben kijelölt 0.7
- ha a T004 baseline-leltár 0 „nem létező" nevet talál, NE „gyárts" problémát —
  jelentsd tényként és állj meg a T005 kapunál (ez is legitim kimenetel)

Ha elakadsz a MANUÁLIS KAPUnál, állj meg és szólj. Befejezéskor küldj
összefoglalót a main-sessionnek (per-phase eredmények, SC-gate-ek kimenetei,
commit-hash-ek), aztán goal.complete().
```

---

## Ami a promptban NINCS, és szándékosan

- **Nincs bemásolt tasklista** — a runner a tasks.md-ből dolgozik (playbook: „a prompt
  kikopik, a spec megmarad").
- **Nincs API-kulcs** — a preflight ellenőrzi a környezetet, a kulcs sosem kerül promptba
  vagy fájlba.
- **Nincs kötelező ütemezés** — a monitoring a completion-message-re támaszkodik.

## Emberi teendők a futás közben (a MANUÁLIS KAPUk)

| Task | Mikor | Mit kell tenned |
|---|---|---|
| T005 | baseline után | A T003/T004 leltár review-ja — hány „nem létező" név van ma; ha 0, a spec itt megállhat |
| T014 | mérés után | A gate default behavior (KD1: flag) + fail-open tradeoff jóváhagyása; SC-kapuk review-ja; küszöb-módosítás esetén indoklás az Agent.md-be |

## Takarítás (a futás után, a playbook 9. pontja szerint)

- runner leállítva, tmux/heartbeat/schedule törölve
- Agent.md naplóbejegyzés (T015 része): tények, commit-hash-ek, döntések, tanulságok
- backlog: TASK-2 lezárása (ez a spec volt a javasolt 014)
