# T004 baseline-leltár: komponensnevek az instance ellen

Dátum: 2026-09-30T16:09:37.472929+00:00  |  Instance: dev432044.service-now.com

| Verdict | Darab |
|---|---|
| exists | 6 |
| not_found | 26 |
| error | 0 |
| in_update_set | 5 |
| whitelisted_generic | 12 |

## Nem létező nevek (a probléma nagysága)

- `JiraInboundUtils` (gold-1)
- `Escalated` (gold-2)
- `JiraIntegrationUtils` (gold-2)
- `User Not Found` (gold-3)
- `Tax code I2 does not exist` (gold-4)
- `Withdrawn` (gold-6)
- `SolMan: Sync CD State to CTASK Closure Readiness` (gold-6)
- `SolMan: Fix CD State Inconsistencies` (gold-6)
- `SolMan` (gold-6)
- `aldi.com` (gold-7)
- `interface.solman` (gold-7)
- `aldi.solman` (gold-7)
- `SolMan` (gold-7)
- `ChTask` (gold-7)
- `FrameWork` (gold-7)
- `aldi.integration.almex.config.matrix` (gold-8)
- `GetReturns` (gold-8)
- `ConfirmReturns` (gold-8)
- `ALDI S4 OData Outbound` (gold-9)
- `ALDI: CHG Scheduled - Push Dates to S4` (gold-9)
- `ALDIS4ProjectInterface` (gold-9)
- `UpdateProjectDates` (gold-9)
- `ProjectMilestone` (gold-9)
- `JiraInboundWebhook` (generated-1)
- `JiraInboundUtils` (generated-1)
- `JiraIntegrationUtils` (generated-2)

## Vakfolt-elemzés (a T005 review segédlete)

Mind a 26 not_found jelölt **szerepel a forrás-story-ban is** (`_component_verified`
igaz) — vagyis a 011-es story-alapú tengely NEM fogja meg őket; pontosan ez a
spec által leírt vakfolt. DE a nyers lista több külön osztályt tartalmaz:

| Osztály | Példák | Megjegyzés |
|---|---|---|
| Külső (SolMan/SAP) rendszer objektumai | `aldi.solman`, `interface.solman`, `SolMan`, `ALDI S4 OData Outbound`, `GetReturns`, `ConfirmReturns`, `UpdateProjectDates`, `ProjectMilestone` | **Out of scope** a spec szerint ("Nem-ServiceNow entitások") — ezek SOSEM léteznek a SNOW instance-ben, mégis legitim tartalom. A gate-nek ezeket kezelnie kell (különben false positive-özön). |
| Workflow-állapot / UI-szöveg idézőjelben | `Escalated`, `Withdrawn`, `User Not Found`, `Tax code I2 does not exist` | Nem komponensnevek — a jelölt-kinyerés false positive-jai (a T007-nek finomítania kell a típus-tippel). |
| Valósnak TŰNŐ SNOW-komponensnevek | `JiraInboundUtils`, `JiraIntegrationUtils`, `JiraInboundWebhook`, `ALDIS4ProjectInterface`, `ChTask`, `FrameWork`, `aldi.integration.almex.config.matrix`, SolMan-BR-nevek | **Ez a tényleges probléma-mag**: a story/payload SolMan-oldali vagy elírt neveket hoz, a cikk SNOW-komponensként írja le őket, az instance-ben nincsenek. |

**A frissen generált minta (3 cikk, lokális Qwen, DEV mód)** 3 ilyen nevet
tartalmaz (`JiraInboundWebhook`, `JiraInboundUtils`, `JiraIntegrationUtils`) —
a hallucináció MA is reprodukálható, nem csak történeti gold-jelenség.

A blind-spot részlista gépi formában: `artifacts/component_baseline_blindspot.json`.
