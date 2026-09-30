---
id: TASK-2
title: >-
  Spec 014 javaslat: új típusos döntési pont a pipeline-ban (a 013-as
  mérőinfrastruktúra újrahasznosításával)
status: Done
assignee: []
created_date: '2026-09-30'
updated_date: '2026-09-30 17:04'
labels: []
dependencies: []
ordinal: 1001
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A spec 013 archiválva (Agent.md §43): az audience-döntésnek nem volt downstream-fogyasztója. A mérőinfrastruktúra (JSONL recording, replay, eval/jev_metrics.py, ReAnchor-wrapper, SC-gate-ek) megmaradt és újrahasznosítható. A 014-es spec tárgya: olyan típusos döntés a pipeline-ban, aminek valódi varianciája és pipeline-hatása van. Jelölt: „Érdemes-e KB-cikk erről a story-ról?" — Noul-kapu a generálás ELŐTT (költség/idő-megtakarítás, a cmpnd.ai e-mail-triage minta alapján). Az SDD 1. lépés (probléma-állítás) a tulajdonossal készül: van-e olyan story-típus, amiről most cikk készül, pedig nem kéne, vagy fordítva. Újraindítási feltétel: a tulajdonos megerősíti, hogy létezik ilyen döntési igény a munkafolyamatban.
<!-- SECTION:DESCRIPTION:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Lezárva: a 014-es spec megvalósult — komponensnév-hitelesítés az instance ellen + production push-gate (a taskban javasolt Noul-generálás-kapu helyett a tulajdonos ezt a témát választotta). A 013-as mérőinfrastruktúra újrahasznosítva (JSONL recording, replay, jev_metrics, ReAnchor, SC-gate-ek). SC-002/003/004 ZÖLD, SC-001 PIROS emberi elfogadással (a gold story-k aldidev-instance-uak). A gate BEKAPCSOLVA: verification_gate.enabled=true + behavior=flag megfigyelési időszakra (T014 emberi döntés, Agent.md §44). 349 pytest zöld. Branch: 014-component-instance-verification.
<!-- SECTION:FINAL_SUMMARY:END -->
