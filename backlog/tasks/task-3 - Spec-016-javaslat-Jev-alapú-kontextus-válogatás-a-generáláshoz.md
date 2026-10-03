---
id: TASK-3
title: >-
  Spec 016 javaslat: Jev-alapú kontextus-válogatás a generáláshoz
  (hide/summarize/show, a v3 history-relevance minta)
status: Done
assignee: []
created_date: '2026-10-01'
updated_date: '2026-10-02 13:27'
labels: []
dependencies: []
ordinal: 1002
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A cmpnd-ai/dspy-system-one-agent-patterns v3-as mintája (history relevance): Jev Score (hide/summarize/show) minősíti a kontextus-darabokat, plain Python dönti el, mi kerül a promptba. A snow-kb pipeline-ban a generálás a story-szöveget + update set XML-eket + kapcsolódó KB-cikkeket kapja — ezek egy része zaj. Jelölt feature: kontextus-válogatás a GenerateKb előtt, a meglévő mérőinfrastruktúrával (recording, replay, ReAnchor) mérve: token-megtakarítás + minőség-delta a rich_metricen. Előfeltétel: a 015 lezárva és a 014 gate megfigyelési időszaka értékelve. Újraindítási feltétel: a tulajdonos jóváhagyja a probléma-állítást (van-e érzékelhető zaj a jelenlegi prompt-kontextusban — a 014-es baseline artifacts alapján mérhető).
<!-- SECTION:DESCRIPTION:END -->

## Final Summary

<!-- SECTION:FINAL_SUMMARY:BEGIN -->
Spec 016 implementálva és a T012 MANUÁLIS KAPUnál emberi döntéssel MEGÁLLÍTVA (2026-10-02). A válogató modul + pipeline-bekötés kész (23 teszt, suite 415 zöld, enabled=false). A mérés: baseline 8540 kontextus-token (21.4% zaj-jelölt), a válogatás INERT a kiinduló küszöbökön (0.45% teljes-prompt csökkenés vs 5% cél). Kalibráció: plafon-táblázat (nyers 11.1% / költség-korlátos 0.0% / state-fixszel ~1.1-1.2%) + gyökéroka-finding (a story_context felfújja a Score-t — a state-fix bekerült). Az SC-001 dokumentált PIROS (a cél minőség-kockázat nélkül nem érhető el), SC-002..006 zöld. Részletek: specs/016-context-selection/runner-report.md, Agent.md §48. Gate-ek: python -m eval.context_sc_gates_016 (exit 0).
<!-- SECTION:FINAL_SUMMARY:END -->
