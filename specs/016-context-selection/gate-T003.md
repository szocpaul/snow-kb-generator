# T003 MANUÁLIS KAPU — spec 016 baseline + zaj-leltár review

**Dátum**: 2026-10-02 (runner)
**Állapot**: VÁRAKOZIK emberi döntésre — a runner MEGÁLLT, nem folytatja a T007-et.

## A kapu tárgya (tasks.md T003)

1. A baseline + zaj-leltár review-ja.
2. **Az SC-001 token-célérték EZ ITT rögzül** (plan.md KD6 — plan-frissítéssel).
3. Ha nincs mérhető zaj → a spec megáll (a 014-es „0 találat" minta).

## Mérhető zaj VAN — a spec folytatható (runner-megállapítás)

Nincs szükség „zaj-gyártásra": a determinisztikus leltár **1825 / 8540
kontextus-token (21.4%)** zaj-jelöltet mutat a 9 gold példán.

## Baseline-összefoglaló (artifacts/context_baseline.json)

- **Modell**: lokális Qwen3.8-27B (DEV mód, `cache=False`) — a T007 after-mérés
  UGYANEZZEL fut (tasks.md T002/a).
- **Token-módszer**: llama.cpp `/tokenize` (a Qwen valódi tokenizere) — az
  after-mérés UGYANEZZEL (tasks.md T002/b).
- **rich_metric baseline átlag**: **0.8417** (per-példa: 0.8467, 0.8817,
  0.7883, 0.7583, 0.8885, 0.8274, 0.7491, 0.9575, 0.8777) — a style judge-dal
  együtt, a capture-időben mérve.
- **Összes kontextus-token** (story + update set darabok): **8540**.
- **Zaj-jelölt token** (determinisztikus heurisztika: meta-mező + near-empty):
  **1825 (21.4%)**.

### Zaj-leltár szerkezete (per-példa, mind a 9 goldon azonos minta)

| Darab | Token/példa | Jelleg |
|---|---|---|
| `story:number` | 14 | azonosító-meta |
| `story:state` | 7 | workflow-meta |
| `story:assigned_to` | 8 | személy-meta |
| `story:assignment_group` | 8 | csapat-meta |
| `story:work_notes` | 33–193 | dev-napló (hide VAGY summarize-jelölt) |
| `story:comments` | 30–82 | megjegyzés (hide VAGY summarize-jelölt) |

- **Nyilvánvaló hide-jelöltek** (number/state/assigned_to/assignment_group):
  37 token/példa × 9 = **333 token (3.9%)**.
- **Summarize-jelöltek** (work_notes/comments): ~1492 token; 60–70%-os
  tömörítéssel további ~900–1000 token megtakarítás várható.
- Update set payload csak a gold-5-ben van (3536 kontextus-tokenéből 2971 az
  US); a kapcsolódó-cikk zaj a gold datasetben nem mérhető (nincs
  related_articles_context) — ez a baseline korlátja, a riportban jelölve.

## Javasolt SC-001 célérték (az EMBER rögzíti)

**Javaslat: ≥ 5% kontextus-token-csökkenés** a gold példákon, minőség-romlás
nélkül (SC-002 mellett).

Indoklás: a nyilvánvaló hide-jelöltek önmagukban 3.9%-ot adnak (recall-kockázat
nélkül), a summarize-sáv e fölé hoz várhatóan 6–10%-ot. Az 5% konzervatív,
elérhető, és nem léggomb — a baseline-leltárból származik. A teljes prompt
(template + signature-többlet) ~3200–8100 token/példa, így a KONTEXTUSRA mért
5% a teljes prompton ~1–2%-nak felel meg — a riport mindkét számot mutatja.

**Alternatívák**: 3% (csak az admin-hide biztosra véve) | 10% (a summarize-sáv
teljes kihasználásával — kockázatosabb az SC-002-re).

## Döntési opciók

- **JÓVÁHAGYOM + célérték** (pl. „5%") → a runner rögzíti a plan.md KD6-ot és
  az `artifacts/context_sc001_target.json`-t, majd T007-T008 (mérés +
  recall-gate) → T009 kapu.
- **MÁS CÉLÉRTÉK** → ugyanaz a folyamat a megadott értékkel.
- **MEGÁLL a spec** → indoklással a runner-reportba kerül, a T004-T006 kód
  `enabled=false` konfiggal inaktív marad.

## Bizonyíték-fájlok

- `artifacts/context_baseline.json` (riport, replay-ból byte-identikus)
- `artifacts/context_baseline_generations.json` (nyers generálások + usage)
- `artifacts/context_baseline_tokens.json` (per-darab token-leltár)
- `artifacts/context_baseline_metrics.json` (rich_metric + style judge pontok)
