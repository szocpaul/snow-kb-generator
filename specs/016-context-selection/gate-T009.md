# T009 MANUÁLIS KAPU — spec 016 hatásriport review

**Dátum**: 2026-10-02 (runner)
**Állapot**: VÁRAKOZIK emberi döntésre — a runner MEGÁLLT.

## A kapu tárgya (tasks.md T009)

A hatásriport review-ja — ha a minőség romlott vagy a recall kiesett, a spec
NEM megy tovább production-felé.

## Főszámok (artifacts/context_selection_report.json)

| Metrika | Baseline | Válogatott | Delta |
|---|---|---|---|
| Kontextus-token (story+US) | 8540 | 8657 | **+1.4%** (nőtt!) |
| Teljes prompt (LM usage) | 37550 | 37380 | **−0.45%** |
| rich_metric átlag | 0.8417 | 0.8511 | +0.009, CI95 [−0.029, +0.038] |
| Recall (valós nevek) | — | 0/9 kiesés | ✅ |
| Verdict-eloszlás | — | 0 hide / 0 summarize / 92 show | — |

## Őszinte megállapítások (NEM „szépre hangolt")

1. **A válogatás INERT a jelenlegi küszöbökön** (hide_below=0.25,
   summarize_below=0.60, min_confidence=0.6): mind a 92 darab show. Az SC-001
   cél (≥5% a teljes prompton) így **PIROS** a jelenlegi configgal — a mért
   0.45% a prompt-szintű zajingadozás (temp 0.6) nagyságrendje.
2. **A minőség NEM romlott** (SC-002 zöld): a delta CI95-je átfedi a 0-t; a
   +0.009 a zaj-sávon belül van. A recall-gate 0/9 (SC-003 zöld). A riport
   kétszeri futtatása byte-identikus (SC-005 mechanika zöld).
3. **A Score-modell magasan pontoz** (kompromittált szelekciós képesség a
   jelenlegi rubrikával): az admin-meta darabok (number/state) 0.93–0.97
   relevanciát kaptak. Az assigned_to/assignment_group darabokon a relevancia
   ALACSONY (0.22–0.49), de a confidence is alacsony (0.0–0.33) → a fail-open
   safety floor (min_confidence=0.6) show-ra kényszeríti őket.
4. **A kontextus-token 1.4%-kal NŐTT**: a JSON story újraépítés
   (fragmentekből objektum) minimális formázási többletet ad; hide nélkül ez
   nettó többlet. (A darabolás-on-tokenizálás és az újraépített szöveg
   tokenizálása közti különbség — a riport az újraépítettet méri.)
5. **Amit ez a mérés mégis ad**: az identikus kontextusú kétszeri generálás
   rich_metric-ingadozása (0.8417 vs 0.8511, per-példa CI95 ±0.03) — ez a
   lokális Qwen rerun-zaj-sávja, az SC-002 kalibráció alapja.

## A következő lépés kérdése

A tasks.md szerint a következő fázis a T010 (címkézett minta — **már kész,
56 darab**) + T011 ReAnchor-kalibráció a hide-küszöbre + T012 kapu.

**Előre látható nehézség (a runner jelzi, nem dönt):** a kalibrációs sweep CSAK
a hide_below-t mozgathatja (a min_confidence safety floor nem kalibrálható).
A selection-capture adatai szerint az alacsony-relevanciás darabok többségénél
a confidence is a padlón van → lehet, hogy a hide_below-sweep EGYEDÜL nem tud
5%-ot (a fail-open show-k változatlanok maradnak). A kalibrációs riport ezt
számszerűen megmutatja; ha így van, az a T012 kapu tárgya lesz (pl. célérték-
revízió vagy a rubrika/kérdés újratervezése — az újraindítási feltétel).

## Döntési opciók

- **FOLYTATÁS a T011 kalibrációval** (a minőség és a recall rendben, a spec
  mehet tovább) → a runner lefuttatja a ReAnchor + sweep + riportot, majd a
  T012 kapunál ismét megáll.
- **MEGÁLLÍTÁS** → a feature `enabled=false`-szal inaktív marad, a runner-report
  lezárja a specet az itteni eredményekkel.

## Bizonyíték-fájlok

- `artifacts/context_selection_report.json` (a fenti számok forrása, replay-ból
  byte-identikus)
- `artifacts/context_selection_capture.json` (per-darab verdict + relevance +
  confidence — a „magas Score" állítás ellenőrizhető)
- `artifacts/context_selection_measurement.jsonl` (a system_one döntések
  recordingja, replay-kompatibilis)
- `eval/context_recall_gate.py` kimenet: 0/9 kiesés
