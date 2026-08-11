# Tasks: Style Judge zajcsökkentés (multi-sample pontozás)

**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

## Phase 1: Multi-sample pontozás (US1)

- [x] T001 [US1] `STYLE_JUDGE_SAMPLES = 3` konstans az `eval/metric.py`-be (tesztek felüldefiniálhatják — FR-002)
- [x] T002 [US1] `_style_score()` átírása: N judge-hívás, a sikeres minták átlaga a pontszám; a critique a mean-hez legközelebbi mintáé (FR-003); clamp megmarad
- [x] T003 [US1] Részleges hibatűrés: 1-2 sikertelen hívás → mean(maradék) + warning; mind hiba → (0.5, "") (FR-001)
- [x] T004 [US1] Tesztek (mock judge): (a) [0.4, 0.6, 0.8] → 0.6; (b) 2 hiba + 1 siker → a sikeres érték + warning; (c) mind hiba → 0.5; (d) critique a mean-hez legközelebbi mintából; (e) a rich_metric axes továbbra is 5 tengely

## Phase 2: Kalibrációs igazolás (US2)

- [x] T005 [US2] Judge diszkrimináció újravalidálása (FR-005): gépies teszt-ikon < 0.4, KB0010015 > 0.7
- [x] T006 [US2] Baseline 3× újramérés (`python -m eval.baseline --model local --output runs/baseline{,_recheck,_recheck2}.json`, `cache=False` — FR-004) — preflight a llama.cpp-re a futások előtt
- [x] T007 [US2] Szórás-elemzés: tengelyenkénti min–max táblázat; **style szórás ≤ 0.10** (SC-002) — ha nem teljesül: N=5 vagy temp=0 kiértékelése, a döntés dokumentálva; az új baseline-referencia rögzítése

## Phase 3: Mini-GEPA újraértékelés + zárás (US3)

- [x] T008 [US3] Számszerű újraértékelés a tasks.md-ben: mért szórás vs mini-GEPA várható nyereség ("javulás > mért szórás + marge" küszöb) — a döntés az emberé
  - **VÉGLEGES DÖNTÉS (emberi, 2026-08-11): a mini-GEPA-t KÉSŐBB futtatjuk — most nincs rá szükség, a pipeline jelenlegi állapota jó. Az elhalasztás korábbi (zaj-alapú) oka a spec 012-tel megszűnt: a futás bármikor indítható, amikor szükség van rá (~5-7 óra, éjszakai futásként, autonóm runner + infra-watcher felállással, a spec 010-es minta szerint).**
- [x] T009 [US3] Agent.md új szekció + README ha kell + commit, push


---

## T007 eredmények (2026-08-11, N=3 multi-sample judge, cache=False, preflight OK)

Preflight: llama.cpp `/health` 200 + smoke-generálás 0.3 s — a szerver élt mindhárom futás előtt.

### Tengelyenkénti min–max táblázat (3 azonos baseline-futás tengely-átlagai)

| tengely | run1 | run2 | run3 | min | max | **szórás** | régi (1-mintás) |
|---|---|---|---|---|---|---|---|
| structure | 0.875 | 0.917 | 0.917 | 0.875 | 0.917 | 0.042 | 0.042 |
| content | 0.667 | 0.699 | 0.660 | 0.660 | 0.699 | 0.039 | 0.070 |
| template | 0.750 | 0.750 | 0.750 | 0.750 | 0.750 | 0.000 | 0.000 |
| hallucination | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 0.000 | 0.000 |
| **style** | 0.513 | 0.508 | 0.525 | 0.508 | 0.525 | **0.017** | **0.188** |
| összesített | 0.751 | 0.768 | 0.762 | 0.751 | 0.768 | 0.018 | ~0.055 |

**SC-002 TELJESÜL: style szórás 0.188 → 0.017 (cél: ≤ 0.10) — a várt ~0.11-nél is jobb** (a per-run tengely-átlagolás tovább csökkenti a varianciát). Az N=5 / temp=0 tartalék-opciókra NEM volt szükség (plan Key Decision #2 szerinti első opció sem kellett).

Módszertani megjegyzés: a per-PÉLDA style szórás továbbra is 0.20–0.27, de ebben a task-modell generálási varianciája (temp=0.6, a cikkek futásonként eltérnek) és a judge-zaj elkülönítetlenül szerepel — az SC-002 az eredeti kalibrációval azonos módszerrel, a tengely-ÁTLAGOK szórására teljesül. Judge-diszkrimináció (T005/SC-003): gépies teszt-ikon 0.017 (< 0.4 ✅), KB0010015 0.950 (> 0.7 ✅) — `runs/t005_judge_revalidation.json`.

### Új baseline-referencia (spec 012 utáni, N=3 judge)

`runs/baseline.json` (2026-08-11T12:48): **átlag 0.751**; structure 0.875 / content 0.667 / template 0.750 / hallucination 1.000 / style 0.513. A 2026-08-11 délelőtti (1-mintás judge-os) számok ELAVULTAK; mentve: `runs/baseline_pre_spec012.json`, `runs/baseline_recheck_pre_spec012.json`, `runs/baseline_recheck2_pre_spec012.json`. Szórás-elemzés: `runs/t007_spread_analysis.json`.

## T008 — Mini-GEPA számszerű újraértékelés (a DÖNTÉS az emberé, GEPA futtatás NEM történt)

**Küszöb (spec US3 acceptance 1):** egy mini-GEPA eredménye akkor értelmezhető, ha **javulás > mért szórás + marge**.

| mennyiség | érték |
|---|---|
| Mért összesített szórás (3 futás, min–max) | **0.018** |
| Mért style-tengely szórás | **0.017** |
| Marge (konzervatív, spec 010 T012-i ±0.05 zaj-sáv mintájára, de az új zajszinthez igazítva) | 0.02 |
| **Értelmezhetőségi küszöb (0.018 + 0.02)** | **≈ 0.04** |
| Mini-GEPA várható nyereség (spec 011 T009 becslés) | +0.02 – +0.05 |

**Olvasat:** az elhalasztás eredeti oka (zaj 0.188 > nyereség 0.02–0.05) MEGSZŰNT — a zaj most 0.018. A várható nyereség felső vége (+0.05) már a küszöb felett van (0.05 > 0.04), az alsó vége (+0.02) még alatta. Tengely-szinten a helyzet erősebb: egy style-célzó javulás a korábbi GEPA tapasztalat alapján +0.15–0.20 nagyságrendű volt (T012: style 0.45–0.46 → 0.60–0.65), ami a 0.017-es style-zaj mellett ~10× jel/zaj arány. **A mini-GEPA kimenetele immár értelmezhető, ha a mért javulás ≥ ~0.04 (vagy dupla méréssel igazolt).**

**Nyitott emberi döntés:** mini-GEPA futtatása (becsült idő: a metric call ára 2→4 lokális hívásra nőtt — 1 gen + 3 judge —, a spec 010-i 200 call-os futás ~3.5 órája várhatóan ~5-7 óra) VAGY további halasztás (pl. valset-bővítés először). A döntés és indoklás rögzítendő: ⬜ DÖNTÉS: ______________ (ember)
