# spec 016 runner-report — KONTEXTUS-VÁLOGATÁS A CIKKGENERÁLÁSHOZ

**VÉGÁLLAPOT**: ✅ **LEZÁRVA** — a spec a T012 MANUÁLIS KAPUnál emberi döntéssel
**MEGÁLLT** (opció (c), 2026-10-02): a feature `enabled=false`-szal, inaktívan,
teljes mérési nyomvonallal és egy valós gyökéroka-javítással (state-fix) zárult.
Ez a spec-cél szerinti elfogadott végállapot: a „measured, not claimed" elv
szerint a megállás is teljes értékű kimenet, ha a plafon számszerű és az ok
azonosított.

**Branch**: `016-context-selection` | **Futási mód**: DEV (SNOW_KB_DEV_MODE=1,
lokális Qwen3.8-27B; Kimi-token felhasználás nélkül) | **Dátum**: 2026-10-02

## SC-gate-ek végső állása (`python -m eval.context_sc_gates_016` → exit 0)

| Gate | Állapot | Számok |
|---|---|---|
| SC-001 (költség) | 🔴 **DOKUMENTÁLT PIROS (elfogadott, T012)** | mért 0.45% teljes prompton vs ≥5% cél; költség-korlátos plafon 0.0%; state-fixszel ~1.1–1.2% — a cél minőség-kockázat nélkül nem érhető el (az SC-002 elsődlegessége húzta meg) |
| SC-002 (minőség) | 🟢 ZÖLD | rich_metric 0.8417 → 0.8511, párosított CI95 [−0.029, +0.038] (átfedi a 0-t) |
| SC-003 (recall) | 🟢 ZÖLD | 0/9 kiesés, exit-code-os gate |
| SC-004 (fail-open) | 🟢 ZÖLD | 23 teszt zöld (SDK-hiba → mind show; alacsony confidence → show; story-core sosem hide) |
| SC-005 (replay) | 🟢 ZÖLD | a hatásmérés riport kétszer futtatva byte-identikus |
| SC-006 (kalibráció) | 🟢 ZÖLD | n=56 (≥20); sweep-döntés exploratív; **T012 végső döntés: „marad" (0.25)**; config változatlan; safety floor érintetlen |

## Per-phase eredmények

### Phase 1: Setup + Baseline
- **T001** ✅ `context_selection` config-blokk + 5 config-teszt.
- **T002** ✅ Baseline: 9 gold, lokális Qwen, cache=False; **8540 kontextus-token,
  1825 zaj-jelölt (21.4%)**, rich_metric avg **0.8417**; token-módszer: llama.cpp
  `/tokenize`; replay-ból byte-identikus.
- **T003** ✅ MANUÁLIS KAPU — **jóváhagyva**: SC-001 = ≥5% a TELJES PROMPTON
  (LM usage prompt_tokens), SC-002 elsődleges.

### Phase 2: US1 – a válogató modul
- **T004/T005/T006** ✅ teszt-előbb sorrendben: `context_selection.py`
  (darabolás + Score-döntés pinnelt jev-1.13.0-val + Python-policy `<`
  operátorral + fail-open show + FR-004 story-core védelem + summarize a lokális
  Qwenen + jev-recording) + pipeline-bekötés (a 014/015 gate az EREDETI
  kontextust kapja; program.py/program.json érintetlen).

### Phase 3: US2 – Hatásmérés
- **T007** ✅ **INERT válogatás** (0 hide / 0 summarize / 92 show): teljes-prompt
  csökkenés **0.45%**; minőség nem romlott; kontextus-token +1.4% (JSON
  újraépítési többlet).
- **T008** ✅ recall-gate **0/9 kiesés**.
- **T009** ✅ MANUÁLIS KAPU — **jóváhagyva a folytatás** a T011 kalibrációval
  (kötelező elemek: plafon-szám, távolság a céltól, érzékenység, „marad" ág).

### Phase 4: US3 – Kalibráció
- **T010** ✅ 56 címkézett darab (39 noise / 14 borderline / 3 relevant),
  per-darab indokolt review, commitolva.
- **T011** ✅ ReAnchor (−0.2946 → −0.2946, nincs javulás) + sweep: a 0.25→0.05
  „javulás" zajszintű (16.5→16.0, recall-hiba 0, ratio-érzéketlen).
  **Plafon-táblázat**: nyers 11.1% / költség-korlátos 0.0% / state-fixszel
  ~1.1–1.2%. **Gyökéroka-finding**: a production `story_context` FELFÚJJA a
  Score-t (zaj: 0.86–0.99 ctx-tel vs 0.00–0.03 ctx nélkül, conf 0.93–1.00).
- **T012** ✅ MANUÁLIS KAPU — **emberi döntés: (c) MEGÁLLÁS**: a küszöb MARAD
  0.25 (nincs config-módosítás); a **state-fix BEKERÜLT** (a `_score_piece`
  state-je már nem tartalmazza a core-szöveget + teszt); a feature
  `enabled=false` marad; SC-001 dokumentált PIROS; Agent.md §48 naplóbejegyzés.

### Phase 5: Zárás
- **T013** ✅ SC-001..SC-006 gate-ek exit-code-dal (ld. fenti tábla, exit 0);
  teljes pytest-suite **415 passed** (`env -u SNOW_KB_DEV_MODE`);
  Agent.md §48 naplóbejegyzés; backlog **TASK-3 lezárva** (Done, a dokumentált
  kimenetellel); commit + push a `016-context-selection` branchre.

## Kulcs-tanulságok (a teljes jelentés: Agent.md §48)

1. A „nincs mérhető hatás" is teljes értékű spec-kimenet — a plafon számszerű,
   a gyökéroka azonosított, a megállás dokumentált.
2. A probe-feltétel (mi kerül a state-be) a döntés minőségének része — a
   kalibrációs wrapper és a production state legyen tudatosan egyforma.
3. A kontextus-zaj ≠ prompt-zaj: a kontextus 21.4%-a zaj-jelölt, de a kontextus
   a teljes prompt ~23%-a — a célérték a gate nevezőjéhez kötött.

## Commit-hash-ek (016-context-selection branch)

- `ee0d6e4` T001 config-blokk + tesztek
- `8cbec87` T004+T005+T006 modul + bekötés (414 zöld)
- `3502be3` T002 baseline + eval-scriptek
- `2485fc8` T003 gate-riport
- `da4e7ab` T003 jóváhagyva: SC-001 target (teljes prompt 5%)
- `9b6b4d1` T008+T010 recall-gate + címkézett minta
- `0b9c90d` T007 hatásmérés (INERT)
- `3b4138a` T009 gate-riport
- `c88f2e1` T011 kalibráció + plafon + gyökéroka
- `053eb5b` T012 gate-riport
- `23fc303` T012 jóváhagyva: state-fix + teszt (415 zöld)
- T013 záró-commit: SC-gate-kód (SC-001 dokumentált PIROS + SC-006 T012-végső
  ellenőrzés), kalibrációs riport T012-döntéssel, Agent.md §48, ez a riport
