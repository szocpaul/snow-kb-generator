# Runner-átadás: 013-audience-typed-decision (Prime Agent / autonomous-spec-runner)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Tasks**: [tasks.md](tasks.md)

Ezt a promptot a szerveren, a repó gyökeréből indított Prime Agentnek add át, MIUTÁN a
`specs/013-audience-typed-decision/` mappa (spec.md, plan.md, tasks.md) bekerült a repóba
és commitolva van.

---

## Indítóprompt (másold át változatlanul)

```
Implementáld a specs/013-audience-typed-decision specet. Használd az
`autonomous-spec-runner` skillt (telepített skill a szerveren — töltsd be
és kövesd az utasításait); az alábbi prompt a skill szabályaira RÁÉPÜL.

FUTTATÁSI MÓD: az egész munka DEV MÓDBAN fusson — SNOW_KB_DEV_MODE=1
környezeti változóval (vagy --dev flaggel), hogy a task-modell a lokális
llama.cpp Qwen3.8-27B legyen a Kimi K3 helyett, Kimi-token felhasználás
NÉLKÜL. A build_lm() így a config.yaml lokális api_base-jára csatlakozik.

ELŐSZÖR: checkoutold a `013-audience-typed-decision` branchet
(git checkout 013-audience-typed-decision) — a spec-fájlok és az összes munka
ezen a branchen él. A mainhez NE nyúlj; a commitok ide kerüljenek.

A spec-FÁJLOKBÓL dolgozz: specs/013-audience-typed-decision/spec.md, plan.md,
tasks.md. A tasks.md checkboxai a külső memóriád — pipáld ahogy haladsz.

PREFLIGHT (ha bármelyik meghiusul, NE indulj el, jelentsd mi hiányzik):
0.  A `013-audience-typed-decision` branch ki van checkoutolva és a 4 spec-fájl megvan
0b. SNOW_KB_DEV_MODE=1 érvényes: settings.pipeline.task_model == "local"
0c. A lokális LLM-endpoint elérhető a szerverről:
    http://desktop-c5ikame-1.tailee6bc1.ts.net:8033/v1 (llama.cpp fut,
    Qwen3.8-27B betöltve, Tailscale serve aktív) — egy minimális
    completion-hívás sikeres
1.  TYPESAFE_API_KEY be van állítva és egy minimális system_one-hívás sikeres
2.  pip install typesafe-sdk és pip install "dspy[typesafe]" sikeres a
    projekt-környezetben (nyilvános PyPI, extra index NEM kell)
3.  A gold dataset példái tartalmaznak futtatható story-inputot (nem csak gold cikket)
4.  pytest -q zöld a kiinduló állapotban

GATE-ek: minden phase végén pytest -q; a T012 mérés gate-ei az SC-001..SC-004
exit-code-jai. A T012-ben a kalibráció a ReAnchor optimizerrel történik egy
csak-evaluációs DSPy-wrapperen; a kijött threshold a config.yaml
audience_decision.confidence_threshold mezőjébe kerül. Használd a projekt saját
interpreterét/környezetét (ld. pyproject.toml).

TILALMAK:
- GEPA TILOS (sem baseline-újrafutás, sem optimalizálás — dev-módban amúgy sincs
  Kimi K3 reflection-modell, ez a tilalom ezzel konzisztens)
- a MANUÁLIS KAPU checkboxokat (T005, T011, T013) NE pipáld — azok emberi
  döntésre várnak
- a DSPy-programhoz (program.py, program.json) és az eval-metrikához NE nyúlj
- a production döntéshívást NE alakítsd át DSPy-modullá (a ReAnchor-wrapper
  csak mérésre való, ld. T012)
- külső szolgáltatás elérhetetlen → állj meg és jelentsd, NE improvizálj
  fallbacket
- a T012-nél a threshold-sweep exploratív — NE jelentsd a legjobb sweep-sort
  confirmatory eredményként; a confirmatory kapu a specben kijelölt 0.7

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
- **Nincs kötelező ütemezés** — a monitoring a completion-message-re támaszkodik; 15 perces
  heartbeat csak akkor, ha a futás várhatóan hosszú (a T012 élő felvétel miatt lehet az).

## Emberi teendők a futás közben (a MANUÁLIS KAPUk)

| Task | Mikor | Mit kell tenned |
|---|---|---|
| T005 | baseline után | A 9 gold audience-címke és a baseline-eredmény review-ja |
| T011 | US2 implementáció után | A fail-open + developer-default tradeoff jóváhagyása production-futás előtt |
| T013 | T012 mérés után | Az SC-kapuk eredményeinek review-ja; küszöb-módosítás esetén indoklás az Agent.md-be |

## Takarítás (a futás után, a playbook 9. pontja szerint)

- runner leállítva, tmux/heartbeat/schedule törölve
- Agent.md naplóbejegyzés (T014 része): tények, commit-hash-ek, döntések, tanulságok
- backlog: a verifikációs-réteg spec újraindítási feltételének állapotjelzése
