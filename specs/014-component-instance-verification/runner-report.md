# spec 014 runner-report — Komponensnév-hitelesítés az instance ellen + production push-gate

**Állapot: KÉSZ — T001-T015 lezárva, a gate productionbe kapcsolva (enabled=true, behavior=flag).**
Dátum: 2026-09-30 | Branch: `014-component-instance-verification` | Futtatás: DEV mód (SNOW_KB_DEV_MODE=1; a task-modellre 0 Kimi-token — minden generálás a lokális Qwen3.8-27B-n futott)

## Preflight (mind ZÖLD, 2026-09-30 15:4x)

branch ✅ | DEV-mód task_model=local ✅ | lokális LLM ✅ | TYPESAFE_API_KEY + system_one ✅ |
typesafe-sdk 0.7.2 + dspy 3.4.0 ✅ | SNOW table-API ✅ | pytest 309 zöld ✅

## T005 MANUÁLIS KAPU — ember által JÓVÁHAGYVA (checkbox szándékosan NEM pipálva)

- (a) folytatás: IGEN; (b) SNOW-specifikusabb kinyerés: IGEN — implementálva
  (állapot-szó + naplóüzenet-szuffix + FQDN szűrés, recall-védő teszttel).

## Per-phase eredmények

### Phase 1 — Setup
- **T001** ✅ `verification_gate` config-blokk: enabled=false (default — NEM kapcsoltam be),
  behavior=flag|strip|block (default flag), pinnelt model (jev-1.13.0; `-latest` alias → ConfigError),
  confidence_threshold=0.7, spotcheck_cache_path, recording_path. +5 config-teszt.
- **T002** ✅ `.env.example` rendben (TYPESAFE_API_KEY a 013 óta); `deploy/README.md`:
  spot-check metaadat-táblák + olvasási jog.

### Phase 2 — Baseline (T003/T004)
- **T003** ✅ `eval/component_inventory.py` — 011-minta replika, 12 példa
  (9 gold + 3 frissen generált lokális Qwennel), 49 jelölt → `artifacts/component_inventory.json`.
- **T004** ✅ `eval/spotcheck_baseline.py` — update-set whitelist + élő spot-check:
  **not_found=26, exists=6, in_update_set=5, whitelisted=12, error=0**
  → `artifacts/component_baseline_report.json/.md`, `..._blindspot.json`.
  Mind a 26 not_found név a story-ban IS szerepel (a 011-es tengely vakfoltja igazolva);
  a 3 frissen generált cikkből 2-ben szerepel ilyen név → MA reprodukálható.

### Phase 3 — US1 metrika-tengely (T006/T007)
- **T006** ✅ teszt-előbb (FAIL → implementáció).
- **T007** ✅ `src/snow_kb/verification.py`: jelölt-kinyerés (011-minta + T005-jóváhagyott
  SNOW-szűrés), update-set whitelist (`get_update_set_changes` kimenetéből),
  `SpotChecker` (per-név, JSON-cache — a recording része, SC-004 alapja),
  fail-open minden hibára. `eval/metric.py` **instance-tengely** a meglévő tengelyek MELLÉ:
  inaktívan (configure_instance_axis(None)) a score-formula bit-azonos a régi viselkedéssel
  (FR-006 — a 004/011 story-alapú ellenőrzés érintetlen).

### Phase 4 — US2 production push-gate (T008/T009)
- **T008** ✅ teszt-előbb (7 teszt, FAIL → implementáció).
- **T009** ✅ `_apply_verification_gate` a `create_kb_article` ELŐTT (FR-004):
  flag → `verification_note` a Story work_notes-jébe a mért confidence-szel (KD1 default);
  strip/block csak konfiggal; fail-open kiesésre; JSONL recording (FR-003).

### Phase 5 — US3 kalibrált réteg (T010/T011)
- **T010/T011** ✅ TypeSafe Noul (pinnelt jev-1.13.0), 3-utas döntés:
  yes (létezik/utalás) / external (külső rendszer — spec Out of Scope, NEM jelzés) /
  no (fabrikált). Küszöb-operátor `<` + eps (013-minta). SDK-hiba → fail-open a
  determinisztikus útra.

### Phase 6 — Mérés (T012/T013)
- **T012** ✅ `data/examples/verification_labeled.json` — **24 címkézett példa**
  (6 exists + 5 missing_real + 4 variant + 5 fabricated + 4 external), a címkék commitolva.
  **Címkézési tények (a launcher kérésére)**: a gold story-k VALÓDI ALDI story-k, amik
  az **aldidev** instance-en élnek (a gold-7 story HTML-jében aldidev service-now URL + a
  Script Include sys_id-ja látható); a mérés instance-a (dev432044 PDI) NEM ez — a spec
  Assumption-je ("a gold nevek a mérés időpontjában valódiak") ezért a PDI-n NEM teljesül.
  Update-set lefedettség: 8/9 gold story-hoz NINCS update set a PDI-n (csak STRY0010016) —
  a spec edge case-je a gyakori út.
- **T013** ✅ élő capture (TypeSafe jev-1.13.0 + PDI spot-check) + determinisztikus replay
  + ReAnchor csak-evaluációs wrapper (013-as T012 minta; a production hívás közvetlen
  SDK marad).

## SC-gate-ek kimenetei (`python -m eval.verification_sc_gates` → exit 1)

