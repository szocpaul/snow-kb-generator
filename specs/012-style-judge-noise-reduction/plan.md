# Implementation Plan: Style Judge zajcsökkentés (multi-sample pontozás)

**Branch**: `012-style-judge-noise-reduction` | **Date**: 2026-08-11 | **Spec**: [spec.md](spec.md)

## Technical Context

- Python 3.12, DSPy 3.3.0; **interpreter: `../.venv`**
- A style judge: lokális Qwen3.6-35B-A3B (llama.cpp, `-np 4`), ugyanaz a modell, mint a task (tudatos kompromisszum — változatlan)
- Érintett fájl: elsődlegesen `eval/metric.py` (`_style_score`, `StyleJudge` környéke) + `tests/test_style_axis.py` / `tests/test_eval_metric.py`
- Mérési oldal: `eval/baseline.py` futtatások (cache=False), NINCS kódmódosítás a pipeline-ban
- Mért kiindulás (2026-08-11): style szórás 0.188 (3 azonos futás, Agent.md 32)

## Architecture

```
ELŐTTE:                          UTÁNA (US1):
_style_score(html)               _style_score(html)
      │                                ├── judge(html, ref) → s1
      ▼                                ├── judge(html, ref) → s2   (N=3)
 judge ×1 → score                       ├── judge(html, ref) → s3
 (±0.19 zaj)                            │
                                         ▼
                                    score = mean(sikeres minták)
                                    critique = az átlaghoz legközelebbi mintáé
                                    részleges hiba: mean(maradék) + warning
                                    mind hiba: (0.5, "") — FR-002 érintetlen
                                         │
                                         ▼
                                    (cél: ±0.10 zaj — US2 kalibráció)
```

## Key Decisions

1. **Átlag (mean), nem medián**: a pontszám 0-1 skálán folytonos; a mean őrzi a várható értéket. (Ha a kalibráció során kiugró outlierek jelentkeznének, a medián tartalék-opció — a tasks.md-ben rögzítendő.)
2. **N=3 alapértelmezett**: σ/√3 ≈ 0.58× → a 0.188-ból ~0.11 várható, ami már a cél közelében van; N=5 (→0.08) csak akkor, ha a kalibráció ezt indokolja (mérésidő-ár!).
3. **A judge temperature változatlan (0.6)**: a minták legyenek valóban függetlenek; a temp=0-s merev judge tartalék-opció, nem alap.
4. **A critique a mean-hez legközelebbi mintáé**: a GEPA reflectionnek egy konkrét, reprezentatív szöveg kell — nem az összes, nem a legszebb.
5. **Részleges hibatűrés**: 1-2 hibás hívás esetén a megmaradt minták átlaga (NEM 0.5) — különben a hibatűrés maga zajforrás lenne; mind-hiba esetén a spec 010-es FR-002 viselkedés érintetlen.
6. **A mérésidő-ár tudatos**: baseline 10 perc → ~15-25 perc N=3 mellett; GEPA-becslésekben a metric call ára 2 lokális hívásról 4-re nő (1 gen + 3 judge) — a jövőbeli futás-tervezés ezzel számol.
7. **A metrika változása ismét elavulttá teszi a baseline-t** (spec 010/011 minta): az US2 kalibráció adja az új referenciát.

## Phases

1. **Phase 1 (US1)**: `STYLE_JUDGE_SAMPLES` konstans + multi-sample `_style_score` + részleges hibatűrés + critique-választás + mock-tesztek.
2. **Phase 2 (US2)**: judge diszkrimináció újravalidálása + baseline 3× + szórás-elemzés + (ha kell: N=5/temp=0 kiértékelés) + új referencia.
3. **Phase 3 (US3)**: mini-GEPA számszerű újraértékelés + emberi döntés + docs.
