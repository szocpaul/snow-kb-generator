---
id: TASK-1
title: >-
  Spec 013 follow-up: SC-002 kalibrációs kapu PIROS — emberi döntés kell
  (T005/T011/T013)
status: To Do
assignee: []
created_date: '2026-09-29 12:02'
labels: []
dependencies: []
ordinal: 1000
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A spec 013 (013-audience-typed-decision) implementáció lefutott (T001-T014, MANUÁLIS KAPUk nélkül). Mérési eredmény: SC-001 ZÖLD (6/9 vs 6/9), SC-003 ZÖLD, SC-004 ZÖLD, de SC-002 PIROS a confirmatory 0.7-es kapunál (selective_risk=0.200 > 0.15, ece=0.163 > 0.10; coverage=0.833 OK). A 3 eltérő gold-címke (STRY0010003/4/5: helpdesk vs a Jev developer-tippje) evidenciával alátámasztott (troubleshooting-guide szekciók), de emberi review kell (T005/T013). Exploratív (NEM confirmatory): sweep 0.8-nál risk=0.111; ReAnchor helpdesk-weight=15.8 (train 0.667→0.917). A verifikációs-réteg spec (komponensnév-hallucináció gate) újraindítási feltétele MÉG NEM TELJESÜL: a spec 013 nincs productionben, a küszöb-hangolás emberi döntésre vár. Részletek: specs/013-audience-typed-decision/runner-report.md
<!-- SECTION:DESCRIPTION:END -->
