# T004 baseline inventory: the component names against the instance

Date: 2026-09-30T16:09:37.472929+00:00  |  Instance: prod.service-now.com

| Verdict | Count |
|---|---|
| exists | 6 |
| not_found | 26 |
| error | 0 |
| in_update_set | 5 |
| whitelisted_generic | 12 |

## Non-existent names (the size of the problem)

- `JiraInboundUtils` (gold-1)
- `Escalated` (gold-2)
- `JiraIntegrationUtils` (gold-2)
- `User Not Found` (gold-3)
- `Tax code I2 does not exist` (gold-4)
- `Withdrawn` (gold-6)
- `SolMan: Sync CD State to CTASK Closure Readiness` (gold-6)
- `SolMan: Fix CD State Inconsistencies` (gold-6)
- `SolMan` (gold-6)
- `example-service.com` (gold-7)
- `interface.solman` (gold-7)
- `integration.solman` (gold-7)
- `SolMan` (gold-7)
- `ChTask` (gold-7)
- `FrameWork` (gold-7)
- `integration.vendor.config.matrix` (gold-8)
- `GetReturns` (gold-8)
- `ConfirmReturns` (gold-8)
- `ERP OData Outbound` (gold-9)
- `Milestone Dates Push to ERP` (gold-9)
- `S4ProjectInterface` (gold-9)
- `UpdateProjectDates` (gold-9)
- `ProjectMilestone` (gold-9)
- `JiraInboundWebhook` (generated-1)
- `JiraInboundUtils` (generated-1)
- `JiraIntegrationUtils` (generated-2)

## Blind spot analysis (a helper for the T005 review)

All 26 not_found candidates **also appear in the source story** (`_component_verified`
is true) — so the 011 story-based axis does NOT catch them; this is exactly the
blind spot described by the spec. BUT the raw list contains several separate classes:

| Class | Examples | Note |
|---|---|---|
| The objects of an external (SolMan/SAP) system | `integration.solman`, `interface.solman`, `SolMan`, `ERP OData Outbound`, `GetReturns`, `ConfirmReturns`, `UpdateProjectDates`, `ProjectMilestone` | **Out of scope** per the spec ("the non-ServiceNow entities") — they NEVER exist in the SNOW instance, yet they are legitimate content. The gate must handle them (otherwise it creates false positives). |
| Workflow state / UI text in quotes | `Escalated`, `Withdrawn`, `User Not Found`, `Tax code I2 does not exist` | Not component names — the false positives of the candidate extraction (the T007 has to refine them with the type hint). |
| The SNOW component names that LOOK real | `JiraInboundUtils`, `JiraIntegrationUtils`, `JiraInboundWebhook`, `S4ProjectInterface`, `ChTask`, `FrameWork`, `integration.vendor.config.matrix`, SolMan-BR-nevek | **This is the actual core of the problem**: the story/payload brings SolMan side or misspelled names, the article describes them as SNOW components, they do not exist on the instance. |

**The freshly generated sample (3 articles, local Qwen, DEV mode)** names 3 such
tartalmaz (`JiraInboundWebhook`, `JiraInboundUtils`, `JiraIntegrationUtils`) —
so the hallucination is reproducible NOW, not only a historical gold occurrence.

The blind spot sub-list in machine form: `artifacts/component_baseline_blindspot.json`.
