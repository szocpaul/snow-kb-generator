---
type: Groma Flow
title: Optimize the program with GEPA
groma:
  id: optimize-the-program-with-gepa
---

The offline quality loop: the maintainer runs the GEPA optimization on the gold dataset; the runner compiles candidate programs, scores them with the rich metric, and uses Kimi K3 to reflect on the feedback and propose better instructions. The winning program is saved to artifacts/program.json, which the webhook server loads at startup.

## Steps

| From | To | Action |
| --- | --- | --- |
| [Maintainer](../actors/maintainer.md) | [Evaluation and GEPA optimization toolkit](../systems/snow-kb-generator/containers/eval-toolkit/container.md) | Run python -m eval.gepa_optimize |
| [GEPA optimization runner](../systems/snow-kb-generator/containers/eval-toolkit/components/gepa-optimize.md) | [Gold dataset loader](../systems/snow-kb-generator/containers/eval-toolkit/components/dataset.md) | Load train and val examples |
| [GEPA optimization runner](../systems/snow-kb-generator/containers/eval-toolkit/components/gepa-optimize.md) | [StoryToKBArticle program](../systems/snow-kb-generator/containers/snow-kb/components/program.md) | Compile candidate programs |
| [GEPA optimization runner](../systems/snow-kb-generator/containers/eval-toolkit/components/gepa-optimize.md) | [Rich evaluation metric](../systems/snow-kb-generator/containers/eval-toolkit/components/metric.md) | Score candidates, collect feedback |
| [GEPA optimization runner](../systems/snow-kb-generator/containers/eval-toolkit/components/gepa-optimize.md) | [Kimi API](../externals/kimi-api.md) | Reflect on feedback, propose instructions |
