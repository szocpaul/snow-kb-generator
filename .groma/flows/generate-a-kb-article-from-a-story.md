---
type: Groma Flow
title: Generate a KB article from a Story
groma:
  id: generate-a-kb-article-from-a-story
---

The production path: a developer clicks the button on a closed Story, the webhook server runs the pipeline, the DSPy program generates the article with Kimi K3, guardrails clean it, and the ServiceNow client creates the KB article and writes its link back to the Story.

## Steps

| From | To | Action |
| --- | --- | --- |
| [ServiceNow developer](../actors/servicenow-developer.md) | [Create KB Article trigger](../systems/snow-kb-generator/components/ui-action-script.md) | Click the button on the closed Story |
| [UI Action script](../systems/snow-kb-generator/components/ui-action-script.md) | [Webhook server](../systems/snow-kb-generator/containers/snow-kb/components/server.md) | POST story id to /generate-kb |
| [Webhook server](../systems/snow-kb-generator/containers/snow-kb/components/server.md) | [Generation pipeline](../systems/snow-kb-generator/containers/snow-kb/components/pipeline.md) | Run generation pipeline |
| [Generation pipeline](../systems/snow-kb-generator/containers/snow-kb/components/pipeline.md) | [ServiceNow client](../systems/snow-kb-generator/containers/snow-kb/components/servicenow-client.md) | Fetch Story, template, Update Set, related articles |
| [ServiceNow client](../systems/snow-kb-generator/containers/snow-kb/components/servicenow-client.md) | [ServiceNow instance](../externals/servicenow-instance.md) | Read via Table API |
| [Generation pipeline](../systems/snow-kb-generator/containers/snow-kb/components/pipeline.md) | [StoryToKBArticle program](../systems/snow-kb-generator/containers/snow-kb/components/program.md) | Generate article from template |
| [Generation pipeline](../systems/snow-kb-generator/containers/snow-kb/components/pipeline.md) | [Kimi API](../externals/kimi-api.md) | Generate with Kimi K3 |
| [Generation pipeline](../systems/snow-kb-generator/containers/snow-kb/components/pipeline.md) | [ServiceNow client](../systems/snow-kb-generator/containers/snow-kb/components/servicenow-client.md) | Publish the guarded article |
| [ServiceNow client](../systems/snow-kb-generator/containers/snow-kb/components/servicenow-client.md) | [ServiceNow instance](../externals/servicenow-instance.md) | Create KB article, write work note |
