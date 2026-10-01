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
