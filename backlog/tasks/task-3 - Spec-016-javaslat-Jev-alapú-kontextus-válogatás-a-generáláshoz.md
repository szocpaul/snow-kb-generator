---
id: TASK-3
title: >-
  Spec 016 javaslat: Jev-alapú kontextus-válogatás a generáláshoz
  (hide/summarize/show, a v3 history-relevance minta)
status: To Do
assignee: []
created_date: '2026-10-01'
labels: []
dependencies: []
ordinal: 1002
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
A cmpnd-ai/dspy-system-one-agent-patterns v3-as mintája (history relevance): Jev Score (hide/summarize/show) minősíti a kontextus-darabokat, plain Python dönti el, mi kerül a promptba. A snow-kb pipeline-ban a generálás a story-szöveget + update set XML-eket + kapcsolódó KB-cikkeket kapja — ezek egy része zaj. Jelölt feature: kontextus-válogatás a GenerateKb előtt, a meglévő mérőinfrastruktúrával (recording, replay, ReAnchor) mérve: token-megtakarítás + minőség-delta a rich_metricen. Előfeltétel: a 015 lezárva és a 014 gate megfigyelési időszaka értékelve. Újraindítási feltétel: a tulajdonos jóváhagyja a probléma-állítást (van-e érzékelhető zaj a jelenlegi prompt-kontextusban — a 014-es baseline artifacts alapján mérhető).
<!-- SECTION:DESCRIPTION:END -->