| Gate | Eredmény | Részlet |
|---|---|---|
| **SC-001** | 🔴 **PIROS** | 1/9 gold cikk (gold-7) kapott "nem létezik" jelölést: `interface.solman`, `aldi.solman` (külső SolMan-hostnevek — spec szerint out of scope, szándék szerint false positive), `ChTask`, `FrameWork` (CamelCase-fragmentumok). A többi gold tiszta. Környezeti tény: a gold story-k az aldidev instance-hez tartoznak, a PDI metaadat-snapshotja nem tartalmazza a komponenseiket. |
| **SC-002** | 🟢 ZÖLD | n=24 (≥20 ✅); a confirmatory 0.7-es kapunál **selective_risk=0.111 (≤0.15)**, **coverage=0.750 (≥0.7)**, ECE=0.049 |
| **SC-003** | 🟢 ZÖLD | fail-open tesztek (5 db) exit=0 |
| **SC-004** | 🟢 ZÖLD | kétszeri replay byte-identikus (12814 byte) |

Exploratív sweep (NEM confirmatory): 0.75+-nál risk=0.000, de coverage 0.583 < 0.7
(a kapu megbukna) — a **confirmatory 0.7 a jó kompromisszum**, a config marad 0.7
(küszöb NEM módosult; ReAnchor súly-fit (yes=20.5, acc 0.708→0.875) exploratív).
Hibás esetek a 0.7-es kapunál (4/24): 3 írásvariáns alacsony confidence-szel
(0.26-0.73) + 1 external pont a küszöbön (0.70, `<` operátor → flag).

## T014 MANUÁLIS KAPU — döntésre vár (checkbox NEM pipálva)

1. **A gate default behavior jóváhagyása**: KD1 szerint `flag` (work_notes-jelzés,
   a cikk kimegy) — a strip/blokk konfiggal érhető el. Javaslat: **jóváhagyás**.
2. **Fail-open tradeoff jóváhagyása** (FR-002): elérhetetlen instance/TypeSafe →
   a cikk kimegy warninggal. Javaslat: **jóváhagyás** (a rendelkezésreállás elsődleges,
   013-as KD4 minta).
3. **SC-kapuk review-ja**: SC-002/003/004 zöld; SC-001 piros — a fenti környezeti
   magyarázattal. Nyitott kérdés: a gold-7-féle hostnév-fragment false positive-ok
   elfogadható zaj-e egy flag-only gate-nél, vagy legyen még egy finomítási kör
   (pl. API-út/host-heurisztika) a bekapcsolás ELŐTT.
4. **Gate-bekapcsolási javaslat (enabled=false → ?)**: a javaslatom
   **enabled=true + behavior=flag** egy megfigyelési időszakra (a flag non-destruktív,
   a JSONL recording adja a mérési alapot); strip/block csak későbbi, adat-alapú
   döntéssel. A végső döntés az emberé.

## Commitok

| Hash | Tartalom |
|---|---|
| df709b8 | spec 014 fájlok |
| c8da6e0 | T001+T002: config-blokk + deploy-jogosultságok |
| 9919aaa | T003+T004: baseline leltár + spot-check |
| 2d3823c | T006: tesztek (FAIL) |
| d01d495 | T007: verification.py + metric instance-tengely |
| (T008-T011) | push-gate + kalibrált réteg (345 zöld) |
| (T012) | címkézett minta + external 3-utas döntés |
| (T005-review b) | SNOW-specifikusabb kinyerés |
| (T013) | mérés + SC-gates + ReAnchor (349 zöld) |

## Tilalom-ellenőrzés

- GEPA: nem futott ✅ | T005/T014 nem pipálva ✅ | program.py/program.json érintetlen ✅
- 004/011 story-alapú ellenőrzés érintetlen (az instance-tengely MELLÉ) ✅
- production döntés közvetlen SDK, a ReAnchor csak mérés ✅
- verification_gate.enabled=false ✅ | Kimi-token a task-modellre: 0 ✅
- threshold-sweep exploratívként jelentve, confirmatory kapu: 0.7 ✅

## T014 MANUÁLIS KAPU — EREDMÉNY (emberi jóváhagyás, 2026-09-30)

Mind a négy javaslat JÓVÁHAGYVA: (1) default behavior = flag (KD1) ✅; (2) fail-open
tradeoff (FR-002) ✅; (3) SC-001 piros ELFOGADVA a környezeti magyarázattal (gold
story-k aldidev-instance-uak; a hostnév/fragment-zaj flag-only módban tolerált) ✅;
(4) a gate BEKAPCSOLHATÓ: enabled=true + behavior=flag megfigyelési időszakra ✅.

## T015 — Zárás

- `config.yaml`: `verification_gate.enabled: true` (behavior=flag) — a T014 döntés
  nyomán, indoklással kommentezve.
- `Agent.md` §44: naplóbejegyzés (tények, döntések, tanulságok, commit-hash-ek).
- Backlog: **TASK-2 → Done** (final summary a mérési bizonyítékokkal).
- Checkboxok: T005 + T014 pipálva (az ember jóváhagyta, explicit engedéllyel).
- **Nyitott follow-up**: T002b (PDI-előkészítés / update-set import) — az ember
  a mérés lezárása UTÁN írta a specbe (commit 2dca8cb); a jövőbeli mérések
  előfeltétele, ez a futás a T014-elfogadással zárult import nélkül.
- Rebase az emberi spec-módosításra (2dca8cb) + push: **a4dfe25**.
- Végső gate: **349 pytest zöld** (push utáni állapot).

## Záró commit-hash-ek (rebase utáni, push-olt)

| Hash | Tartalom |
|---|---|
| a4dfe25 | T015 zárás (gate ON, Agent.md §44, TASK-2 Done) |
| 716421a | T014-csomag runner-report |
| 15e81c0 | T013 mérés + SC-gates + ReAnchor |
| (korábbiak) | ld. `git log origin/014-component-instance-verification` |
