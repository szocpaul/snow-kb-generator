# Runner-riport — spec 015 (aszimmetrikus kalibráció + gate-emelés)

**Állapot: PARKOLVA a T003 MANUÁLIS KAPUnál** (emberi review-ra vár).
Utolsó frissítés: 2026-10-01T17:16:55

## Preflight — mind ZÖLD

| # | Ellenőrzés | Eredmény |
|---|---|---|
| 0 | branch `015-asymmetric-verification-gate` + spec-fájlok | OK |
| 0b | SNOW_KB_DEV_MODE=1 → task_model=local | OK |
| 0c | lokális LLM (Qwen3.8-27B, Tailscale) smoke completion | OK (HTTP 200) |
| 1 | TYPESAFE_API_KEY + minimális system_one | OK (choice=yes, conf=0.74) |
| 2 | dspy 3.4.0 + typesafe_sdk a projekt-venvben | OK |
| 3 | PDI table-API (sys_script_include, admin user) | OK (HTTP 200) |
| 4 | 014-es mérőinfrastruktúra megvan | OK |
| 5 | pytest kiinduló állapot | 349 passed |

## Phase-eredmények

### Phase 1 — Fixture + baseline (T001, T002, T004 KÉSZ)

- **T001**: `scripts_pdi/fixture_verification_gate.py` — a komponensek a PDI-n
  MÁR MEGLEVŐ rekordok (capture, NEM létrehozás). A `sys_update_xml` közvetlen
  insertje ACL-tiltott → a capture a platform standard mechanizmusa: az user
  aktuális update set-je a fixture set-re állítva (user preference), benignis
  mező touch + AZONNALI visszaállítás (a rekord-tartalom nem változott), a
  preference a végén visszaállítva az eredetire (`11226d84...`).
  - Story: **STRY0010004** ("ServiceNow oldali webhook-fogadas es KB-draft
    generalas bekotese"), Update Set: **STRY0010004** (sys_id 5cbd59e3...).
  - 13 capture-ölt komponens: 4 Script Include (PrototypeServer,
    MosaicHermesUtils, RAGResponseGenerator, CodeSigningUtil), 3 Business Rule
    ('Change Phase Events Before', 'Contract Instance', 'Choice Events'),
    3 System Property (com.snc.sdlc.scrum.pp.smclass, glide.lastplugin,
    glide.ui.session_timeout), 3 mező (kb_knowledge.u_source_story,
    rm_story.story_points, rm_story.type).
  - Dump: `artifacts/verification_fixture_components.json` (név, típus, sys_id,
    sys_updated_on) — **EZT kell review-zni a T003-ban.**
  - Incidens a futás közben: az első próba árva Story-t/Update Set-et hagyott
    (STRY0010005) és 9 felesleges dictionary capture-sort — mindkettő
    TAKARÍTVA (törölve), a dump végül a STRY0010004-re mutat.
- **T002 / SC-001**: `verify` al-parancs exit-code-os gate — **ZÖLD: 13/13 név
  spot-checkkel létezik (0 eltérés)**.
- **T004**: baseline — a jelenlegi 0.7-es threshold aszimmetrikus költsége a
  meglévő 24 példán: **4** (0 átsikló hallucináció ×10, 4 felesleges jelzés ×1;
  szimmetrikus: 4). Fájl: `artifacts/verification_asymmetric_baseline.json`.

### Phase 3 — Aszimmetrikus kalibráció (T006 KÉSZ, T005/T007/T008 KÓD kész, futtatás T003 után)

- **T006**: `eval/verification_asymmetric.py` + 9 teszt (10:1 arány, KD1;
  riport-séma; "marad" döntés indoklással) — zöld.
- **T005**: `eval/verification_labeled_015.py` (valós/variáns/fabrikált/
  típus-eltérés gépi származtatás; **magminimum: <8 jóváhagyott név → exit 2**;
  egyesítés ≥30 példa). Futtatása a T003 jóváhagyás UTÁN:
  `python -m eval.verification_labeled_015 build [--approved <json>]`
- **T007**: `eval/verification_measure_015.py` (capture/report, per-eset NYERS
  (choice, confidence) a tiszta replay-sweephez) + `eval/verification_reanchor_015.py`
  (aszimmetrikus metrikájú ReAnchor, eval-only wrapper; GEPA nincs).
- **T008**: az SC-003 regresszió-blokk a measure-riport része (romlás → decision
  "marad", config NEM módosul).

### Phase 4 — Gate-emelés (T010, T011 KÉSZ)

- **T010**: `tests/test_verification_gate_client.py` (5 teszt, FAIL-előbb) —
  közvetlen `_create_kb_article_live` hívás gated; pipeline-ban pontosan 1
  döntés + 1 recording; fail-open block módban is; a régi pipeline-függvény
  megszűnt.
- **T011**: a gate a `servicenow_client._create_kb_article_live` BELSÉJÉBE
  költözött (`_apply_verification_gate` metódus); a pipeline-rétegű hívás és a
  `VerificationBlocked` a pipeline.py-ból TÖRÖLVE (a kivétel az
  `snow_kb.errors`-ben él); `deploy/README.md` deploy-megjegyzés (a restart
  EMBERI LÉPÉS; in-flight kérések a régi úton fejeződnek be).
- A 014-es `tests/test_verification_gate.py` áthuzalozva az új architektúrára
  (valódi kliens + stubolt HTTP), a viselkedés-tesztek változatlanok.
- **pytest: 363 passed** (349 + 14 új).

### Phase 5 — Zárás (T012 KÓD kész, T013 hátravan)

- **T012**: `eval/verification_sc_gates_015.py` (SC-001..SC-005 exit-code) —
  futtatása a kalibráció után.

## MANUÁLIS KAPU — T003 (emberi teendő)

**Review-zd a dumpolt komponens-listát**: `artifacts/verification_fixture_components.json`
(furcsa/instabil nevek kiszúrése). Ha szűkítesz, add meg a jóváhagyott neveket
(pl. `{"approved_names": [...]}` JSON), a T005 azzal épít. Ha a lista
maradhat ahogy van, szólj és a teljes 13 névvel megy tovább a runner.

A T003 checkboxot a runner NEM pipálja.

## Commit-hash-ek (branch: 015-asymmetric-verification-gate)

- `1271cc4` T001+T002: PDI-natív fixture + SC-001 gate ZÖLD
- `72e8ae6` T006+T004: aszimmetrikus metrika + baseline (költség=4)
- `55be7a8` T010+T011: gate-emelés a kliensbe, 363 teszt zöld
- `5644c8a` T005/T007/T008/T012 kód (futtatás T003 után)

## Megjegyzések

- A `git add -A` behúzta a `.groma/` autoscan-fájlokat (a `groma agent-instructions`
  első scan-je hozta létre) a 55be7a8 commitban — NEM én írtam/curátorkodtam
  rajtuk; ha nem kellenek a branchre, külön commitban kiszedhetők.
- Kimi-token felhasználás: 0 (minden helyi/dev-mód; a TypeSafe jev-hívások
  csak a smoke-ban futottak, a kalibrációs capture T003 után esedékes).


---

# FOLYTATÁS a T003 jóváhagyás után (2026-10-01T17:41:27)

**Állapot: PARKOLVA a T009 MANUÁLIS KAPUnál** (a kalibrációs riport emberi review-ja).

## T003 jóváhagyás + takarítás-igazolás

- Az ember JÓVÁHAGYTA mind a 13 nevet; független ellenőrzése igazolta: a
  sys_updated_on változás a capture (touch+revert) mellékhatása, tartalmi
  módosítás NINCS, '[spec015-capture]' maradvány NINCS.
- Az árva STRY0010005 + 8b6e1927 update set már a futás közben TÖRÖLVE lett
  (a runner cleanup-ja); újraellenőrizve: mindkettő 404.

## Phase 2/3/5 eredmények (T005, T007, T008, T012)

- **T005**: `data/examples/verification_labeled_015.json` — 57 példa
  (24 régi + 33 fixture-szarmaztatott). A T005-MAG: 9 kinyerhető név (≥8 ✓) —
  4 jóváhagyott név (RAGResponseGenerator, kb_knowledge.u_source_story,
  rm_story.story_points, rm_story.type) a gate 011-es konzervatív
  kinyerő-regexei által NEM látható felületi alak → nem mérhető példaként
  (a címke továbbra is valós; ez a kinyerő dokumentált korlátja).
  FR-002-szűrő cache-alapú: a 6 régi "exists" mindegyike empírikusan
  PDI-ellenőrzött, egy sem esett ki.
- **T007**: capture (57 eset, élő jev-1.13.0 + PDI spot-check) + replay-riport
  + ReAnchor (aszimmetrikus metrika, eval-only wrapper):
  - ReAnchor: aszimmetrikus score **−0.526 → −0.281**, szimmetrikus accuracy
    0.474 → 0.719 (EXPLORATÍV fitted paraméterek).
  - Sweep (EXPLORATÍV): a jelölt threshold **0.35** (aszimmetrikus költség
    21 → 18; fp_exists 0, fn 21 → 18). A domináns hibaosztály: a kalibrált
    réteg a valós nevek írásvariánsaira "no"/"external"-t mond (ezt a
    threshold NEM javítja).
  - **Érzékenység-analízis (KD1): a threshold ÉRZÉKENY az arányra** —
    10:1-nél és 20:1-nél a 0.35 a nyerő, 5:1-nél a 0.0-0.10 sáv nyerne.
    Ez a T009 döntés kulcsadata.
  - Szimmetrikus összevetés a riportban (spec US2): 21 → 18.
- **T008 / SC-003**: régi 24 példa: aszimmetrikus költség **4 → 3** a 0.35-ön —
  NINCS romlás.
- **T012**: `eval/verification_sc_gates_015.py` — **SC-001..SC-005 MIND ZÖLD**:
  - SC-001 ZÖLD: 13/13 fixture-nél spot-check létezik (élő PDI)
  - SC-002 ZÖLD: n=57 (≥30), döntés indokolt, szimmetrikus összevetés megvan
  - SC-003 ZÖLD: nincs romlás a régi mintán
  - SC-004 ZÖLD: gate-emelés tesztek (12+9) exit=0
  - SC-005 ZÖLD: kétszeri replay byte-identikus (37007 byte)
- pytest teljes suite: **363 passed**.

## MANUÁLIS KAPU — T009 (emberi teendő)

**Review-zd a kalibrációs riportot**: `artifacts/verification_calibration_report_015.json`
(+ `artifacts/verification_reanchor_report_015.json`).

A jelölt döntés: `confidence_threshold: 0.7 → 0.35` (aszimmetrikus költség
21 → 18 a 57 példán; a régi mintán 4 → 3, nincs romlás). FIGYELEM: a jelölt
EXPLORATÍV sweep-eredmény, és az arány-érzékenység miatt (5:1-nél a 0.0
nyerne) a 10:1-es KD1-arány megerősítése is a döntés része.

- Ha JÓVÁHAGYOD: a runner a config.yaml-ba írja a 0.35-öt + az indoklás az
  Agent.md-be kerül (ez a T013 része), majd zárás.
- Ha NEM: a threshold marad 0.7, a "marad" indoklás kerül a riportba/Agent.md-be.

A config.yaml a jóváhagyásig NEM módosul (jelenleg is 0.7). A T009 checkboxot
a runner NEM pipálja.

## Commit-hash-ek (folytatás)

- `d77daa4` T005: egyesített minta (70→57 példa a kinyerhetőségi szűrő után)
- `07c2b52` T005 javítás: kinyerhetőségi szűrő + extractable variánsok
- `64166f9` T007+T008+T012: kalibráció + SC-gate-ek MIND ZÖLD


---

# ZÁRÁS (2026-10-01T17:54:16) — VÉGLEGES

**Állapot: KÉSZ.** A T009 MANUÁLIS KAPU az ember által JÓVÁHAGYVA.

## T009 döntés és végrehajtása

- A **10:1 súlyarány MEGERŐSÍTVE**; a `confidence_threshold` **0.7 → 0.35**
  a config.yaml-ban MÓDOSULT (az ember jóváhagyásával).
- **KÖTELEZŐ FELTÉTEL (az ember megjegyzése): a 0.35-ös küszöb EGYETLEN
  FP-példán nyugszik (a sweepben 0.35 a legalsó érték, ami kiszűri az 1 db
  fabrikált átcsúszót) — a threshold a KÖVETKEZŐ minta-bővítésnél
  ÚJRAMÉRENDŐ.** Az Agent.md §45 indoklásában és a config.yaml kommentjében
  is rögzítve.
- Agent.md §45 naplóbejegyzés: tények / döntések / tanulságok.

## Végső audit (az objective minden pontja)

| Követelmény | Állapot |
|---|---|
| T001-T013 implementálva dev-módban | ✅ (T003/T009 emberi kapuk: nem a runner pipálta, az ember jóváhagyta) |
| Kimi-token felhasználás | 0 (task-modell: lokális Qwen3.8-27B; a kalibráció a pinnelt jev-1.13.0 TypeSafe-hívásokkal mért — mérőinfra, nem task-modell) |
| SC-001..SC-005 exit-code-osan zöldek | ✅ `python -m eval.verification_sc_gates_015` → exit 0 (SC-001 13/13, SC-002 n=57 indokolt döntés, SC-003 4→3 nincs romlás, SC-004 gate-tesztek, SC-005 byte-identikus replay) |
| MANUÁLIS KAPUk emberi döntésre parkolva | ✅ T003, T009 — a runner egyiket sem pipálta; mindkettő emberi jóváhagyást kapott |
| Záróriport runner-report.md-ben | ✅ ez a fájl |
| pytest teljes suite | ✅ 363 passed (349 kiinduló + 14 új) |
| commit + push | ✅ origin/015-asymmetric-verification-gate |
| backlog | TASK-3 (spec 016 jelölt) változatlanul To Do — a 015-ös nem backlog-task volt |

## Összes commit (branch: 015-asymmetric-verification-gate)

- `1271cc4` T001+T002: PDI-natív fixture (STRY0010004), SC-001 gate
- `72e8ae6` T006+T004: aszimmetrikus metrika + baseline
- `55be7a8` T010+T011: gate-emelés a kliensbe
- `5644c8a` T005/T007/T008/T012 kód
- `74bf45c` runner-report (T003 parkolás)
- `d77daa4` T005: egyesített minta
- `07c2b52` T005 javítás: kinyerhetőségi szűrő
- `64166f9` T007+T008+T012: kalibráció + SC-gate-ek ZÖLD
- `7a2a02e` runner-report (T009 parkolás)
- `405ea5f` T013 zárás: config 0.35 + Agent.md §45

## Nyitott emberi lépések

- **Deploy**: a gate-emelés élesítése EMBERI lépés (`sudo systemctl restart
  snow-kb.service`) — deploy/README.md megjegyzés. A runner NEM deployolt.
- **Minta-bővítésnél**: a 0.35-ös threshold újramérendő (T009 feltétel).
- A T003/T009 tasks.md-checkboxokat az ember pipálhatja (a runner nem tette).
