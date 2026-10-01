# Runner-átadás: 015-asymmetric-verification-gate (Prime Agent / autonomous-spec-runner)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

Ezt a promptot a szerveren, a repó gyökeréből indított Prime Agentnek add át, MIUTÁN a
`specs/015-asymmetric-verification-gate/` mappa (spec.md, plan.md, tasks.md) bekerült
a repóba és commitolva van.

---

## Indítóprompt (másold át változatlanul)

```
Implementáld a specs/015-asymmetric-verification-gate specet. Használd az
`autonomous-spec-runner` skillt (telepített skill a szerveren — töltsd be
és kövesd az utasításait); az alábbi prompt a skill szabályaira RÁÉPÜL.

FUTTATÁSI MÓD: az egész munka DEV MÓDBAN fusson — SNOW_KB_DEV_MODE=1
környezeti változóval (vagy --dev flaggel), hogy a task-modell a lokális
llama.cpp Qwen3.8-27B legyen a Kimi K3 helyett, Kimi-token felhasználás
NÉLKÜL. A build_lm() így a config.yaml lokális api_base-jára csatlakozik.

ELŐSZÖR: checkoutold a `015-asymmetric-verification-gate` branchet
(git checkout 015-asymmetric-verification-gate) — a spec-fájlok és az összes
munka ezen a branchen él. A mainhez NE nyúlj; a commitok ide kerüljenek.

A spec-FÁJLOKBÓL dolgozz: specs/015-asymmetric-verification-gate/spec.md,
plan.md, tasks.md. A tasks.md checkboxai a külső memóriád — pipáld ahogy haladsz.

PREFLIGHT (ha bármelyik meghiusul, NE indulj el, jelentsd mi hiányzik):
0.  A `015-asymmetric-verification-gate` branch ki van checkoutolva és a
    spec-fájlok megvannak
0b. SNOW_KB_DEV_MODE=1 érvényes: settings.pipeline.task_model == "local"
0c. A lokális LLM-endpoint elérhető a szerverről:
    http://desktop-c5ikame-1.tailee6bc1.ts.net:8033/v1 (llama.cpp fut,
    Qwen3.8-27B betöltve, Tailscale serve aktív) — egy minimális
    completion-hívás sikeres
1.  TYPESAFE_API_KEY be van állítva és egy minimális system_one-hívás sikeres
2.  typesafe-sdk és dspy[typesafe] telepítve (a 013/014 óta a projekt része —
    ellenőrizd, ne telepítsd újra)
3.  A ServiceNow PDI elérhető a szerverről ÉS a user admin jogú (a metaadat-
    táblák lekérdezéséhez) — egy minimális table-API hívás a sys_script_include-on
    sikeres
4.  A 014-es mérőinfrastruktúra megvan és működik: eval/verification_measure.py,
    eval/verification_reanchor.py, eval/verification_sc_gates.py,
    data/examples/verification_labeled.json, artifacts/verification_spotcheck_cache.json
5.  pytest -q zöld a kiinduló állapotban (349 teszt; SNOW_KB_DEV_MODE NÉLKÜL
    futtasd a suite-et — a 013-as runner-report megjegyzése)

GATE-ek: minden phase végén pytest -q; a T012 gate-ei az SC-001..SC-005
exit-code-jai. A kalibráció a ReAnchor optimizerrel történik egy csak-evaluációs
DSPy-wrapperen (014-es minta); a kijött threshold CSAK T009 emberi jóváhagyás
után kerülhet a config.yaml-ba. Használd a projekt saját interpreterét.

TILALMAK:
- GEPA TILOS (dev-módban nincs Kimi K3 reflection-modell)
- a MANUÁLIS KAPU checkboxokat (T003, T009) NE pipáld — azok emberi döntésre
  várnak
- a DSPy-programhoz (program.py, program.json), az eval-metrika MEGLÉVŐ
  tengelyeihez és a 004/011-es story-alapú ellenőrzéshez NE nyúlj
- a production döntéshívást NE alakítsd át DSPy-modullá (ReAnchor csak mérés)
- a fixture-script KIZÁRÓLAG a PDI-n MÁR MEGLEVŐ komponenseket capture-ölje —
  ÚJ komponens létrehozása TILOS (a T001-ben „capture, NEM létrehozás")
- T005 magminimum: ha a jóváhagyott magnév-halmaz < 8 név, ÁLLJ MEG és jelentsd —
  a minta NEM hígítható korrelált variánsokkal
- a kalibráció CSAK a confidence_threshold-ot hangolja: a fail-open és a
  flag-only alapviselkedés kézzel beállított safety floor, nem mozgatható
- a threshold-sweep exploratív — NE jelentsd a legjobb sweep-sort confirmatory
  eredményként
- SC-003: ha az új threshold a meglévő 24 példás mintán RONT, a config NEM
  módosul, a riport PIROS — NE „kerüld meg" ezt a gate-et
- külső szolgáltatás (ServiceNow / TypeSafe / lokális LLM) elérhetetlen →
  állj meg és jelentsd, NE improvizálj fallbacket
- a gate-emelés (T011) során a deploy-t NEM a runner végzi — csak a kód és a
  deploy/README megjegyzés; a tényleges restart emberi lépés

Ha elakadsz a MANUÁLIS KAPUnál, állj meg és szólj. Befejezéskor küldj
összefoglalót a main-sessionnek (per-phase eredmények, SC-gate-ek kimenetei,
commit-hash-ek), aztán goal.complete().
```

---

## Ami a promptban NINCS, és szándékosan

- **Nincs bemásolt tasklista** — a runner a tasks.md-ből dolgozik.
- **Nincs API-kulcs** — a preflight ellenőrzi a környezetet.
- **Nincs deploy-utasítás** — a T011 csak kód + deploy/README megjegyzés; a tényleges
  élesítés emberi lépés (a 014-es deploy-checklist mintájára).

## Emberi teendők a futás közben (a MANUÁLIS KAPUk)

| Task | Mikor | Mit kell tenned |
|---|---|---|
| T003 | T002 után | A dumpolt komponens-lista review-ja (furcsa/instabil nevek kiszúrása) — a minta csak ezután épül |
| T009 | T008 után | A kalibrációs riport review-ja; threshold-változás jóváhagyása + indoklás az Agent.md-be |

## Takarítás (a futás után)

- runner leállítva, tmux/heartbeat/schedule törölve
- Agent.md naplóbejegyzés (T013 része)
- backlog: TASK-3 (016 jelölt) állapotának felülvizsgálata
