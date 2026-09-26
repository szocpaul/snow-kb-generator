---
type: Groma Relationships
title: Architecture relationships
---

## Relationships

| Source | Target | Description | Technology |
| --- | --- | --- | --- |
| [ServiceNow developer](actors/servicenow-developer.md) | [Create KB Article trigger (ServiceNow-side)](systems/snow-kb-generator/components/ui-action-script.md) | Clicks Create KB Article | ServiceNow UI |
| [servicenow/ui_action_script.js](../servicenow/ui_action_script.js) | [src/snow_kb/server.py](../src/snow_kb/server.py) | Posts story id | HTTPS REST, X-API-Key |
| [src/snow_kb/server.py](../src/snow_kb/server.py) | [src/snow_kb/pipeline.py](../src/snow_kb/pipeline.py) | Runs generation pipeline | in-process call |
| [src/snow_kb/cli.py](../src/snow_kb/cli.py) | [src/snow_kb/pipeline.py](../src/snow_kb/pipeline.py) | Runs generation pipeline | in-process call |
| [src/snow_kb/pipeline.py](../src/snow_kb/pipeline.py) | [src/snow_kb/config.py](../src/snow_kb/config.py) | Loads settings | in-process call |
| [src/snow_kb/pipeline.py](../src/snow_kb/pipeline.py) | [src/snow_kb/servicenow_client.py](../src/snow_kb/servicenow_client.py) | Fetches inputs, publishes article | in-process call |
| [src/snow_kb/pipeline.py](../src/snow_kb/pipeline.py) | [src/snow_kb/program.py](../src/snow_kb/program.py) | Generates article | dspy.Module forward |
| [src/snow_kb/servicenow_client.py](../src/snow_kb/servicenow_client.py) | [ServiceNow instance](externals/servicenow-instance.md) | Reads stories, writes KB articles | ServiceNow Table API |
| [src/snow_kb/pipeline.py](../src/snow_kb/pipeline.py) | [Kimi API](externals/kimi-api.md) | Generates article text | OpenAI-compatible HTTPS |
| [src/snow_kb/pipeline.py](../src/snow_kb/pipeline.py) | [Local llama.cpp server](externals/local-llama-cpp-server.md) | Generates in dev mode | OpenAI-compatible HTTP |
| [scripts_pdi/bootstrap_pdi.py](../scripts_pdi/bootstrap_pdi.py) | [ServiceNow instance](externals/servicenow-instance.md) | Provisions fields and UI Action | ServiceNow Table API |
| [Maintainer](actors/maintainer.md) | [Evaluation and GEPA optimization toolkit](systems/snow-kb-generator/containers/eval-toolkit/container.md) | Runs measurements and optimization | CLI |
| [Maintainer](actors/maintainer.md) | [PDI provisioning script](systems/snow-kb-generator/containers/pdi-provisioning/container.md) | Provisions new instances | CLI |
| [eval/baseline.py](../eval/baseline.py) | [eval/dataset.py](../eval/dataset.py) | Loads val examples | in-process call |
| [eval/baseline.py](../eval/baseline.py) | [eval/metric.py](../eval/metric.py) | Scores valset predictions | dspy.Evaluate |
| [eval/gepa_optimize.py](../eval/gepa_optimize.py) | [eval/dataset.py](../eval/dataset.py) | Loads train and val examples | in-process call |
| [eval/gepa_optimize.py](../eval/gepa_optimize.py) | [eval/metric.py](../eval/metric.py) | Reflects on metric feedback | dspy.GEPA |
| [eval/gepa_optimize.py](../eval/gepa_optimize.py) | [src/snow_kb/program.py](../src/snow_kb/program.py) | Optimizes predictor instructions | dspy.GEPA compile |
| [eval/gepa_optimize.py](../eval/gepa_optimize.py) | [Kimi API](externals/kimi-api.md) | Reflects and proposes instructions | OpenAI-compatible HTTPS |
| [eval/metric.py](../eval/metric.py) | [Local llama.cpp server](externals/local-llama-cpp-server.md) | Judges article style | LLM-as-judge |
